---
name: run-tests
description: "Use this skill when you need to execute Python pytest tests, calculate code coverage, generate matplotlib visualizations, and create structured summary reports. This skill handles the entire test execution workflow including running tests with coverage metrics, creating visual charts, and producing markdown summaries. It's designed for testing pipelines where automated test execution and reporting is needed. Use this skill whenever the user mentions running tests, executing pytest, generating test summaries, calculating code coverage, creating coverage charts, or needs structured test results. This is particularly useful in CI/CD pipelines, automated testing workflows, and quality assurance processes."
---

# Run Tests Skill

This skill executes Python pytest tests, calculates code coverage, generates visualizations, and creates structured summary reports.

## Core Functionality

When invoked, this skill will:

1. **Execute pytest tests** with coverage analysis
2. **Calculate coverage metrics** (line coverage, branch coverage)
3. **Generate matplotlib charts** for coverage visualization
4. **Create structured summary files** in markdown format

## Usage Parameters

The skill accepts these command-line arguments:

- `--test-file`: Path to the pytest test file to execute (required)
- `--coverage-target`: Path to the source code being tested (optional, defaults to parent directory of test file)
- `--output=<out_dir>`: Output directory for summary files and charts (required)
  - Creates `<out_dir>/<file>_summary.md` for test summary
  - Creates `<out_dir>/fig/` directory for charts

## How It Works

The skill uses the bundled `run_tests.py` script to handle the complete workflow:

### 1. Test Execution
The script runs pytest with coverage collection:
```bash
pytest <test_file> --cov=<coverage_target> --cov-report=term --cov-report=html --cov-report=xml
```

### 2. Coverage Analysis
Parses pytest output to extract:
- Line coverage percentage
- Branch coverage percentage
- Number of statements covered vs total
- Test execution statistics (passed, failed, skipped, etc.)

### 3. Chart Generation
Creates matplotlib visualizations in the `fig/` directory:
- `coverage_summary.png`: Bar chart showing line and branch coverage percentages

### 4. Summary File Creation
Generates a structured markdown summary with:
- Executive summary with pass/fail status
- Detailed test results table
- Coverage metrics table
- Generated charts embedded as images
- Actionable recommendations based on results
- Raw test output for debugging

## Required Dependencies

Ensure these Python packages are installed:
```bash
pip install pytest pytest-cov matplotlib
```

## Output Structure

```
<output_dir>/
├── <file>_summary.md          # Structured test summary
└── fig/                       # Generated charts
    └── coverage_summary.png   # Coverage bar chart
```

## Example Usage

```bash
# Run tests for test_calculator.py and generate summary
claude -s run-tests --test-file test_calculator.py --output=./test_results

# Run tests with specific coverage target
claude -s run-tests --test-file test_utils.py --coverage-target=./src/utils.py --output=./results
```

## Implementation Instructions

When using this skill, follow these steps:

1. **Check dependencies**: Ensure `pytest`, `pytest-cov`, and `matplotlib` are installed
2. **Execute the script**: Run the bundled `run_tests.py` script with the required parameters
3. **Review outputs**: Check the generated summary and charts

**Example implementation in Claude**:

```python
# Check if dependencies are installed
import subprocess
import sys

def check_dependencies():
    try:
        subprocess.run([sys.executable, "-m", "pytest", "--version"],
                      capture_output=True, check=True)
        print("✓ pytest is installed")
    except:
        print("✗ pytest not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pytest", "pytest-cov", "matplotlib"])

# Run the tests using the skill script
import os
script_path = os.path.expanduser("~/.claude/skills/run-tests/scripts/run_tests.py")
cmd = [
    sys.executable, script_path,
    "--test-file", "test_calculator.py",
    "--coverage-target", "calculator.py",
    "--output", "./test_results"
]

result = subprocess.run(cmd, capture_output=True, text=True)
print(result.stdout)
if result.returncode != 0:
    print(f"Error: {result.stderr}")
```

## Skill Script Location

The core implementation is in `~/.claude/skills/run-tests/scripts/run_tests.py`. When the skill is triggered, read and execute this script to perform the test execution.

## Implementation Details

The skill follows these steps:

1. **Validate inputs**: Check that test file exists and output directory can be created
2. **Execute tests**: Run pytest with coverage collection
3. **Parse results**: Extract test statistics and coverage metrics from pytest output
4. **Generate charts**: Use matplotlib to create visualizations of coverage data
5. **Write summary**: Create structured markdown file with all test results
6. **Clean up**: Ensure all files are properly saved and accessible

## Error Handling

- If pytest fails, the skill captures error output and includes it in the summary
- If matplotlib is not available, chart generation is skipped with a warning
- If coverage cannot be calculated, metrics are marked as "N/A"

## Best Practices

1. **Run tests in isolation**: Ensure test environment is clean before execution
2. **Review coverage gaps**: Use the generated charts to identify untested code paths
3. **Integrate with CI/CD**: This skill is designed to work in automated pipelines
4. **Track trends**: Save historical summaries to monitor coverage improvements over time

## Notes

- The skill assumes pytest and pytest-cov are properly configured in the project
- Coverage analysis works best when tests are run against the actual source code
- Chart generation requires matplotlib; install it if visualizations are needed
- Summary files are designed to be human-readable and machine-parseable