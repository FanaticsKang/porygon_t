"""
porygon_t 工具脚本包

包含测试生成、执行和报告相关的辅助工具。
"""

__version__ = "0.1.0"

from .claude_client import ClaudeClient, ClaudeError
from .file_parser import (
    PythonFileParser,
    CppFileParser,
    ModuleInfo,
    FunctionInfo,
    ClassInfo,
    get_file_parser
)
from .git_utils import (
    GitError,
    checkout_branch,
    get_commit_diff_files,
    get_diff_stat,
    get_diff_content,
    is_valid_git_repo
)
from .report_generator import ReportGenerator, ReportData
from .test_runner import TestRunner, CppTestRunner, TestResult, TestCase

__all__ = [
    # Claude 客户端
    'ClaudeClient',
    'ClaudeError',
    # 文件解析
    'PythonFileParser',
    'CppFileParser',
    'ModuleInfo',
    'FunctionInfo',
    'ClassInfo',
    'get_file_parser',
    # Git 工具
    'GitError',
    'checkout_branch',
    'get_commit_diff_files',
    'get_diff_stat',
    'get_diff_content',
    'is_valid_git_repo',
    # 报告生成
    'ReportGenerator',
    'ReportData',
    # 测试执行
    'TestRunner',
    'CppTestRunner',
    'TestResult',
    'TestCase',
]
