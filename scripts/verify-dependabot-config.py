#!/usr/bin/env python3
"""
Dependabot Configuration Verification Script

This script verifies that the comprehensive Dependabot configuration
is properly set up and covers all dependency categories for the
symbolic-mcp project.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Set

import yaml


def load_yaml_file(file_path: Path) -> Dict:
    """Load and parse a YAML file."""
    try:
        with open(file_path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"❌ Error parsing {file_path}: {e}")
        sys.exit(1)


def check_dependabot_config() -> Dict[str, any]:
    """Verify the main dependabot.yml configuration."""
    print("🔍 Verifying main Dependabot configuration...")

    config_path = Path(".github/dependabot.yml")
    if not config_path.exists():
        print("❌ .github/dependabot.yml not found")
        return {"valid": False, "errors": ["Main configuration file missing"]}

    config = load_yaml_file(config_path)

    # Required structure checks
    errors = []
    warnings = []

    # Check version
    if config.get("version") != 2:
        errors.append("Dependabot version should be 2")

    # Check for updates section
    if not config.get("updates"):
        errors.append("No updates section found in configuration")

    # Check for required ecosystems
    ecosystems_found = set()
    security_updates_found = False

    for update in config.get("updates", []):
        ecosystem = update.get("package-ecosystem")
        if ecosystem:
            ecosystems_found.add(ecosystem)

            # Check for security-focused updates
            if update.get("schedule", {}).get("interval") == "daily":
                security_updates_found = True

    # Required ecosystems
    required_ecosystems = {"pip", "github-actions"}
    missing_ecosystems = required_ecosystems - ecosystems_found

    if missing_ecosystems:
        errors.append(f"Missing required ecosystems: {missing_ecosystems}")

    if not security_updates_found:
        warnings.append("No daily security updates found")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "ecosystems": list(ecosystems_found),
    }


def check_workflow_files() -> Dict[str, any]:
    """Verify workflow files exist and have proper content."""
    print("🔍 Verifying workflow files...")

    required_workflows = [
        ".github/workflows/dependabot-auto-merge.yml",
        ".github/workflows/dependency-security-monitoring.yml",
        ".github/workflows/dependabot-pr-management.yml",
    ]

    errors = []
    present_workflows = []

    for workflow_path in required_workflows:
        path = Path(workflow_path)
        if path.exists():
            present_workflows.append(workflow_path)

            # Basic content checks
            try:
                with open(path, "r") as f:
                    content = f.read()

                # Check for required keys
                if workflow_path.endswith("auto-merge.yml"):
                    if "auto-merge" not in content:
                        errors.append(
                            f"Auto-merge workflow missing auto-merge functionality"
                        )

                if workflow_path.endswith("security-monitoring.yml"):
                    if "security" not in content:
                        errors.append(
                            f"Security monitoring workflow missing security checks"
                        )

                if workflow_path.endswith("pr-management.yml"):
                    if "label" not in content:
                        errors.append(
                            f"PR management workflow missing labeling functionality"
                        )

            except Exception as e:
                errors.append(f"Error reading {workflow_path}: {e}")
        else:
            errors.append(f"Missing required workflow: {workflow_path}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "present_workflows": present_workflows,
    }


def check_dependency_coverage() -> Dict[str, any]:
    """Verify coverage of all dependency categories."""
    print("🔍 Verifying dependency coverage...")

    # Expected dependencies from requirements.txt and pyproject.toml
    expected_deps = {
        "core": {
            "fastmcp",
            "crosshair-tool",
            "z3-solver",
            "icontract",
            "RestrictedPython",
            "typing-extensions",
            "pydantic",
            "psutil",
        },
        "dev": {"pytest", "black", "flake8", "isort", "mypy", "bandit", "safety"},
        "prod": {"structlog", "prometheus-client", "pydantic-settings"},
        "experimental": {"angr", "scikit-learn", "numpy", "ray"},
    }

    # Load dependabot config
    config = load_yaml_file(Path(".github/dependabot.yml"))

    covered_deps = set()
    errors = []

    for update in config.get("updates", []):
        if update.get("package-ecosystem") == "pip":
            for allow in update.get("allow", []):
                dep_name = allow.get("dependency-name", "").replace("*", "")
                if dep_name:
                    covered_deps.add(dep_name)

    # Check coverage
    all_expected = set()
    for category_deps in expected_deps.values():
        all_expected.update(category_deps)

    missing_deps = all_expected - covered_deps

    if missing_deps:
        errors.append(f"Missing dependencies in configuration: {missing_deps}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "covered_dependencies": list(covered_deps),
        "missing_dependencies": list(missing_deps),
    }


def check_security_features() -> Dict[str, any]:
    """Verify security-focused features are properly configured."""
    print("🔍 Verifying security features...")

    errors = []
    warnings = []

    # Check main dependabot.yml for security features
    config = load_yaml_file(Path(".github/dependabot.yml"))

    security_features = {
        "daily_security_updates": False,
        "auto_merge_security": False,
        "version_constraints": False,
        "grouped_updates": False,
    }

    for update in config.get("updates", []):
        # Check for daily security updates
        if update.get("schedule", {}).get("interval") == "daily":
            security_features["daily_security_updates"] = True

        # Check for auto-merge on security updates
        if update.get("auto-merge-level") == "patch":
            security_features["auto_merge_security"] = True

        # Check for version constraints (ignoring major versions)
        for ignore in update.get("ignore", []):
            if ignore.get("update-types") == ["version-update:semver-major"]:
                security_features["version_constraints"] = True

        # Check for grouped updates
        if update.get("groups"):
            security_features["grouped_updates"] = True

    # Check workflow files for security features
    security_workflow = Path(".github/workflows/dependency-security-monitoring.yml")
    if security_workflow.exists():
        with open(security_workflow, "r") as f:
            content = f.read()

        if "safety" not in content:
            warnings.append("Security monitoring workflow missing safety checks")
        if "bandit" not in content:
            warnings.append("Security monitoring workflow missing bandit checks")
        if "pip-audit" not in content:
            warnings.append("Security monitoring workflow missing pip-audit checks")
    else:
        errors.append("Security monitoring workflow not found")

    # Report missing features
    for feature, enabled in security_features.items():
        if not enabled:
            warnings.append(f"Security feature not enabled: {feature}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "security_features": security_features,
    }


def check_documentation() -> Dict[str, any]:
    """Verify documentation is complete."""
    print("🔍 Verifying documentation...")

    errors = []
    warnings = []

    # Check for documentation file
    doc_path = Path("docs/dependabot-configuration.md")
    if not doc_path.exists():
        errors.append("Dependabot configuration documentation not found")
        return {"valid": False, "errors": errors, "warnings": warnings}

    # Check documentation content
    try:
        with open(doc_path, "r") as f:
            content = f.read()

        required_sections = [
            "## Overview",
            "## Configuration Components",
            "## Security Features",
            "## Integration with CI/CD",
        ]

        missing_sections = []
        for section in required_sections:
            if section not in content:
                missing_sections.append(section)

        if missing_sections:
            warnings.append(f"Documentation missing sections: {missing_sections}")

        # Check for key content
        if "FastMCP 2.0" not in content:
            warnings.append("Documentation should mention FastMCP 2.0 compatibility")

        if "CVE-003-001" not in content:
            warnings.append("Documentation should mention CVE-003-001 protections")

    except Exception as e:
        errors.append(f"Error reading documentation: {e}")

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


def main():
    """Main verification function."""
    print("🚀 Dependabot Configuration Verification")
    print("=" * 50)
    print()

    # Change to project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    os.chdir(project_root)

    # Run all checks
    results = {
        "dependabot_config": check_dependabot_config(),
        "workflow_files": check_workflow_files(),
        "dependency_coverage": check_dependency_coverage(),
        "security_features": check_security_features(),
        "documentation": check_documentation(),
    }

    # Print results
    print("\n📊 VERIFICATION RESULTS")
    print("=" * 50)

    all_valid = True
    total_errors = 0
    total_warnings = 0

    for check_name, result in results.items():
        status = "✅ PASS" if result["valid"] else "❌ FAIL"
        print(f"{status} {check_name.replace('_', ' ').title()}")

        if result.get("errors"):
            for error in result["errors"]:
                print(f"  ❌ {error}")
            total_errors += len(result["errors"])
            all_valid = False

        if result.get("warnings"):
            for warning in result["warnings"]:
                print(f"  ⚠️  {warning}")
            total_warnings += len(result["warnings"])

    # Summary
    print(f"\n📈 SUMMARY")
    print("=" * 50)
    print(f"Overall Status: {'✅ PASSED' if all_valid else '❌ FAILED'}")
    print(f"Total Errors: {total_errors}")
    print(f"Total Warnings: {total_warnings}")

    # Coverage details
    if results["dependency_coverage"].get("covered_dependencies"):
        print(
            f"Dependencies Covered: {len(results['dependency_coverage']['covered_dependencies'])}"
        )

    if results["workflow_files"].get("present_workflows"):
        print(
            f"Workflows Configured: {len(results['workflow_files']['present_workflows'])}"
        )

    if all_valid and total_errors == 0:
        print(
            "\n🎉 Dependabot configuration is properly set up and ready for production!"
        )
        sys.exit(0)
    else:
        print("\n⚠️  Please address the errors before deploying to production.")
        sys.exit(1)


if __name__ == "__main__":
    main()
