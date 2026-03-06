"""
测试执行器模块

提供运行 pytest、Google Test，收集测试结果等功能。
"""

import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET

logger = logging.getLogger('porygon_t.runner')


@dataclass
class TestCase:
    """单个测试用例结果"""
    name: str
    status: str  # 'passed', 'failed', 'skipped', 'error'
    duration: float = 0.0
    message: Optional[str] = None
    traceback: Optional[str] = None


@dataclass
class TestResult:
    """测试结果"""
    test_file: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration: float = 0.0
    cases: List[TestCase] = field(default_factory=list)
    coverage: Dict = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.passed / self.total * 100


class TestRunner:
    """Python 测试执行器（基于 pytest）"""

    def __init__(self, test_file_path: Path, project_path: Optional[Path] = None):
        self.test_file_path = Path(test_file_path)
        self.project_path = project_path or self.test_file_path.parent
        self.result = TestResult(test_file=str(test_file_path))
        self.junit_file = Path(tempfile.mktemp(suffix='.xml'))

    def run(self, with_coverage: bool = True, coverage_target: Optional[Path] = None,
            timeout: int = 300) -> TestResult:
        """运行 pytest 测试"""
        # with_coverage 和 coverage_target 参数暂时保留以保持兼容性
        _ = with_coverage, coverage_target
        logger.info(f"运行测试: {self.test_file_path.name}")

        def _posix(path):
            return path.as_posix() if hasattr(path, 'as_posix') else str(path).replace('\\', '/')

        cmd = [
            'python', '-m', 'pytest',
            _posix(self.test_file_path),
            '-v', '--tb=short',
            f'--junitxml={_posix(self.junit_file)}'
        ]

        try:
            result = subprocess.run(
                cmd, cwd=self.project_path,
                capture_output=True, text=True, timeout=timeout
            )

            if result.returncode != 0 and result.stderr:
                logger.warning(f"pytest stderr: {result.stderr[:500]}")

            self._parse_junit_results()

            logger.info(f"测试完成: {self.result.passed}/{self.result.total} 通过")

        except subprocess.TimeoutExpired:
            logger.error(f"测试超时 ({timeout}s)")
            self.result.errors += 1
        except Exception as e:
            logger.error(f"运行测试失败: {e}")
            self.result.errors += 1
        finally:
            self._cleanup()

        return self.result

    def _parse_junit_results(self):
        """解析 JUnit XML 结果"""
        if not self.junit_file.exists():
            return

        try:
            tree = ET.parse(self.junit_file)
            root = tree.getroot()

            for testsuite in root.findall('testsuite'):
                self.result.total = int(testsuite.get('tests', 0))
                self.result.failed = int(testsuite.get('failures', 0))
                self.result.errors = int(testsuite.get('errors', 0))
                self.result.skipped = int(testsuite.get('skipped', 0))
                self.result.duration = float(testsuite.get('time', 0))
                self.result.passed = (
                    self.result.total - self.result.failed
                    - self.result.errors - self.result.skipped
                )

                for testcase in testsuite.findall('testcase'):
                    case = self._parse_test_case(testcase)
                    self.result.cases.append(case)

        except Exception:
            logger.exception("解析 JUnit 结果失败")

    def _parse_test_case(self, testcase: ET.Element) -> TestCase:
        """解析单个测试用例"""
        name = testcase.get('name', 'unknown')
        duration = float(testcase.get('time', 0))
        status = 'passed'
        message = None
        traceback = None

        failure = testcase.find('failure')
        if failure is not None:
            status = 'failed'
            message = failure.get('message', '')
            traceback = failure.text

        error = testcase.find('error')
        if error is not None:
            status = 'error'
            message = error.get('message', '')
            traceback = error.text

        skipped = testcase.find('skipped')
        if skipped is not None:
            status = 'skipped'
            message = skipped.get('message', '')

        return TestCase(
            name=name, status=status, duration=duration,
            message=message, traceback=traceback
        )

    def _cleanup(self):
        """清理临时文件"""
        if self.junit_file.exists():
            try:
                self.junit_file.unlink()
            except OSError:
                pass

    def generate_summary(self, output_path: Path) -> bool:
        """生成测试摘要文件"""
        summary = {
            'test_file': self.result.test_file,
            'summary': {
                'total': self.result.total,
                'passed': self.result.passed,
                'failed': self.result.failed,
                'skipped': self.result.skipped,
                'errors': self.result.errors,
                'duration': self.result.duration,
                'success_rate': self.result.success_rate
            },
            'coverage': self.result.coverage,
            'cases': [
                {
                    'name': case.name,
                    'status': case.status,
                    'duration': case.duration,
                    'message': case.message
                }
                for case in self.result.cases
            ]
        }

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
            return True
        except Exception as e:
            logger.error(f"生成摘要失败: {e}")
            return False


