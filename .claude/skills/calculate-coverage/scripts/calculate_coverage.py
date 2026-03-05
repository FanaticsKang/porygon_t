#!/usr/bin/env python3
"""
Calculate test coverage and generate visual charts.

This script runs pytest with coverage, extracts line and branch coverage metrics,
and generates a visual chart showing coverage percentages.
"""

import os
import sys
import subprocess
import argparse
import re
from pathlib import Path
import json

try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Calculate test coverage and generate visual charts')
    parser.add_argument('--test-file', required=True, help='Path to the test file')
    parser.add_argument('--source-file', required=True, help='Path to the source code file being tested')
    parser.add_argument('--output-dir', required=True, help='Directory where coverage charts will be saved')
    return parser.parse_args()

def validate_paths(test_file, source_file):
    """Validate that the provided file paths exist."""
    if not os.path.exists(test_file):
        raise FileNotFoundError(f"Test file not found: {test_file}")
    if not os.path.exists(source_file):
        raise FileNotFoundError(f"Source file not found: {source_file}")

def run_coverage(test_file, source_file):
    """
    Run pytest with coverage and return coverage metrics.

    Returns:
        dict: Dictionary with 'line_coverage' and 'branch_coverage' percentages
    """
    # Get the module name from the source file path
    source_dir = os.path.dirname(source_file)
    source_module = os.path.splitext(os.path.basename(source_file))[0]

    # Use pytest with text output parsing (more reliable)
    cmd = [
        'pytest',
        test_file,
        f'--cov={source_module}',
        '--cov-report=term-missing',
        '--cov-branch',
        '-v'
    ]

    print(f"Running coverage analysis: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            cwd=source_dir,
            capture_output=True,
            text=True,
            check=False
        )
    except subprocess.CalledProcessError as e:
        print(f"Error running pytest: {e}")
        return {'line_coverage': 0.0, 'branch_coverage': 0.0}

    # Parse text output
    line_coverage, branch_coverage = parse_pytest_output(result.stdout, source_module)

    return {
        'line_coverage': line_coverage,
        'branch_coverage': branch_coverage,
        'stdout': result.stdout[:500] + '...' if len(result.stdout) > 500 else result.stdout,
        'stderr': result.stderr,
        'returncode': result.returncode
    }

def run_coverage_direct(test_file, source_file, source_dir, source_module):
    """Use coverage.py library directly for more reliable coverage calculation."""
    import coverage

    # Create coverage object
    cov = coverage.Coverage(source=[source_dir], branch=True)
    cov.start()

    # Run the tests
    try:
        import pytest
        pytest_args = [test_file, '-v']
        pytest.main(pytest_args)
    except Exception as e:
        print(f"Error running tests: {e}")
        return {'line_coverage': 0.0, 'branch_coverage': 0.0}
    finally:
        cov.stop()
        cov.save()

    # Analyze coverage
    cov.load()

    # Get coverage for the specific source file
    source_abs_path = os.path.abspath(source_file)
    line_coverage = 0.0
    branch_coverage = 0.0

    # Get coverage data
    analysis = cov.analysis2(source_abs_path) if hasattr(cov, 'analysis2') else None

    if analysis:
        # analysis2 returns (nums, analyzed, excluded, missing, missing_branches)
        # nums is (n_statements, n_excluded, n_missing, n_branches, n_partial_branches)
        if len(analysis) >= 5:
            nums = analysis[0]
            if len(nums) >= 5:
                n_statements = nums[0]
                n_missing = nums[2]
                n_branches = nums[3]
                n_missing_branches = analysis[4] if len(analysis) > 4 else []

                if n_statements > 0:
                    line_coverage = (n_statements - len(n_missing)) / n_statements * 100

                if n_branches > 0:
                    branch_coverage = (n_branches - len(n_missing_branches)) / n_branches * 100

    # Fallback: use get_data() method
    if line_coverage == 0.0:
        data = cov.get_data()
        lines = data.lines(source_abs_path) if source_abs_path in data.measured_files() else []
        arcs = data.arcs(source_abs_path) if hasattr(data, 'arcs') else None

        # Simple calculation
        if lines:
            # This is simplified - would need more complex logic for accurate coverage
            line_coverage = 100.0  # Placeholder

    return {
        'line_coverage': line_coverage,
        'branch_coverage': branch_coverage,
        'stdout': 'Coverage calculated using coverage.py library',
        'stderr': '',
        'returncode': 0
    }

