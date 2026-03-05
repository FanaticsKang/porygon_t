#!/usr/bin/env python3
"""
Run Tests Script

This script executes pytest tests with coverage analysis, generates visualizations,
and creates structured summary reports.
"""

import argparse
import subprocess
import sys
import os
import json
from pathlib import Path
import matplotlib.pyplot as plt
from datetime import datetime

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run pytest tests with coverage analysis')
    parser.add_argument('--test-file', required=True, help='Path to pytest test file')
    parser.add_argument('--coverage-target', help='Path to source code for coverage analysis')
    parser.add_argument('--output', required=True, help='Output directory for results')
    return parser.parse_args()

def validate_inputs(args):
    """Validate input files and directories."""
    test_file = Path(args.test_file)
    if not test_file.exists():
        print(f"Error: Test file not found: {test_file}")
        return False

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create fig subdirectory
    fig_dir = output_dir / "fig"
    fig_dir.mkdir(exist_ok=True)

    return True

def run_pytest_with_coverage(test_file, coverage_target, output_dir):
    """Run pytest with coverage collection."""
    cmd = [
        sys.executable, "-m", "pytest",
        str(test_file),
        "-v",
        "--tb=short"
    ]

    if coverage_target:
        cmd.extend([
            f"--cov={coverage_target}",
            "--cov-branch",
            "--cov-report=term",
            "--cov-report=html",
            "--cov-report=xml"
        ])
    else:
        # If no coverage target specified, use the directory containing the test file
        test_dir = Path(test_file).parent
        cmd.extend([
            f"--cov={test_dir}",
            "--cov-branch",
            "--cov-report=term",
            "--cov-report=html",
            "--cov-report=xml"
        ])

    print(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        }
    except subprocess.CalledProcessError as e:
        return {
            "returncode": e.returncode,
            "stdout": e.stdout,
            "stderr": e.stderr,
            "success": False
        }
    except FileNotFoundError:
        print("Error: pytest not found. Please install pytest and pytest-cov.")
        return {
            "returncode": 1,
            "stdout": "",
            "stderr": "pytest not found",
            "success": False
        }

def parse_coverage_from_output(output):
    """Parse coverage metrics from pytest output."""
    coverage_data = {
        "line_coverage": None,
        "branch_coverage": None,
        "statements_covered": None,
        "statements_total": None
    }

    lines = output.split('\n')
    in_coverage_section = False

    for line in lines:
        line = line.strip()

        # Check if we're in the coverage section
        if "coverage:" in line.lower():
            in_coverage_section = True
            continue

        if in_coverage_section:
            # Look for TOTAL line
            if line.startswith("TOTAL") or line.startswith("---") and "TOTAL" in lines[lines.index(line)+1]:
                # Find the TOTAL line
                for i in range(min(3, len(lines) - lines.index(line))):
                    check_line = lines[lines.index(line) + i].strip()
                    if check_line.startswith("TOTAL"):
                        parts = check_line.split()
                        if len(parts) >= 4:
                            try:
                                coverage_data["statements_total"] = int(parts[-3])
                                coverage_data["statements_covered"] = int(parts[-2])
                                coverage_percent = parts[-1].replace('%', '')
                                coverage_data["line_coverage"] = float(coverage_percent)
                            except (ValueError, IndexError):
                                pass
                        break

            # Look for branch coverage
            if "branch" in line.lower() and "%" in line:
                import re
                match = re.search(r'(\d+\.?\d*)%', line)
                if match:
                    try:
                        coverage_data["branch_coverage"] = float(match.group(1))
                    except ValueError:
                        pass

    return coverage_data

