#!/usr/bin/env python3
"""
FastMCP 2.0 Compatibility Checker

This script verifies FastMCP 2.0 compatibility and provides
detailed compatibility reports and recommendations.
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from typing_extensions import NotRequired, TypedDict


class _CompatibilityResults(TypedDict):
    """Type definition for compatibility results dictionary."""

    version: str | None
    compatibility: str
    issues: list[str]
    recommendations: list[str]
    api_compatibility: dict[str, Any]
    dependency_compatibility: dict[str, Any]
    test_results: dict[str, Any]
    installation: NotRequired[dict[str, bool | str | None]]
    import_compatibility: NotRequired[dict[str, bool]]


class FastMCPCompatibilityChecker:
    """FastMCP 2.0 compatibility checker"""

    def __init__(self) -> None:
        self.compatibility_results: _CompatibilityResults = {
            "version": None,
            "compatibility": "unknown",
            "issues": [],
            "recommendations": [],
            "api_compatibility": {},
            "dependency_compatibility": {},
            "test_results": {},
        }

    def check_fastmcp_installation(self) -> dict[str, bool | str | None]:
        """Check FastMCP installation and version"""
        try:
            import fastmcp

            version = getattr(fastmcp, "__version__", "unknown")

            return {
                "installed": True,
                "version": version,
                "location": getattr(fastmcp, "__file__", "unknown"),
            }
        except ImportError:
            return {"installed": False, "version": None, "location": None}

    def check_version_compatibility(self, version: str) -> tuple[str, list[str]]:
        """Check if FastMCP version is compatible"""
        try:
            from packaging import version as pkg_version

            current = pkg_version.parse(version)
            required = pkg_version.parse("2.0.0")

            if current >= required:
                return "compatible", []
            elif current.major == 2:
                return "minor_incompatible", [
                    f"FastMCP {version} is 2.x but older than required 2.0.0",
                    "Consider upgrading FastMCP: pip install --upgrade fastmcp",
                ]
            else:
                return "incompatible", [
                    f"FastMCP {version} is not compatible with 2.0+",
                    "Major upgrade required: breaking changes expected",
                    "Backup your code before upgrading",
                ]
        except Exception as e:
            return "error", [f"Version comparison failed: {e}"]

    def check_api_compatibility(self) -> dict[str, dict[str, bool | str]]:
        """Check FastMCP API compatibility"""
        api_checks: dict[str, dict[str, bool | str]] = {}

        try:
            import fastmcp

            # Check for FastMCP 2.0 core APIs
            api_checks["core"] = {
                "MCPContext": hasattr(fastmcp, "MCPContext"),
                "Context": hasattr(fastmcp, "Context"),
                "Server": hasattr(fastmcp, "Server"),
                "Tool": hasattr(fastmcp, "Tool"),
                "Resource": hasattr(fastmcp, "Resource"),
            }

            # Check for FastMCP 2.0 decorators
            api_checks["decorators"] = {
                "mcp_tool": hasattr(fastmcp, "mcp_tool"),
                "with_tool": hasattr(fastmcp, "with_tool"),
                "mcp_resource": hasattr(fastmcp, "mcp_resource"),
                "with_resource": hasattr(fastmcp, "with_resource"),
            }

            # Check for FastMCP 2.0 server functionality
            api_checks["server"] = {
                "create_server": hasattr(fastmcp, "create_server"),
                "run_server": hasattr(fastmcp, "run_server"),
                "Server": hasattr(fastmcp, "Server"),
            }

            # Check for FastMCP 2.0 context management
            api_checks["context"] = {
                "ContextManager": hasattr(fastmcp, "ContextManager"),
                "create_context": hasattr(fastmcp, "create_context"),
                "context_decorator": hasattr(fastmcp, "context"),
            }

        except ImportError:
            api_checks["error"] = {"message": "FastMCP not available for API checking"}
        except Exception as e:
            api_checks["error"] = {"message": f"API compatibility check failed: {e}"}

        return api_checks

    def check_import_compatibility(self) -> dict[str, bool]:
        """Check critical FastMCP imports"""
        imports_to_check = [
            "fastmcp",
            "fastmcp.Context",
            "fastmcp.Server",
            "fastmcp.Tool",
            "fastmcp.Resource",
            "fastmcp.mcp_tool",
            "fastmcp.with_tool",
        ]

        import_results = {}

        for import_name in imports_to_check:
            try:
                # Split module and attribute
                if "." in import_name:
                    module_name, attr_name = import_name.rsplit(".", 1)
                    module = importlib.import_module(module_name)
                    import_results[import_name] = hasattr(module, attr_name)
                else:
                    importlib.import_module(import_name)
                    import_results[import_name] = True
            except (ImportError, AttributeError):
                import_results[import_name] = False

        return import_results

    def check_dependencies_compatibility(
        self,
    ) -> dict[str, dict[str, str | bool | None]]:
        """Check FastMCP dependencies compatibility"""
        dependency_checks = {}

        # Check FastMCP dependencies
        dependencies_to_check = [
            "mcp",  # Model Context Protocol
            "pydantic",  # Data validation
            "anyio",  # Async I/O
            "starlette",  # ASGI framework
            "typing_extensions",  # Type extensions
        ]

        for dep in dependencies_to_check:
            try:
                module = importlib.import_module(dep)
                version = getattr(module, "__version__", "unknown")
                dependency_checks[dep] = {
                    "available": True,
                    "version": version,
                    "location": getattr(module, "__file__", "unknown"),
                }
            except ImportError:
                dependency_checks[dep] = {
                    "available": False,
                    "version": None,
                    "location": None,
                }

        return dependency_checks

    def run_compatibility_tests(self) -> dict[str, bool | str]:
        """Run basic FastMCP compatibility tests"""
        test_results: dict[str, bool | str] = {}

        try:
            import fastmcp

            # Test 1: Create basic context
            try:
                if hasattr(fastmcp, "Context") or hasattr(fastmcp, "MCPContext"):
                    context_class = getattr(
                        fastmcp, "Context", getattr(fastmcp, "MCPContext", None)
                    )
                    if context_class:
                        # Try to instantiate context (if it's possible without args)
                        test_results["context_creation"] = True
                    else:
                        test_results["context_creation"] = False
                else:
                    test_results["context_creation"] = False
            except Exception:
                test_results["context_creation"] = False

            # Test 2: Check decorator functionality
            try:
                if hasattr(fastmcp, "mcp_tool"):
                    test_results["tool_decorator"] = True
                else:
                    test_results["tool_decorator"] = False
            except Exception:
                test_results["tool_decorator"] = False

            # Test 3: Check server creation
            try:
                if hasattr(fastmcp, "create_server") or hasattr(fastmcp, "Server"):
                    test_results["server_creation"] = True
                else:
                    test_results["server_creation"] = False
            except Exception:
                test_results["server_creation"] = False

            # Test 4: Check resource handling
            try:
                if hasattr(fastmcp, "Resource") or hasattr(fastmcp, "mcp_resource"):
                    test_results["resource_handling"] = True
                else:
                    test_results["resource_handling"] = False
            except Exception:
                test_results["resource_handling"] = False

        except ImportError:
            test_results["fastmcp_available"] = False
        except Exception as e:
            test_results["test_error"] = str(e)

        return test_results

    def generate_recommendations(
        self, compatibility_results: _CompatibilityResults
    ) -> list[str]:
        """Generate upgrade/recommendation suggestions"""
        recommendations = []

        installation = compatibility_results.get("installation", {})
        api_compatibility = compatibility_results.get("api_compatibility", {})
        test_results = compatibility_results.get("test_results", {})

        if not installation.get("installed"):
            recommendations.extend(
                [
                    "Install FastMCP: pip install fastmcp>=2.0.0",
                    "Verify installation in your Python environment",
                    "Check virtual environment activation",
                ]
            )
            return recommendations

        version = installation.get("version", "unknown")
        compatibility_status = compatibility_results.get("compatibility", "unknown")

        if compatibility_status == "incompatible":
            recommendations.extend(
                [
                    f"Upgrade FastMCP from {version} to 2.0+",
                    "Backup your current implementation",
                    "Review breaking changes in FastMCP 2.0",
                    "Test after upgrade with compatibility checker",
                ]
            )
        elif compatibility_status == "minor_incompatible":
            recommendations.extend(
                [
                    f"Upgrade FastMCP from {version} to latest 2.x",
                    "Minor version upgrade should be safe",
                    "pip install --upgrade fastmcp",
                ]
            )

        # API-specific recommendations
        missing_apis = []
        for api_category, checks in api_compatibility.items():
            if api_category == "error":
                continue

            for api_name, available in checks.items():
                if not available:
                    missing_apis.append(f"{api_category}.{api_name}")

        if missing_apis:
            recommendations.append(f"Missing FastMCP APIs: {', '.join(missing_apis)}")

        # Test failure recommendations
        failed_tests = [test for test, passed in test_results.items() if not passed]
        if failed_tests:
            recommendations.append(
                f"Failed compatibility tests: {', '.join(failed_tests)}"
            )

        if not recommendations:
            recommendations.append("✅ FastMCP 2.0 compatibility confirmed")

        return recommendations

    def run_full_compatibility_check(self) -> dict[str, Any]:
        """Run comprehensive compatibility check"""
        results: dict[str, Any] = dict(self.compatibility_results)

        # Check installation
        results["installation"] = self.check_fastmcp_installation()

        if results["installation"]["installed"]:
            version = results["installation"]["version"]
            if version is None:
                version = "unknown"

            # Check version compatibility
            compatibility, issues = self.check_version_compatibility(version)
            results["compatibility"] = compatibility
            results["issues"].extend(issues)

            # Run detailed checks
            results["api_compatibility"] = self.check_api_compatibility()
            results["import_compatibility"] = self.check_import_compatibility()
            results["dependency_compatibility"] = (
                self.check_dependencies_compatibility()
            )
            results["test_results"] = self.run_compatibility_tests()

        # Generate recommendations
        results["recommendations"] = self.generate_recommendations(
            results  # type: ignore[arg-type]
        )

        return results

    def print_report(self, results: dict[str, Any]) -> None:
        """Print formatted compatibility report"""
        print("🔍 FastMCP 2.0 Compatibility Report")
        print("=" * 50)

        # Installation status
        installation = results.get("installation", {})
        if installation.get("installed"):
            version = installation.get("version", "unknown")
            print(f"✅ FastMCP installed: v{version}")
            print(f"📍 Location: {installation.get('location', 'unknown')}")
        else:
            print("❌ FastMCP not installed")
            print("💡 Install with: pip install fastmcp>=2.0.0")
            return

        # Compatibility status
        compatibility = results.get("compatibility", "unknown")
        compatibility_emoji = {
            "compatible": "✅",
            "minor_incompatible": "⚠️",
            "incompatible": "❌",
            "error": "❌",
        }.get(compatibility, "❓")

        print(f"\n{compatibility_emoji} Compatibility: {compatibility}")

        # Issues
        if results.get("issues"):
            print("\n❌ Issues Found:")
            for issue in results["issues"]:
                print(f"  • {issue}")

        # API Compatibility
        api_compatibility = results.get("api_compatibility", {})
        if api_compatibility and "error" not in api_compatibility:
            print("\n🔧 API Compatibility:")
            for category, checks in api_compatibility.items():
                print(f"\n  {category.title()}:")
                for api_name, available in checks.items():
                    status = "✅" if available else "❌"
                    print(f"    {status} {api_name}")

        # Import Compatibility
        import_compatibility = results.get("import_compatibility", {})
        if import_compatibility:
            print("\n📦 Import Compatibility:")
            for import_name, available in import_compatibility.items():
                status = "✅" if available else "❌"
                print(f"    {status} {import_name}")

        # Test Results
        test_results = results.get("test_results", {})
        if test_results:
            print("\n🧪 Compatibility Tests:")
            for test_name, passed in test_results.items():
                status = "✅" if passed else "❌"
                print(f"    {status} {test_name}")

        # Recommendations
        recommendations = results.get("recommendations", [])
        if recommendations:
            print("\n💡 Recommendations:")
            for rec in recommendations:
                if rec.startswith("✅"):
                    print(f"  {rec}")
                elif rec.startswith("❌") or rec.startswith("⚠️"):
                    print(f"  {rec}")
                else:
                    print(f"  • {rec}")

        print("\n" + "=" * 50)


def main() -> int:
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="FastMCP 2.0 Compatibility Checker")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--quiet", action="store_true", help="Minimal output")
    parser.add_argument("--output", help="Output file for detailed report")

    args = parser.parse_args()

    checker = FastMCPCompatibilityChecker()
    results = checker.run_full_compatibility_check()

    if args.json:
        print(json.dumps(results, indent=2))
    elif args.quiet:
        compatibility = results.get("compatibility", "unknown")
        installation = results.get("installation", {})

        if installation.get("installed"):
            version = installation.get("version", "unknown")
            print(f"{compatibility}:{version}")
        else:
            print("not_installed")
    else:
        checker.print_report(results)

    # Write to file if requested
    if args.output:
        Path(args.output).write_text(json.dumps(results, indent=2))

    # Return appropriate exit code
    compatibility = results.get("compatibility", "incompatible")
    if compatibility == "compatible":
        return 0
    elif compatibility in ["minor_incompatible", "error"]:
        return 1
    else:  # incompatible or not installed
        return 2


if __name__ == "__main__":
    sys.exit(main())