def parse_pytest_output(output, source_module):
    """Parse pytest coverage output."""
    line_coverage = 0.0
    branch_coverage = 0.0

    # Look for the coverage table
    lines = output.split('\n')
    in_coverage_table = False

    for line in lines:
        # Check if we're entering the coverage table
        if 'Name' in line and 'Stmts' in line and 'Miss' in line and 'Branch' in line:
            in_coverage_table = True
            continue

        if in_coverage_table:
            # Look for the specific file
            if source_module in line and '.py' in line:
                # Parse the line: "calculator.py      14      0      2      0   100%"
                parts = line.split()
                if len(parts) >= 6:
                    try:
                        line_coverage = float(parts[-1].replace('%', ''))
                        # Branch coverage is more complex - need to calculate from Branch and BrPart
                        if len(parts) >= 5:
                            branch = int(parts[3]) if parts[3].isdigit() else 0
                            brpart = int(parts[4]) if parts[4].isdigit() else 0
                            if branch > 0:
                                branch_coverage = (branch - brpart) / branch * 100
                    except ValueError:
                        pass
                break

            # Check for end of table
            if line.strip().startswith('---') and len(line.strip()) > 10:
                continue
            if not line.strip() or '===' in line:
                in_coverage_table = False

    return line_coverage, branch_coverage

def extract_coverage_from_file(source_dir):
    """Extract coverage from .coverage file using coverage.py."""
    try:
        import coverage
        cov = coverage.Coverage(data_file=os.path.join(source_dir, '.coverage'))
        cov.load()

        # Get coverage report
        report_data = cov.get_data()

        # Calculate line coverage for the specific file
        # This is simplified - in practice would need to analyze specific file
        line_coverage = 0.0
        branch_coverage = 0.0

        # Return default values
        return line_coverage, branch_coverage
    except ImportError:
        print("coverage.py not available for detailed analysis")
        return 0.0, 0.0
    except Exception as e:
        print(f"Error extracting coverage from file: {e}")
        return 0.0, 0.0

def generate_coverage_chart(line_coverage, branch_coverage, source_file, output_dir):
    """Generate a bar chart showing coverage metrics."""
    if not HAS_MATPLOTLIB:
        print("Matplotlib not available, skipping chart generation")
        return None

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Get source file name for chart title
    source_name = os.path.splitext(os.path.basename(source_file))[0]

    # Prepare data
    metrics = ['Line Coverage', 'Branch Coverage']
    values = [line_coverage, branch_coverage]
    colors = ['#2E86AB', '#A23B72']

    # Create figure
    plt.figure(figsize=(10, 6))

    # Create bar chart
    bars = plt.bar(metrics, values, color=colors, edgecolor='black', linewidth=1.5)

    # Add value labels on bars
    for bar, value in zip(bars, values):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 1,
                f'{value:.1f}%', ha='center', va='bottom', fontsize=12, fontweight='bold')

    # Customize chart
    plt.title(f'Test Coverage Analysis: {source_name}', fontsize=16, fontweight='bold', pad=20)
    plt.ylabel('Coverage Percentage (%)', fontsize=14)
    plt.ylim(0, 105)  # Set y-axis limit to 105% to accommodate labels

    # Add grid
    plt.grid(axis='y', alpha=0.3, linestyle='--')

    # Add target line at 90%
    plt.axhline(y=90, color='red', linestyle='--', alpha=0.5, label='Target (90%)')
    plt.legend()

    # Adjust layout
    plt.tight_layout()

    # Save chart
    chart_filename = f'coverage_{source_name}.png'
    chart_path = os.path.join(output_dir, chart_filename)
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"Coverage chart saved to: {chart_path}")
    return chart_path

def main():
    """Main function."""
    args = parse_arguments()

    try:
        # Validate paths
        validate_paths(args.test_file, args.source_file)

        # Run coverage analysis
        coverage_data = run_coverage(args.test_file, args.source_file)

        # Extract coverage percentages
        line_coverage = coverage_data['line_coverage']
        branch_coverage = coverage_data['branch_coverage']

        # Print coverage results
        print("\n" + "="*50)
        print("COVERAGE RESULTS")
        print("="*50)
        print(f"Line coverage: {line_coverage:.1f}%")
        print(f"Branch coverage: {branch_coverage:.1f}%")
        print("="*50 + "\n")

        # Generate chart
        chart_path = generate_coverage_chart(
            line_coverage, branch_coverage,
            args.source_file, args.output_dir
        )

        # Output structured results for Claude skill
        results = {
            'line_coverage': f"{line_coverage:.1f}%",
            'branch_coverage': f"{branch_coverage:.1f}%",
            'chart_generated': chart_path is not None,
            'chart_path': chart_path
        }

        # Print JSON results for machine parsing
        print("\n" + "="*50)
        print("STRUCTURED RESULTS (JSON)")
        print("="*50)
        print(json.dumps(results, indent=2))

        # Return exit code based on test results
        if coverage_data.get('returncode', 0) != 0:
            print(f"\nWarning: Tests exited with code {coverage_data.get('returncode', 0)}")
            return 1

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())