def parse_test_results(output):
    """Parse test execution results from pytest output."""
    results = {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "xfailed": 0,
        "xpassed": 0,
        "error": 0,
        "total": 0,
        "duration": 0.0
    }

    lines = output.split('\n')

    # Look for the summary line that contains test counts
    # Example: "=== 8 passed, 1 skipped, 1 xfailed in 0.07s ==="
    for line in lines:
        line = line.strip().lower()

        # Check if this is a summary line with test counts
        if ("passed" in line or "failed" in line or "skipped" in line or
            "error" in line or "xfailed" in line or "xpassed" in line):

            # Try to extract numbers before each test type
            import re

            # Look for patterns like "X passed", "Y failed", etc.
            passed_match = re.search(r'(\d+)\s+passed', line)
            failed_match = re.search(r'(\d+)\s+failed', line)
            skipped_match = re.search(r'(\d+)\s+skipped', line)
            error_match = re.search(r'(\d+)\s+error', line)
            xfailed_match = re.search(r'(\d+)\s+xfailed', line)
            xpassed_match = re.search(r'(\d+)\s+xpassed', line)

            if passed_match:
                results["passed"] = int(passed_match.group(1))
            if failed_match:
                results["failed"] = int(failed_match.group(1))
            if skipped_match:
                results["skipped"] = int(skipped_match.group(1))
            if error_match:
                results["error"] = int(error_match.group(1))
            if xfailed_match:
                results["xfailed"] = int(xfailed_match.group(1))
            if xpassed_match:
                results["xpassed"] = int(xpassed_match.group(1))

            # Also try to extract duration - supports both "in 0.04s" and "in 0.04 seconds"
            duration_match = re.search(r'in\s+(\d+\.\d+)\s*s(?:econds?)?', line)
            if duration_match:
                results["duration"] = float(duration_match.group(1))

    # Calculate total
    results["total"] = sum([
        results["passed"], results["failed"], results["skipped"],
        results["xfailed"], results["xpassed"], results["error"]
    ])

    return results

def generate_coverage_chart(coverage_data, output_path):
    """Generate matplotlib coverage chart."""
    try:
        categories = ['Line Coverage', 'Branch Coverage']
        values = [
            coverage_data.get('line_coverage', 0) or 0,
            coverage_data.get('branch_coverage', 0) or 0
        ]

        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(categories, values, color=['#2ecc71', '#3498db'])

        # Add value labels on bars
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                   f'{value:.1f}%', ha='center', va='bottom')

        ax.set_ylim(0, 100)
        ax.set_ylabel('Coverage Percentage (%)')
        ax.set_title('Test Coverage Summary')
        ax.grid(axis='y', alpha=0.3)

        # Add target line at 80%
        ax.axhline(y=80, color='r', linestyle='--', alpha=0.5, label='Target (80%)')
        ax.legend()

        plt.tight_layout()
        plt.savefig(output_path, dpi=100)
        plt.close()

        print(f"Coverage chart saved to: {output_path}")
        return True
    except Exception as e:
        print(f"Warning: Could not generate coverage chart: {e}")
        return False

