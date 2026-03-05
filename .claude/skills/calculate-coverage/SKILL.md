---
name: calculate-coverage
description: |
  Calculate test coverage for Python code and generate visual charts.

  Use this skill when the user needs to compute line and branch coverage for Python tests,
  generate coverage percentage reports, and create visual charts showing coverage metrics.
  This skill is particularly useful in testing pipelines, CI/CD workflows, and quality
  assurance processes where automated coverage analysis and visualization are needed.

  Trigger this skill when the user mentions:
  - Calculating test coverage
  - Generating coverage reports
  - Creating coverage visualizations
  - Measuring line or branch coverage
  - Analyzing test coverage metrics
  - Visualizing coverage data with charts
  - Running coverage analysis for Python tests

  The skill takes a test file and source code file as input, runs coverage analysis,
  and outputs coverage percentages along with visual charts in the specified directory.
compatibility:
  tools:
    - Bash
    - Read
    - Write
    - Edit
  dependencies:
    - Python 3.6+
    - pytest
    - pytest-cov
    - coverage
    - matplotlib (for chart generation)
---

# Calculate Coverage Skill

This skill calculates test coverage for Python code and generates visual charts showing coverage metrics.

## Purpose

The skill provides automated test coverage analysis for Python projects, calculating both line and branch coverage percentages and creating visual charts to help understand coverage distribution.

## How to Use

When you need to calculate test coverage, follow these steps:

1. **Check prerequisites**: Ensure the target Python environment has `pytest`, `pytest-cov`, `coverage`, and `matplotlib` installed. You can install them with:
   ```bash
   pip install pytest pytest-cov coverage matplotlib
   ```

2. **Execute the skill**: Run the skill with the required parameters:
   ```bash
   python skills/calculate-coverage/scripts/calculate_coverage.py \
     --test-file /path/to/test/test_auth.py \
     --source-file /path/to/src/auth.py \
     --output-dir ./fig/
   ```

   **Required parameters**:
   - `--test-file`: Path to the test file (e.g., `test_auth.py`)
   - `--source-file`: Path to the source code file being tested (e.g., `auth.py`)
   - `--output-dir`: Directory where coverage charts will be saved (e.g., `./fig/`)

3. **Interpret results**: The skill outputs:
   - Line and branch coverage percentages in human-readable format
   - A structured JSON output with coverage metrics
   - A visual chart saved to the specified output directory (if matplotlib is available)

## Implementation Details

The skill performs the following operations:

1. **Run coverage analysis**: Uses `pytest --cov` to execute tests and collect coverage data
2. **Extract coverage metrics**: Parses coverage output to get line and branch coverage percentages
3. **Generate visual charts**: Creates bar charts showing coverage metrics using matplotlib
4. **Save results**: Outputs coverage percentages and saves charts to the output directory

The main implementation is in `scripts/calculate_coverage.py`. When using this skill as Claude, you should:

1. First check if the required dependencies are installed
2. Call the script using the Bash tool
3. Parse the output to extract coverage percentages
4. Reference the generated chart in your response

## Output Format

The skill produces:

1. **Human-readable output**:
   ```
   ==================================================
   COVERAGE RESULTS
   ==================================================
   Line coverage: 92.5%
   Branch coverage: 87.3%
   ==================================================
   ```

2. **Structured JSON output** (for machine parsing):
   ```json
   {
     "line_coverage": "92.5%",
     "branch_coverage": "87.3%",
     "chart_generated": true,
     "chart_path": "./fig/coverage_auth.png"
   }
   ```

3. **Visual chart**: `coverage_<source_file_name>.png` saved in the specified output directory

## Example Claude Usage

When using this skill as Claude, here's how to structure your response:

```bash
# First, check if dependencies are installed
python -c "import pytest, coverage, matplotlib" 2>/dev/null || echo "Dependencies missing"

# Then run the coverage calculation
python skills/calculate-coverage/scripts/calculate_coverage.py \
  --test-file /path/to/test/test_auth.py \
  --source-file /path/to/src/auth.py \
  --output-dir ./fig/
```

**After running the script, present the results clearly:**

```
## Coverage Analysis Results

- **Line coverage**: 92.5%
- **Branch coverage**: 87.3%

Coverage chart generated and saved to: `./fig/coverage_auth.png`

The chart shows a visual comparison of line vs branch coverage, with a target line at 90% for reference.
```

## Notes

- The output directory will be created if it doesn't exist
- If matplotlib is not available, the skill will still calculate coverage percentages but skip chart generation
- For multi-file coverage analysis, run the skill separately for each source file or consider using the `run-tests` skill which handles batch processing
- The script expects the test file and source file to exist; it will validate paths before running
- Test failures don't stop coverage calculation (coverage is calculated based on what was executed)

## Error Handling

Common errors and solutions:

1. **File not found**: Check that both test and source file paths are correct
2. **Missing dependencies**: Install required packages with `pip install pytest pytest-cov coverage matplotlib`
3. **Permission issues**: Ensure you have execute permissions for the Python script
4. **Chart generation failure**: If matplotlib fails, coverage percentages will still be calculated