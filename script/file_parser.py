"""
代码文件解析器

提供解析 Python 和 C++ 文件、提取函数/类/方法信息等功能。
"""

import ast
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

logger = logging.getLogger('porygon_t.parser')


@dataclass
class FunctionInfo:
    """函数信息"""
    name: str
    line_start: int
    line_end: int
    args: List[str] = field(default_factory=list)
    returns: Optional[str] = None
    docstring: Optional[str] = None
    is_async: bool = False


@dataclass
class ClassInfo:
    """类信息"""
    name: str
    line_start: int
    line_end: int
    methods: List[FunctionInfo] = field(default_factory=list)
    docstring: Optional[str] = None
    bases: List[str] = field(default_factory=list)


@dataclass
class ModuleInfo:
    """模块信息"""
    file_path: str
    file_name: str
    functions: List[FunctionInfo] = field(default_factory=list)
    classes: List[ClassInfo] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    docstring: Optional[str] = None


class PythonFileParser:
    """Python 文件解析器"""

    def __init__(self, file_path: str):
        """
        初始化解析器

        Args:
            file_path: Python 文件路径
        """
        self.file_path = Path(file_path)
        self.file_name = self.file_path.name
        self.content = ""
        self.tree: Optional[ast.AST] = None

    def parse(self) -> Optional[ModuleInfo]:
        """
        解析 Python 文件

        Returns:
            模块信息，解析失败返回 None
        """
        try:
            self.content = self.file_path.read_text(encoding='utf-8')
            self.tree = ast.parse(self.content)
            return self._extract_module_info()
        except SyntaxError as e:
            logger.error(f"解析文件语法错误 [{self.file_name}]: {e}")
            return None
        except Exception as e:
            logger.error(f"解析文件失败 [{self.file_name}]: {e}")
            return None

    def _extract_module_info(self) -> ModuleInfo:
        """提取模块信息"""
        module = ModuleInfo(
            file_path=str(self.file_path),
            file_name=self.file_name
        )

        # 提取文档字符串
        module.docstring = ast.get_docstring(self.tree)

        for node in ast.iter_child_nodes(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module.imports.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module_name = node.module or ''
                names = [alias.name for alias in node.names]
                module.imports.append(f"from {module_name} import {', '.join(names)}")
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                func_info = self._extract_function_info(node)
                module.functions.append(func_info)
            elif isinstance(node, ast.ClassDef):
                class_info = self._extract_class_info(node)
                module.classes.append(class_info)

        return module

    def _extract_function_info(
        self,
        node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
    ) -> FunctionInfo:
        """提取函数信息"""
        return FunctionInfo(
            name=node.name,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            args=self._extract_args(node.args),
            returns=self._get_annotation(node.returns),
            docstring=ast.get_docstring(node),
            is_async=isinstance(node, ast.AsyncFunctionDef)
        )

    def _extract_class_info(self, node: ast.ClassDef) -> ClassInfo:
        """提取类信息"""
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef) or isinstance(item, ast.AsyncFunctionDef):
                method_info = self._extract_function_info(item)
                methods.append(method_info)

        bases = [self._get_base_name(base) for base in node.bases]

        return ClassInfo(
            name=node.name,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            methods=methods,
            docstring=ast.get_docstring(node),
            bases=bases
        )

    def _extract_args(self, args: ast.arguments) -> List[str]:
        """提取参数列表"""
        arg_list = []

        # 位置参数
        for arg in args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {self._get_annotation(arg.annotation)}"
            arg_list.append(arg_str)

        # 可变参数 (*args)
        if args.vararg:
            arg_str = f"*{args.vararg.arg}"
            if args.vararg.annotation:
                arg_str += f": {self._get_annotation(args.vararg.annotation)}"
            arg_list.append(arg_str)

        # 关键字参数 (**kwargs)
        if args.kwarg:
            arg_str = f"**{args.kwarg.arg}"
            if args.kwarg.annotation:
                arg_str += f": {self._get_annotation(args.kwarg.annotation)}"
            arg_list.append(arg_str)

        return arg_list

    def _get_annotation(self, node: Optional[ast.AST]) -> Optional[str]:
        """获取类型注解字符串"""
        if node is None:
            return None
        return ast.unparse(node) if hasattr(ast, 'unparse') else str(node)

    def _get_base_name(self, node: ast.AST) -> str:
        """获取基类名称"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_base_name(node.value)}.{node.attr}"
        return ""

    def get_changed_lines(self, line_numbers: List[int]) -> List[Dict]:
        """
        获取指定行的代码信息

        Args:
            line_numbers: 行号列表

        Returns:
            每行代码的信息
        """
        if not self.content:
            self.content = self.file_path.read_text(encoding='utf-8')

        lines = self.content.split('\n')
        result = []

        for line_no in line_numbers:
            if 1 <= line_no <= len(lines):
                result.append({
                    'line_no': line_no,
                    'content': lines[line_no - 1],
                    'is_function_def': False,
                    'is_class_def': False
                })

        # 标记函数和类定义
        if self.tree:
            for node in ast.walk(self.tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    for item in result:
                        if item['line_no'] == node.lineno:
                            item['is_function_def'] = isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                            item['is_class_def'] = isinstance(node, ast.ClassDef)
                            item['name'] = node.name

        return result


def extract_function_signatures(file_path: str) -> Dict[str, str]:
    """
    快速提取文件中的函数签名

    Args:
        file_path: Python 文件路径

    Returns:
        函数名到签名的映射
    """
    parser = PythonFileParser(file_path)
    module_info = parser.parse()

    if not module_info:
        return {}

    signatures = {}

    # 模块级函数
    for func in module_info.functions:
        args_str = ', '.join(func.args)
        return_str = f" -> {func.returns}" if func.returns else ""
        sig = f"def {func.name}({args_str}){return_str}"
        signatures[func.name] = sig

    # 类方法
    for cls in module_info.classes:
        for method in cls.methods:
            full_name = f"{cls.name}.{method.name}"
            args_str = ', '.join(method.args)
            return_str = f" -> {method.returns}" if method.returns else ""
            sig = f"def {method.name}({args_str}){return_str}"
            signatures[full_name] = sig

    return signatures


def get_testable_items(file_path: str) -> List[str]:
    """
    获取文件中可测试的项（函数和类）

    Args:
        file_path: Python 文件路径

    Returns:
        可测试项名称列表
    """
    parser = PythonFileParser(file_path)
    module_info = parser.parse()

    if not module_info:
        return []

    items = []

    # 函数
    for func in module_info.functions:
        if not func.name.startswith('_'):  # 跳过私有函数
            items.append(func.name)

    # 类
    for cls in module_info.classes:
        items.append(cls.name)

    return items


# ============ C++ 文件解析器 ============


class CppFileParser:
    """C++ 文件解析器（基于正则表达式）"""

    def __init__(self, file_path: str):
        """
        初始化解析器

        Args:
            file_path: C++ 文件路径
        """
        self.file_path = Path(file_path)
        self.file_name = self.file_path.name
        self.content = ""

    def parse(self) -> Optional[ModuleInfo]:
        """
        解析 C++ 文件

        Returns:
            模块信息，解析失败返回 None
        """
        try:
            self.content = self.file_path.read_text(encoding='utf-8')
            return self._extract_module_info()
        except Exception as e:
            logger.error(f"解析 C++ 文件失败 [{self.file_name}]: {e}")
            return None

    def _extract_module_info(self) -> ModuleInfo:
        """提取模块信息"""
        module = ModuleInfo(
            file_path=str(self.file_path),
            file_name=self.file_name
        )

        # 提取 #include 语句
        include_pattern = re.compile(r'#include\s+[<"]([^>"]+)[>"]')
        module.imports = [f"#include {m.group(1)}" for m in include_pattern.finditer(self.content)]

        # 提取类定义
        module.classes = self._extract_classes()

        # 提取函数定义（不在类中的）
        module.functions = self._extract_global_functions()

        return module

    def _extract_classes(self) -> List[ClassInfo]:
        """提取类定义"""
        classes = []

        # 匹配 class 定义（简化版，不处理模板和嵌套类）
        class_pattern = re.compile(
            r'class\s+(\w+)\s*(?::\s*(?:public|private|protected)\s+\w+)?\s*\{',
            re.MULTILINE
        )

        for match in class_pattern.finditer(self.content):
            class_name = match.group(1)
            start_pos = match.start()

            # 找到匹配的结束括号
            brace_count = 1
            pos = match.end()
            while pos < len(self.content) and brace_count > 0:
                if self.content[pos] == '{':
                    brace_count += 1
                elif self.content[pos] == '}':
                    brace_count -= 1
                pos += 1

            end_pos = pos
            class_body = self.content[match.end():end_pos-1]

            # 计算行号
            line_start = self.content[:start_pos].count('\n') + 1
            line_end = self.content[:end_pos].count('\n') + 1

            # 提取类中的方法
            methods = self._extract_class_methods(class_body)

            cls = ClassInfo(
                name=class_name,
                line_start=line_start,
                line_end=line_end,
                methods=methods
            )
            classes.append(cls)

        return classes

    def _extract_class_methods(self, class_body: str) -> List[FunctionInfo]:
        """提取类方法定义"""
        methods = []

        # 匹配方法定义（简化版）
        method_pattern = re.compile(
            r'(?:virtual\s+|static\s+|const\s+)?'  # 修饰符
            r'(?:\w+[\s\*\&]*\s+)?'  # 返回类型（可选，构造函数没有）
            r'(\w+)\s*\([^)]*\)'  # 方法名和参数
            r'\s*(?:const)?\s*(?:override)?\s*(?:=\s*0)?\s*\{?',  # 修饰符
            re.MULTILINE
        )

        for match in method_pattern.finditer(class_body):
            method_name = match.group(1)
            # 跳过构造函数和析构函数的简单检测
            if method_name in ['if', 'for', 'while', 'switch', 'return']:
                continue

            line_start = class_body[:match.start()].count('\n') + 1

            # 提取参数
            params_str = match.group(0).split('(')[1].split(')')[0] if '(' in match.group(0) else ""
            args = [p.strip() for p in params_str.split(',') if p.strip()]

            func = FunctionInfo(
                name=method_name,
                line_start=line_start,
                line_end=line_start,  # 简化处理
                args=args
            )
            methods.append(func)

        return methods

    def _extract_global_functions(self) -> List[FunctionInfo]:
        """提取全局函数"""
        functions = []

        # 匹配全局函数定义（简化版）
        func_pattern = re.compile(
            r'(?:\w+[\s\*\&]*\s+)+'  # 返回类型
            r'(\w+)\s*\([^)]*\)'  # 函数名和参数
            r'\s*\{',  # 函数体开始
            re.MULTILINE
        )

        for match in func_pattern.finditer(self.content):
            func_name = match.group(1)
            # 跳过常见关键字和类方法
            if func_name in ['if', 'for', 'while', 'switch', 'return', 'class', 'struct', 'namespace']:
                continue

            # 检查是否在类定义中（简化判断）
            before = self.content[:match.start()]
            if before.rfind('class') > before.rfind('}'):
                continue

            line_start = before.count('\n') + 1

            # 提取参数
            params_str = match.group(0).split('(')[1].split(')')[0] if '(' in match.group(0) else ""
            args = [p.strip() for p in params_str.split(',') if p.strip()]

            func = FunctionInfo(
                name=func_name,
                line_start=line_start,
                line_end=line_start,
                args=args
            )
            functions.append(func)

        return functions


def extract_cpp_function_signatures(file_path: str) -> Dict[str, str]:
    """
    快速提取 C++ 文件中的函数签名

    Args:
        file_path: C++ 文件路径

    Returns:
        函数名到签名的映射
    """
    parser = CppFileParser(file_path)
    module_info = parser.parse()

    if not module_info:
        return {}

    signatures = {}

    # 全局函数
    for func in module_info.functions:
        args_str = ', '.join(func.args)
        sig = f"{func.name}({args_str})"
        signatures[func.name] = sig

    # 类方法
    for cls in module_info.classes:
        for method in cls.methods:
            full_name = f"{cls.name}::{method.name}"
            args_str = ', '.join(method.args)
            sig = f"{method.name}({args_str})"
            signatures[full_name] = sig

    return signatures


def get_cpp_testable_items(file_path: str) -> List[str]:
    """
    获取 C++ 文件中可测试的项（函数和类）

    Args:
        file_path: C++ 文件路径

    Returns:
        可测试项名称列表
    """
    parser = CppFileParser(file_path)
    module_info = parser.parse()

    if not module_info:
        return []

    items = []

    # 函数
    for func in module_info.functions:
        if not func.name.startswith('_'):  # 跳过私有函数
            items.append(func.name)

    # 类
    for cls in module_info.classes:
        items.append(cls.name)

    return items


# ============ 通用接口 ============


def get_file_parser(file_path: str):
    """
    根据文件类型获取对应的解析器

    Args:
        file_path: 文件路径

    Returns:
        对应的文件解析器实例
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == '.py':
        return PythonFileParser(file_path)
    elif ext in ['.cpp', '.cc', '.cxx', '.hpp', '.h']:
        return CppFileParser(file_path)
    else:
        raise ValueError(f"不支持的文件类型: {ext}")
