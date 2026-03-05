# porygon_t - Claude Agents & Skills 设计规划

> 基于 plan.md 的流水线设计，分析需要创建的 Claude Agents 和 Skills

---

## 核心架构

```
porygon_t.py (Python编排层)
    ↓ 调用 Claude CLI
Claude Agents (执行AI任务 - 需LLM推理)
    ↓ 使用
Claude Skills (原子操作 - 确定性逻辑)
```

---

## 一、Agents 设计

### 1. test-plan-generator
**职责**: 分析代码结构，生成测试方案文档

**对应流水线阶段**: 阶段3 - 计划阶段

**输入**:
- `program_<file1>_config.json` 或 `<file2>_config.json`
- 目标源代码文件

**输出**:
- `test_plan_program_<file1>.md` - 用户指定程序的测试方案
- `test_plan_case_<file2>.md` - commit diff文件的测试方案

**核心任务**:
- 解析Python文件，提取函数/类定义
- 分析关键逻辑分支、边界条件、异常处理点
- 分析git diff变更影响（针对commit diff文件）
- 设计测试用例覆盖策略（正向/边界/异常/回归）

**说明**：
- 此·agent·始终使用`ultrathink`模式

---

### 2. test-code-generator
**职责**: 基于测试方案生成或更新测试代码

**对应流水线阶段**: 阶段4 - 生成阶段

**输入**:
- `test_plan_*.md` 测试方案
- 目标源代码文件
- 已存在的测试文件（如有，用于增量更新）

**输出**:
- `test_<file>.py` - 生成或更新的测试代码

**核心任务**:
- 根据测试方案实现具体测试用例
- 使用pytest框架
- 支持增量更新：识别已有测试，补充缺失用例
- 确保测试代码可执行、命名规范

---

### 3. test-report-analyzer
**职责**: 分析单个文件的测试结果，生成详细分析报告

**对应流水线阶段**: 阶段5 - 报告阶段（单文件）

**输入**:
- `<file>_summary.md` - 测试执行摘要
- `fig/` 目录下的覆盖率图表
- 测试代码文件
- 目标源代码文件

**输出**:
- `<file>_report.md` - 详细分析报告
- `program_<file>_report.md` - 用户指定程序的报告

**核心任务**:
- 分析测试用例执行情况
- 解读覆盖率报告
- 分析失败用例原因
- 提供代码改进建议
- 评估是否通过测试评估

---

### 4. summary-report-generator
**职责**: 汇总所有文件测试结果，生成总体测试报告

**对应流水线阶段**: 阶段6 - 报告阶段（总体）

**输入**:
- 所有 `*_summary.md` 文件
- 所有 `*_report.md` 文件
- `fig/` 目录下的覆盖率图表
- `test_plan.json` 原始配置

**输出**:
- `summary_report.md` - 总体测试报告

**核心任务**:
- 汇总统计所有测试用例数据
- 计算平均/最低/最高覆盖率
- 识别失败用例和低覆盖率文件
- 生成质量评估结论
- 提供合并建议和后续行动建议

---

## 二、Skills 设计

### 1. run-tests
**职责**: 执行pytest测试并生成结构化摘要

**使用阶段**: 阶段5 - 执行阶段

**输入参数**:
- `--test-file`: 测试文件路径
- `--output`: summary.md输出路径
- `--coverage-target`: 被测源代码路径（用于计算覆盖率）

**输出**:
- 执行测试并生成 `<file>_summary.md`
- 生成覆盖率图表到 `fig/` 目录

**功能**:
- 执行pytest并收集结果
- 计算行覆盖率、分支覆盖率
- 生成matplotlib覆盖率图表
- 输出结构化summary（支持--summary选项格式）

---

### 2. check-test-exists
**职责**: 检查测试文件是否存在及基本信息

**使用阶段**: 阶段4 - 生成阶段（决策分支）

**输入参数**:
- `--source-file`: 被测源代码路径

**输出**: JSON格式
```json
{
  "exists": true,
  "test_file_path": "/path/to/test/test_file.py",
  "test_case_count": 5,
  "last_modified": "2026-03-05T10:00:00"
}
```

---

### 3. parse-python-ast
**职责**: 解析Python文件AST，提取结构化信息

**使用阶段**: 阶段3 - 辅助生成测试方案

