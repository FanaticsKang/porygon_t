#!/usr/bin/env python3
"""
检查测试文件是否存在并返回基本信息。
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
import ast
import re

def infer_test_path(source_file: str) -> str:
    """
    根据源代码文件路径推断测试文件路径。

    规则:
    1. 如果源代码在 src/ 目录下，测试文件在 tests/ 目录下，文件名加 test_ 前缀
    2. 否则，测试文件在同一目录下，文件名加 test_ 前缀
    3. 保持目录结构
    """
    source_path = Path(source_file)

    # 标准化路径为绝对路径
    if not source_path.is_absolute():
        source_path = Path.cwd() / source_path

    # 检查是否在 src 目录下
    source_parts = list(source_path.parts)

    # 查找 src 目录的位置
    try:
        src_index = source_parts.index('src')
        # 在 src 目录下，替换为 tests
        test_parts = list(source_parts)
        test_parts[src_index] = 'tests'

        # 获取文件名并添加 test_ 前缀
        filename = test_parts[-1]
        test_parts[-1] = f"test_{filename}"

        test_path = Path(*test_parts)
    except ValueError:
        # 不在 src 目录下，直接在相同目录添加 test_ 前缀
        test_path = source_path.parent / f"test_{source_path.name}"

    return str(test_path)

def count_test_cases(test_file_path: str) -> int:
    """
    统计测试文件中的测试用例数量。

    支持:
    1. pytest 风格: test_ 开头的函数
    2. unittest 风格: TestCase 子类中 test_ 开头的方法
    """
    try:
        with open(test_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return 0

    count = 0

    # 方法1: 使用正则表达式简单统计（快速但可能不准确）
    # 统计 test_ 开头的函数定义
    pytest_pattern = r'^\s*def test_[a-zA-Z0-9_]*\s*\('
    pytest_matches = re.findall(pytest_pattern, content, re.MULTILINE)
    count += len(pytest_matches)

    # 统计 unittest 测试方法
    unittest_pattern = r'^\s*def test_[a-zA-Z0-9_]*\s*\(self[^)]*\)'
    unittest_matches = re.findall(unittest_pattern, content, re.MULTILINE)
    count += len(unittest_matches)

    # 如果正则匹配到结果，直接返回
    if count > 0:
        return count

    # 方法2: 使用 AST 解析（更准确但稍慢）
    try:
        tree = ast.parse(content)

        for node in ast.walk(tree):
            # pytest 风格函数
            if isinstance(node, ast.FunctionDef):
                if node.name.startswith('test_'):
                    count += 1

            # unittest 风格方法
            elif isinstance(node, ast.ClassDef):
                # 检查是否继承自 unittest.TestCase
                base_names = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        base_names.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        base_names.append(base.attr)

                # 简单的继承检查（不处理 import as 等情况）
                if 'TestCase' in base_names:
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            if item.name.startswith('test_'):
                                count += 1
    except SyntaxError:
        # 文件可能不是有效的 Python 代码
        pass

    return count

def get_last_modified(test_file_path: str):
    """获取文件的最后修改时间，返回 ISO 8601 格式字符串或 None"""
    try:
        mtime = os.path.getmtime(test_file_path)
        return datetime.utcfromtimestamp(mtime).isoformat() + 'Z'
    except Exception:
        return None

def main():
    parser = argparse.ArgumentParser(description='检查测试文件是否存在并返回基本信息')
    parser.add_argument('--source-file', required=True, help='源代码文件路径')

    args = parser.parse_args()

    # 检查源代码文件是否存在
    if not os.path.exists(args.source_file):
        print(json.dumps({
            "error": f"源代码文件不存在: {args.source_file}",
            "exists": False,
            "test_file_path": "",
            "test_case_count": 0,
            "last_modified": None
        }, indent=2))
        sys.exit(1)

    # 推断测试文件路径
    test_file_path = infer_test_path(args.source_file)

    # 检查测试文件是否存在
    exists = os.path.exists(test_file_path)

    # 计算测试用例数量
    test_case_count = 0
    last_modified = None

    if exists:
        test_case_count = count_test_cases(test_file_path)
        last_modified = get_last_modified(test_file_path)

    # 输出结果
    result = {
        "exists": exists,
        "test_file_path": test_file_path,
        "test_case_count": test_case_count,
        "last_modified": last_modified
    }

    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()