def generate_summary_markdown(test_file, test_results, coverage_data, pytest_output, output_path):
    """Generate structured markdown summary file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    test_filename = Path(test_file).name

    with open(output_path, 'w') as f:
        f.write(f"# Test Execution Summary: {test_filename}\n\n")
        f.write(f"**Generated**: {timestamp}\n\n")

        f.write("## Executive Summary\n\n")
        f.write(f"- **Test File**: `{test_file}`\n")
        f.write(f"- **Execution Status**: {'✅ PASSED' if test_results['failed'] == 0 and test_results['error'] == 0 else '❌ FAILED'}\n")
        f.write(f"- **Total Tests**: {test_results['total']}\n")
        f.write(f"- **Duration**: {test_results['duration']:.2f} seconds\n\n")

        f.write("## Test Results\n\n")
        f.write("| Metric | Count |\n")
        f.write("|--------|-------|\n")
        f.write(f"| Passed | {test_results['passed']} |\n")
        f.write(f"| Failed | {test_results['failed']} |\n")
        f.write(f"| Skipped | {test_results['skipped']} |\n")
        f.write(f"| XFailed | {test_results['xfailed']} |\n")
        f.write(f"| XPassed | {test_results['xpassed']} |\n")
        f.write(f"| Error | {test_results['error']} |\n")
        f.write(f"| **Total** | **{test_results['total']}** |\n\n")

        if coverage_data['line_coverage'] is not None:
            f.write("## Coverage Analysis\n\n")
            f.write("| Metric | Value |\n")
            f.write("|--------|-------|\n")
            f.write(f"| Line Coverage | {coverage_data['line_coverage']:.1f}% |\n")
            if coverage_data['branch_coverage'] is not None:
                f.write(f"| Branch Coverage | {coverage_data['branch_coverage']:.1f}% |\n")
            if coverage_data['statements_covered'] is not None and coverage_data['statements_total'] is not None:
                f.write(f"| Statements Covered | {coverage_data['statements_covered']}/{coverage_data['statements_total']} |\n")

        f.write("\n## Generated Charts\n\n")
        fig_dir = Path(output_path).parent / "fig"
        coverage_chart = fig_dir / "coverage_summary.png"
        if coverage_chart.exists():
            f.write(f"![Coverage Summary](./fig/coverage_summary.png)\n\n")
            f.write(f"*Coverage summary chart generated at {timestamp}*\n\n")

        f.write("## Recommendations\n\n")

        if test_results['failed'] > 0 or test_results['error'] > 0:
            f.write("❌ **Issues Found**:\n")
            f.write("- Investigate failed tests\n")
            f.write("- Check for test environment issues\n")
            f.write("- Review error messages below\n\n")

        if coverage_data['line_coverage'] is not None and coverage_data['line_coverage'] < 80:
            f.write("⚠️ **Coverage Improvements Needed**:\n")
            f.write(f"- Current line coverage ({coverage_data['line_coverage']:.1f}%) is below 80% target\n")
            f.write("- Add tests for uncovered code paths\n")
            f.write("- Consider edge cases and boundary conditions\n\n")
        elif coverage_data['line_coverage'] is not None and coverage_data['line_coverage'] >= 80:
            f.write("✅ **Good Coverage**:\n")
            f.write(f"- Line coverage ({coverage_data['line_coverage']:.1f}%) meets target\n")
            f.write("- Maintain current test quality\n\n")

        f.write("## Raw Test Output\n\n")
        f.write("```\n")
        # Include relevant parts of pytest output
        lines = pytest_output.split('\n')
        # Show last 50 lines or all if less
        start = max(0, len(lines) - 50)
        for line in lines[start:]:
            f.write(line + "\n")
        f.write("```\n\n")

        f.write("---\n")
        f.write("*Generated by run-tests skill*\n")

def main():
    """Main execution function."""
    args = parse_arguments()

    if not validate_inputs(args):
        sys.exit(1)

    print(f"Running tests for: {args.test_file}")
    print(f"Output directory: {args.output}")

    # Run pytest with coverage
    pytest_result = run_pytest_with_coverage(
        args.test_file,
        args.coverage_target,
        args.output
    )

    # Parse results
    test_results = parse_test_results(pytest_result["stdout"])
    coverage_data = parse_coverage_from_output(pytest_result["stdout"])

    # Generate charts
    fig_dir = Path(args.output) / "fig"
    chart_path = fig_dir / "coverage_summary.png"

    if coverage_data['line_coverage'] is not None:
        generate_coverage_chart(coverage_data, chart_path)

    # Generate summary markdown
    test_filename = Path(args.test_file).stem
    summary_path = Path(args.output) / f"{test_filename}_summary.md"

    generate_summary_markdown(
        args.test_file,
        test_results,
        coverage_data,
        pytest_result["stdout"],
        summary_path
    )

    # Print summary
    print("\n" + "="*60)
    print("TEST EXECUTION COMPLETE")
    print("="*60)
    print(f"Test File: {args.test_file}")
    print(f"Status: {'PASSED' if test_results['failed'] == 0 and test_results['error'] == 0 else 'FAILED'}")
    print(f"Tests: {test_results['passed']} passed, {test_results['failed']} failed, {test_results['skipped']} skipped")
    if coverage_data['line_coverage'] is not None:
        print(f"Line Coverage: {coverage_data['line_coverage']:.1f}%")
    print(f"Duration: {test_results['duration']:.2f} seconds")
    print(f"Summary: {summary_path}")
    if chart_path.exists():
        print(f"Chart: {chart_path}")
    print("="*60)

    # Return non-zero exit code if tests failed
    if test_results['failed'] > 0 or test_results['error'] > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()