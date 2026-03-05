---
name: check-test-exists
description: |
  检查指定源代码文件对应的测试文件是否存在，并返回测试文件的基本信息。
  当用户需要检查测试文件是否存在、获取测试用例数量或了解测试文件最后修改时间时使用此技能。
  此技能专为测试自动化流水线设计，用于判断是否需要生成新测试或更新现有测试。
  使用此技能的场景包括：检查测试覆盖率、评估测试完整性、决定是否运行测试、或作为测试生成流程的决策依据。
---

# check-test-exists 技能

检查源代码文件对应的测试文件是否存在，并返回测试文件路径、测试用例数量和最后修改时间。

## 使用方式

```bash
claude -s check-test-exists --source-file <源代码文件路径>
```

## 参数

- `--source-file`: **必需**，源代码文件路径（相对或绝对路径）

## 输出格式

技能输出 JSON 格式的结果到标准输出：

```json
{
  "exists": true,
  "test_file_path": "/path/to/test/test_file.py",
  "test_case_count": 5,
  "last_modified": "2026-03-05T10:00:00Z"
}
```

### 字段说明

- `exists`: 布尔值，测试文件是否存在
- `test_file_path`: 字符串，推测或实际存在的测试文件路径
- `test_case_count`: 整数，测试用例数量（文件不存在时为 0）
- `last_modified`: 字符串，ISO 8601 格式的最后修改时间（文件不存在时为 null）

## 行为说明

### 1. 测试文件路径推断

根据源代码文件路径自动推断对应的测试文件路径：

1. 如果源代码文件在 `src/` 目录下，测试文件路径为：
   - `src/foo.py` → `tests/test_foo.py`
   - `src/utils/bar.py` → `tests/utils/test_bar.py`

2. 如果源代码文件在项目根目录或其他目录，测试文件路径为：
   - `foo.py` → `test_foo.py`
   - `utils/bar.py` → `utils/test_bar.py`

3. 支持自定义测试目录前缀（如 `test_` 是默认的）

### 2. 测试用例计数

如果测试文件存在，解析文件内容计算测试用例数量：

- **pytest 风格**: 统计所有以 `test_` 开头的函数
- **unittest 风格**: 统计 `unittest.TestCase` 子类中所有以 `test_` 开头的方法
- 如果同时存在两种风格，合并计数

### 3. 最后修改时间

使用文件系统的最后修改时间，格式化为 ISO 8601 字符串（UTC 时区）。

### 4. 错误处理

- 如果源代码文件不存在：返回错误信息并退出
- 如果测试文件不存在：`exists` 为 `false`，`test_case_count` 为 0，`last_modified` 为 null
- 如果测试文件存在但无法读取：`exists` 为 `true`，但 `test_case_count` 可能为 0

## 实现细节

技能使用 Python 脚本实现，执行以下步骤：

1. 验证源代码文件路径
2. 推断测试文件路径
3. 检查测试文件是否存在
4. 如果存在：
   - 解析文件统计测试用例
   - 获取最后修改时间
5. 输出 JSON 结果

## 示例

### 示例 1：测试文件存在

```bash
$ claude -s check-test-exists --source-file src/utils.py
{
  "exists": true,
  "test_file_path": "/project/tests/test_utils.py",
  "test_case_count": 8,
  "last_modified": "2026-03-05T14:30:22Z"
}
```

### 示例 2：测试文件不存在

```bash
$ claude -s check-test-exists --source-file src/new_module.py
{
  "exists": false,
  "test_file_path": "/project/tests/test_new_module.py",
  "test_case_count": 0,
  "last_modified": null
}
```

## 集成到测试流水线

此技能设计用于测试自动化流水线的决策阶段：

```python
# 伪代码示例
result = check_test_exists("src/my_module.py")
if result["exists"]:
    # 增量更新现有测试
    update_existing_tests(result["test_file_path"])
else:
    # 生成新测试文件
    generate_new_tests(result["test_file_path"])
```

## 技能执行流程

当使用此技能时，Claude 应该：

1. 验证 `--source-file` 参数是否提供
2. 调用 bundled script 执行检查：
   ```bash
   python scripts/check_test_exists.py --source-file "<source_file_path>"
   ```
3. 捕获脚本输出（JSON 格式）并呈现给用户
4. 如有错误，显示错误信息并建议解决方案

## 脚本说明

技能包含 `scripts/check_test_exists.py` 脚本，该脚本：
- 接受 `--source-file` 参数
- 输出 JSON 格式结果到标准输出
- 使用 Python 3.6+ 运行

如果用户需要自定义路径推断逻辑，可以修改脚本中的 `infer_test_path` 函数。

## 注意事项

1. 路径推断逻辑基于常见项目结构，可能不适用于所有项目
2. 测试用例计数基于简单的文本解析，可能无法处理复杂情况
3. 对于大型测试文件，解析可能需要一些时间
4. 技能不执行测试，仅检查文件存在性和基本信息