def run_single_test(test_file: Path, project_path: Optional[Path] = None,
                    output_summary: Optional[Path] = None) -> TestResult:
    """运行单个测试文件的便捷函数"""
    runner = TestRunner(test_file, project_path)
    result = runner.run()
    if output_summary:
        runner.generate_summary(output_summary)
    return result


class CppTestRunner:
    """C++ 测试执行器（基于 Google Test）"""

    def __init__(self, test_file_path: Path, project_path: Optional[Path] = None,
                 target_file: Optional[Path] = None):
        self.test_file_path = Path(test_file_path)
        self.project_path = project_path or self.test_file_path.parent
        self.target_file = target_file
        self.result = TestResult(test_file=str(test_file_path))
        self.test_binary: Optional[Path] = None

    def _find_cmake_or_build_system(self) -> Optional[Path]:
        """向上查找 CMakeLists.txt"""
        current = self.project_path
        for _ in range(5):
            cmake_file = current / 'CMakeLists.txt'
            if cmake_file.exists():
                return current
            parent = current.parent
            if parent == current:
                break
            current = parent
        return None

    def _compile_test(self, timeout: int = 300) -> bool:
        """编译 C++ 测试"""
        cmake_root = self._find_cmake_or_build_system()
        if cmake_root:
            logger.info(f"检测到 CMake 项目: {cmake_root}")
            return self._compile_with_cmake(cmake_root, timeout)
        else:
            logger.info("未检测到 CMake，尝试直接编译")
            return self._compile_directly(timeout)

    def _find_cmake_executable(self) -> str:
        """查找 CMake 可执行文件"""
        cmake_exe = 'cmake.exe' if os.name == 'nt' else 'cmake'
        cmake_path = shutil.which(cmake_exe)
        if cmake_path:
            return cmake_path
        try:
            import cmake
            cmake_dir = Path(cmake.CMAKE_BIN_DIR)
            cmake_exe_path = cmake_dir / cmake_exe
            if cmake_exe_path.exists():
                return str(cmake_exe_path)
        except ImportError:
            pass
        return cmake_exe

    def _detect_mingw(self) -> Optional[Path]:
        """检测 MinGW 安装路径"""
        if os.name != 'nt':
            return None
        msys2_paths = [
            Path('C:/msys64/ucrt64/bin'),
            Path('C:/msys64/mingw64/bin'),
            Path('C:/mingw64/bin'),
            Path('C:/mingw/bin'),
        ]
        for path in msys2_paths:
            if path.exists() and (path / 'g++.exe').exists():
                return path
        return None

    def _compile_with_cmake(self, cmake_root: Path, timeout: int) -> bool:
        """使用 CMake 编译"""
        build_dir = Path(tempfile.mkdtemp(prefix=f'cmake_build_{self.test_file_path.stem}_'))
        logger.info(f"CMake 构建目录: {build_dir}")

        env = os.environ.copy()
        mingw_path = self._detect_mingw()
        if mingw_path:
            logger.info(f"检测到 MinGW: {mingw_path}")
            env['PATH'] = str(mingw_path) + os.pathsep + env.get('PATH', '')
            env['CXX'] = str(mingw_path / 'g++.exe')

        cmake_exe = self._find_cmake_executable()
        logger.info(f"使用 CMake: {cmake_exe}")

        cmake_cmd = [cmake_exe, str(cmake_root), '-DCMAKE_BUILD_TYPE=Debug']
        if os.name == 'nt' and mingw_path:
            cmake_cmd.extend(['-G', 'MinGW Makefiles'])

        try:
            result = subprocess.run(
                cmake_cmd, cwd=build_dir, capture_output=True,
                text=True, timeout=timeout, env=env
            )
            if result.returncode != 0:
                logger.error(f"CMake 配置失败: {result.stderr}")
                return False

            build_cmd = [cmake_exe, '--build', str(build_dir), '--parallel', '4']
            result = subprocess.run(
                build_cmd, capture_output=True,
                text=True, timeout=timeout, env=env
            )
            if result.returncode != 0:
                logger.error(f"CMake 构建失败: {result.stderr}")
                return False

            # 查找测试二进制文件
            test_name = self.test_file_path.stem.replace('test_', '')
            exe_suffix = '.exe' if os.name == 'nt' else ''
            for pattern in [f'test_{test_name}{exe_suffix}', f'{test_name}_test{exe_suffix}']:
                for search_dir in [build_dir, build_dir / 'src', build_dir / 'tests']:
                    binary = search_dir / pattern
                    if binary.exists():
                        self.test_binary = binary
                        break
                if self.test_binary:
                    break

            if self.test_binary:
                logger.info(f"找到测试二进制文件: {self.test_binary}")
            else:
                logger.error("未找到测试二进制文件")

            return self.test_binary is not None

        except Exception as e:
            logger.error(f"CMake 编译失败: {e}")
            return False

    def _compile_directly(self, timeout: int) -> bool:
        """直接编译单个测试文件"""
        temp_dir = Path(tempfile.mkdtemp(prefix='cpp_test_'))
        exe_suffix = '.exe' if os.name == 'nt' else ''
        self.test_binary = temp_dir / f'test_runner{exe_suffix}'

        cmd = [
            'g++', '-std=c++14', '-O0', '-g',
            '-I', str(self.project_path),
            '-I', str(self.project_path / 'src'),
            str(self.test_file_path)
        ]

        if self.target_file and self.target_file.suffix in ['.cpp', '.cc', '.cxx']:
            cmd.append(str(self.target_file))

        cmd.extend(['-lgtest', '-lgtest_main', '-lpthread', '-o', str(self.test_binary)])

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
            if result.returncode != 0:
                logger.error(f"编译失败: {result.stderr}")
                return False
            return True
        except Exception as e:
            logger.error(f"编译异常: {e}")
            return False

    def _parse_gtest_output(self, output: str):
        """解析 Google Test 输出"""
        test_pattern = re.compile(r'\[\s+(\w+)\s+\]\s+(\w+)\.(\w+)\s+\((\d+)\s*ms\)')

        for line in output.split('\n'):
            match = test_pattern.search(line)
            if match:
                status_str, suite, test_name, duration = match.groups()
                status_map = {'OK': 'passed', 'FAILED': 'failed', 'SKIPPED': 'skipped'}
                case = TestCase(
                    name=f"{suite}.{test_name}",
                    status=status_map.get(status_str, 'unknown'),
                    duration=float(duration) / 1000.0
                )
                self.result.cases.append(case)
                self.result.total += 1
                if case.status == 'passed':
                    self.result.passed += 1
                elif case.status == 'failed':
                    self.result.failed += 1
                elif case.status == 'skipped':
                    self.result.skipped += 1

    def run(self, with_coverage: bool = True, coverage_target: Optional[Path] = None,
            timeout: int = 300) -> TestResult:
        """运行 C++ 测试"""
        # with_coverage 和 coverage_target 参数暂时保留以保持兼容性
        _ = with_coverage, coverage_target
        logger.info(f"编译 C++ 测试: {self.test_file_path.name}")

        if not self._compile_test(timeout):
            logger.error("C++ 测试编译失败")
            self.result.errors += 1
            return self.result

        logger.info(f"执行 C++ 测试: {self.test_binary}")

        try:
            env = os.environ.copy()
            mingw_path = self._detect_mingw()
            if mingw_path:
                env['PATH'] = str(mingw_path) + os.pathsep + env.get('PATH', '')

            cmd = [str(self.test_binary), '--gtest_color=no']
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=timeout, shell=False, env=env
            )

            self._parse_gtest_output(result.stdout)
            self._parse_gtest_output(result.stderr)

            logger.info(f"测试完成: {self.result.passed}/{self.result.total} 通过")

        except subprocess.TimeoutExpired:
            logger.error(f"测试超时 ({timeout}s)")
            self.result.errors += 1
        except Exception as e:
            logger.error(f"运行测试失败: {e}")
            self.result.errors += 1

        return self.result

    def generate_summary(self, output_path: Path) -> bool:
        """生成测试摘要文件"""
        summary = {
            'test_file': self.result.test_file,
            'summary': {
                'total': self.result.total,
                'passed': self.result.passed,
                'failed': self.result.failed,
                'skipped': self.result.skipped,
                'errors': self.result.errors,
                'duration': self.result.duration,
                'success_rate': self.result.success_rate
            },
            'coverage': self.result.coverage,
            'cases': [
                {
                    'name': case.name,
                    'status': case.status,
                    'duration': case.duration,
                    'message': case.message
                }
                for case in self.result.cases
            ],
            'language': 'cpp'
        }

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
            return True
        except Exception as e:
            logger.error(f"生成摘要失败: {e}")
            return False
