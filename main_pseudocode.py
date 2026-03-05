def main():
    # 1. 初始化
    config = load_test_plan("test_plan.json")
    workers = config.execution.maxWorkers

    # 2. 发现待测试文件
    targets = []
    targets += get_commit_diff_files(config.commit_id)      # commit diff 文件
    targets += config.test_programs                          # 用户指定文件

    ## 2.1 生成program_<file_name>_config.json和<file_name>_config.json
    create_config_files(targets) 

    # 3. 生成测试方案（可并行）
    plans = []
    for target in targets:
        plan = generate_test_plan(target)    # 调用 Claude Agent Team 生成 test_plan_*.md，使用不同测试角色
        plans.append(plan)

    # 4. 生成/更新测试代码（可并行）
    for plan in plans:
        if test_file_exists(plan.test_file_path):
            update_tests(plan)               # 增量更新现有测试
        else:
            generate_tests(plan)             # 创建新测试文件

    # 5. 执行测试（可并行），执行之后会生成测试_summary.md
    results = []
    for plan in plans:
        result = run_tests(plan.test_file_path)
        result.create_summary()
        result.create_report() # 调用Claude模型生成 program_<file_name>_report.md或者<file_name>_report.md
        results.append(result)

    # 6. 生成报告（调用 Claude）
    generate_summary_report(results)