**输入参数**:
- `--file`: Python文件路径
- `--output-format`: json/markdown

**输出**: 结构化信息
- 函数列表（名称、参数、返回值注解）
- 类列表（方法、继承关系）
- 导入语句
- 异常处理块
- 条件分支点

---

### 4. calculate-coverage
**职责**: 计算测试覆盖率并生成可视化图表

**使用阶段**: 阶段5 - 测试执行后

**输入参数**:
- `--test-file`: 测试文件路径
- `--source-file`: 被测源代码路径
- `--output-dir`: 图表输出目录

**输出**:
- 行覆盖率百分比
- 分支覆盖率百分比
- `fig/coverage_<file>.png` 可视化图表

---

## 三、关键设计决策

### 3.1 Agent vs Skill 边界

| 维度 | Agent | Skill |
|------|-------|-------|
| 是否需要LLM推理 | ✅ 需要 | ❌ 不需要 |
| 输入输出 | 非结构化/半结构化 | 结构化/确定性 |
| 典型任务 | 分析、设计、生成代码 | 执行命令、解析数据、文件操作 |
| 示例 | 生成测试方案、分析报告 | 运行pytest、检查文件存在性 |

### 3.2 主程序调用方式

```python
# porygon_t.py 中调用 Claude CLI 的方式建议：

# 1. 生成测试方案 - Agent
subprocess.run([
    "claude", "-a", "test-plan-generator",
    "--input", config_json,
    "--output", plan_md
])

# 2. 生成测试代码 - Agent
subprocess.run([
    "claude", "-a", "test-code-generator",
    "--plan", plan_md,
    "--test-file", test_py
])

# 3. 执行测试 - Skill
subprocess.run([
    "claude", "-s", "run-tests",
    "--test-file", test_py,
    "--output", summary_md
])

# 4. 生成报告 - Agent
subprocess.run([
    "claude", "-a", "test-report-analyzer",
    "--summary", summary_md,
    "--output", report_md
])
```

### 3.3 为什么不用 Orchestrator Agent

保持 `porygon_t.py` 作为主编排器，而非创建orchestrator agent：

| 方案 | 优点 | 缺点 |
|------|------|------|
| Python编排 | 调试简单、状态管理灵活、CI/CD集成直接 | 需要维护Python代码 |
| Agent编排 | 更"AI原生" | 调试困难、prompt复杂、错误恢复难 |

**结论**: 当前设计下Python编排更合适。

---

## 四、实现路线图

### Phase 1: 核心链路（MVP）
1. **test-code-generator** agent - 直接根据代码生成测试
2. **run-tests** skill - 执行测试并生成摘要

目标: 能跑通单个文件的测试生成和执行

### Phase 2: 方案生成
3. **test-plan-generator** agent - 先生成方案再生成代码
4. **parse-python-ast** skill - 辅助方案生成

目标: 支持基于方案的测试生成

### Phase 3: 报告系统
5. **test-report-analyzer** agent - 单文件报告
6. **calculate-coverage** skill - 覆盖率可视化

目标: 完整的单文件测试闭环

### Phase 4: 汇总能力
7. **summary-report-generator** agent - 总体报告
8. **check-test-exists** skill - 增量更新支持

目标: 完整的流水线闭环

---

## 五、文件位置规划

```
~/.claude/
├── agents/
│   ├── test-plan-generator.md         # Agent定义
│   ├── test-code-generator.md
│   ├── test-report-analyzer.md
│   └── summary-report-generator.md
└── skills/
    ├── run-tests/
    │   └── skill.yaml
    ├── check-test-exists/
    │   └── skill.yaml
    ├── parse-python-ast/
    │   └── skill.yaml
    └── calculate-coverage/
        └── skill.yaml
```

---

## 六、待确认问题

1. **模型选择**: 是否所有agent都使用同一模型？测试生成是否需要更强的模型（Opus）？
2. **并行限制**: Claude CLI的并行调用是否需要限制？是否需要排队机制？
3. **错误恢复**: 某个agent失败时，是否需要重试机制？如何记录失败状态？
4. **增量更新**: 测试代码的增量更新策略具体如何实现？基于AST对比还是文本对比？

---

*生成时间: 2026-03-05*
*基于: plan.md 流水线设计*
