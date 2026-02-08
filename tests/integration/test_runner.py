"""
SPDX-License-Identifier: MIT
Copyright (c) 2025 Symbolic MCP Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

"""
Comprehensive Integration Test Runner

This script provides a command-line interface for running the integration test suite
with various options and reporting capabilities.
"""

import argparse  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any, Dict, List, Optional  # noqa: E402

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


class IntegrationTestRunner:
    """Comprehensive test runner for the integration test suite"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.test_dir = Path(__file__).parent
        self.results = {}

    def run_pytest(
        self,
        test_pattern: str = "tests/integration/",
        markers: Optional[List[str]] = None,
        extra_args: Optional[List[str]] = None,
        verbose: bool = True,
    ) -> Dict[str, Any]:
        """Run pytest with specified options"""

        cmd = ["python", "-m", "pytest"]

        # Add test pattern
        cmd.append(test_pattern)

        # Add markers
        if markers:
            for marker in markers:
                cmd.extend(["-m", marker])

        # Add extra arguments
        if extra_args:
            cmd.extend(extra_args)

        # Add verbosity
        if verbose:
            cmd.append("-v")

        # Change to project directory
        original_cwd = os.getcwd()
        os.chdir(self.project_root)

        try:
            print(f"Running command: {' '.join(cmd)}")
            start_time = time.time()

            # Activate virtual environment and run
            activate_cmd = (
                f"source {self.project_root}/venv/bin/activate && {' '.join(cmd)}"
            )
            result = subprocess.run(
                activate_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            execution_time = time.time() - start_time

            # Parse results
            return_code = result.returncode

            # Extract test summary from output
            summary = self._parse_pytest_output(result.stdout, result.stderr)

            return {
                "command": " ".join(cmd),
                "return_code": return_code,
                "execution_time": execution_time,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "summary": summary,
                "success": return_code == 0,
            }

        except subprocess.TimeoutExpired:
            return {
                "command": " ".join(cmd),
                "return_code": 124,  # Timeout exit code
                "execution_time": 300,
                "stdout": "",
                "stderr": "Test execution timed out after 5 minutes",
                "summary": {"status": "timeout"},
                "success": False,
            }

        except Exception as e:
            return {
                "command": " ".join(cmd),
                "return_code": -1,
                "execution_time": 0,
                "stdout": "",
                "stderr": str(e),
                "summary": {"status": "error", "error": str(e)},
                "success": False,
            }

        finally:
            os.chdir(original_cwd)

    def _parse_pytest_output(
        self, stdout: str, stderr: str
    ) -> Dict[str, Any]:  # noqa: C901
        """Parse pytest output to extract summary information"""
        summary = {
            "status": "unknown",
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
        }

        # Look for the test summary line
        lines = stdout.split("\n") + stderr.split("\n")
        for line in lines:
            if "passed" in line and "failed" in line:
                # Example: "5 passed, 2 failed, 1 skipped in 10.5s"
                parts = line.split()
                try:
                    for i, part in enumerate(parts):
                        if part == "passed":
                            summary["passed"] = int(parts[i - 1])
                        elif part == "failed":
                            summary["failed"] = int(parts[i - 1])
                        elif part == "skipped":
                            summary["skipped"] = int(parts[i - 1])
                        elif part == "error" or part == "errors":
                            summary["errors"] = int(parts[i - 1])
                except (ValueError, IndexError):
                    pass

                # Determine status
                if summary["failed"] == 0 and summary["errors"] == 0:
                    summary["status"] = "passed"
                else:
                    summary["status"] = "failed"

                break

        return summary

    def run_all_tests(
        self, include_slow: bool = False, include_memory: bool = False
    ) -> Dict[str, Any]:
        """Run all integration tests with different categories"""

        results = {
            "timestamp": time.time(),
            "test_categories": {},
            "overall_summary": {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
        }

        # Test categories
        categories = [
            {
                "name": "basic_integration",
                "description": "Basic integration tests",
                "pattern": "tests/integration/test_e2e_harness.py",
                "markers": ["integration"],
                "expected": "Most should pass",
            },
            {
                "name": "load_performance",
                "description": "Load and performance tests",
                "pattern": "tests/integration/test_load_harness.py",
                "markers": ["load"],
                "expected": "Most should pass",
            },
            {
                "name": "security_validation",
                "description": "Security validation tests",
                "pattern": "tests/integration/test_security_harness.py",
                "markers": ["security"],
                "expected": "All should pass",
            },
            {
                "name": "resilience_testing",
                "description": "Resilience and failure testing",
                "pattern": "tests/integration/test_crosshair_failure_harness.py",
                "markers": ["resilience"],
                "expected": "Most should pass",
            },
        ]

        # Optional categories
        if include_slow:
            categories.append(
                {
                    "name": "memory_leak_detection",
                    "description": "Memory leak detection tests",
                    "pattern": "tests/integration/test_memory_leak_detector.py",
                    "markers": ["memory"],
                    "expected": "All should pass",
                }
            )

        # Run each category
        for category in categories:
            print(f"\n{'='*60}")
            print(f"Running {category['description']}")
            print(f"Expected: {category['expected']}")
            print(f"{'='*60}")

            extra_args = []
            if include_slow:
                extra_args.append("--run-slow")
            if include_memory:
                extra_args.append("--run-memory")

            result = self.run_pytest(
                test_pattern=category["pattern"],
                markers=category["markers"],
                extra_args=extra_args,
                verbose=True,
            )

            results["test_categories"][category["name"]] = {
                "description": category["description"],
                "expected": category["expected"],
                "result": result,
            }

            # Update overall summary
            summary = result["summary"]
            for key in ["total", "passed", "failed", "skipped"]:
                if key in summary:
                    results["overall_summary"][key] += summary[key]

        return results

    def run_failing_tests(self) -> Dict[str, Any]:
        """Run failing tests to demonstrate current issues"""

        print(f"\n{'='*60}")
        print("RUNNING FAILING TESTS (Expected to Fail)")
        print("These tests demonstrate current integration issues")
        print(f"{'='*60}")

        result = self.run_pytest(
            test_pattern="tests/integration/test_failing_integration_tests.py",
            markers=["failing"],
            extra_args=["--tb=short"],
            verbose=True,
        )

        return {
            "category": "failing_tests",
            "description": "Tests that demonstrate current integration issues",
            "expected": "All should fail (demonstrating issues)",
            "result": result,
        }

    def generate_report(
        self, results: Dict[str, Any], output_file: Optional[str] = None
    ) -> str:
        """Generate a comprehensive test report"""

        report = []
        report.append("# Symbolic Execution MCP Integration Test Report")
        report.append(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # Overall summary
        overall = results.get("overall_summary", {})
        report.append("## Overall Summary")
        report.append(f"- Total tests: {overall.get('total', 0)}")
        report.append(f"- Passed: {overall.get('passed', 0)}")
        report.append(f"- Failed: {overall.get('failed', 0)}")
        report.append(f"- Skipped: {overall.get('skipped', 0)}")

        if overall.get("total", 0) > 0:
            pass_rate = (overall.get("passed", 0) / overall.get("total", 0)) * 100
            report.append(f"- Pass rate: {pass_rate:.1f}%")
        report.append("")

        # Category results
        if "test_categories" in results:
            report.append("## Test Categories")
            for category_name, category_data in results["test_categories"].items():
                report.append(f"### {category_data['description']}")
                report.append(f"**Expected:** {category_data['expected']}")

                result = category_data["result"]
                summary = result["summary"]

                report.append(f"**Status:** {summary.get('status', 'unknown')}")
                report.append(f"**Passed:** {summary.get('passed', 0)}")
                report.append(f"**Failed:** {summary.get('failed', 0)}")
                report.append(f"**Time:** {result['execution_time']:.1f}s")

                if not result["success"]:
                    report.append("**Errors detected:** See detailed output below")

                report.append("")

        # Failing tests
        if "failing_tests" in results:
            failing_data = results["failing_tests"]
            report.append("## Failing Tests (Expected)")
            report.append(f"**Purpose:** {failing_data['description']}")
            report.append(f"**Expected:** {failing_data['expected']}")

            result = failing_data["result"]
            summary = result["summary"]

            report.append(f"**Status:** {summary.get('status', 'unknown')}")
            report.append(f"**Passed:** {summary.get('passed', 0)}")
            report.append(f"**Failed:** {summary.get('failed', 0)}")

            report.append("")

        # Recommendations
        report.append("## Recommendations")

        if overall.get("failed", 0) == 0:
            report.append("✅ All tests passed - system is ready for production")
        else:
            report.append("⚠️  Some tests failed - review the following:")
            report.append("1. Check the detailed output for each failed test")
            report.append("2. Address any security issues immediately")
            report.append("3. Fix performance bottlenecks if load tests failed")
            report.append("4. Resolve memory leaks if detected")
            report.append("5. Improve error handling and resilience if needed")

        report_text = "\n".join(report)

        # Save to file if requested
        if output_file:
            with open(output_file, "w") as f:
                f.write(report_text)
            print(f"Report saved to: {output_file}")

        return report_text

    def print_results(self, results: Dict[str, Any]):
        """Print a summary of results to console"""
        print(f"\n{'='*60}")
        print("INTEGRATION TEST RESULTS SUMMARY")
        print(f"{'='*60}")

        overall = results.get("overall_summary", {})
        if overall.get("total", 0) > 0:
            pass_rate = (overall.get("passed", 0) / overall.get("total", 0)) * 100
            print(  # noqa: E501
                f"Overall: {overall.get('passed', 0)}/{overall.get('total', 0)} passed ({pass_rate:.1f}%)"
            )
        else:
            print("No tests executed")

        # Category summary
        if "test_categories" in results:
            for category_name, category_data in results["test_categories"].items():
                result = category_data["result"]
                summary = result["summary"]
                status = "✅" if result["success"] else "❌"
                print(  # noqa: E501
                    f"{status} {category_data['description']}: {summary.get('status', 'unknown')}"
                )

        print(f"{'='*60}")


def main():  # noqa: C901
    """Main entry point for the test runner"""
    parser = argparse.ArgumentParser(
        description="Run Symbolic Execution MCP Integration Tests"
    )
    parser.add_argument(
        "--category",
        choices=["all", "basic", "load", "security", "resilience", "memory", "failing"],
        default="all",
        help="Test category to run",
    )
    parser.add_argument(
        "--include-slow", action="store_true", help="Include slow tests"
    )
    parser.add_argument(
        "--include-memory", action="store_true", help="Include memory-intensive tests"
    )
    parser.add_argument(
        "--verbose", action="store_true", default=True, help="Verbose output"
    )
    parser.add_argument("--output", help="Output file for test report")
    parser.add_argument("--json", help="Output file for JSON results")
    parser.add_argument("--no-failing", action="store_true", help="Skip failing tests")

    args = parser.parse_args()

    runner = IntegrationTestRunner()
    results = {}

    try:
        if args.category == "all":
            results = runner.run_all_tests(
                include_slow=args.include_slow, include_memory=args.include_memory
            )
            if not args.no_failing:
                failing_results = runner.run_failing_tests()
                results["failing_tests"] = failing_results

        elif args.category == "failing":
            results = runner.run_failing_tests()

        else:
            # Run specific category
            category_map = {
                "basic": ("tests/integration/test_e2e_harness.py", ["integration"]),
                "load": ("tests/integration/test_load_harness.py", ["load"]),
                "security": (
                    "tests/integration/test_security_harness.py",
                    ["security"],
                ),
                "resilience": (
                    "tests/integration/test_crosshair_failure_harness.py",
                    ["resilience"],
                ),
                "memory": (
                    "tests/integration/test_memory_leak_detector.py",
                    ["memory"],
                ),
            }

            if args.category in category_map:
                pattern, markers = category_map[args.category]
                extra_args = []
                if args.include_slow:
                    extra_args.append("--run-slow")
                if args.include_memory:
                    extra_args.append("--run-memory")

                result = runner.run_pytest(
                    test_pattern=pattern,
                    markers=markers,
                    extra_args=extra_args,
                    verbose=args.verbose,
                )

                results = {
                    "test_categories": {
                        args.category: {
                            "description": f"{args.category.title()} tests",
                            "result": result,
                        }
                    },
                    "overall_summary": result["summary"],
                }

        # Print results
        runner.print_results(results)

        # Generate report
        if args.output or args.verbose:
            report = runner.generate_report(results, args.output)
            if args.verbose and not args.output:
                print("\n" + report)

        # Save JSON if requested
        if args.json:
            with open(args.json, "w") as f:
                json.dump(results, f, indent=2, default=str)
            print(f"JSON results saved to: {args.json}")

        # Exit with appropriate code
        overall = results.get("overall_summary", {})
        if overall.get("failed", 0) > 0 or overall.get("errors", 0) > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    except KeyboardInterrupt:
        print("\nTest execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Test execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
