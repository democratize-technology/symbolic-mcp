#!/usr/bin/env python3
"""
Development Setup Script

This script sets up the development environment for symbolic-mcp
including version management, pre-commit hooks, and development tools.
"""

import subprocess  # nosec B404  # Dev utility script, subprocess is needed
import sys
from pathlib import Path


def run_command(cmd: str, description: str, check: bool = True) -> bool:
    """Run a command and handle errors"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(
            cmd,
            shell=True,  # nosec B602  # Dev utility with controlled input
            check=check,
            capture_output=True,
            text=True,
        )
        if result.stdout.strip():
            print(f"   {result.stdout.strip()}")
        if result.stderr.strip() and check:
            print(f"   Warning: {result.stderr.strip()}")
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Error: {e}")
        if e.stdout:
            print(f"   stdout: {e.stdout}")
        if e.stderr:
            print(f"   stderr: {e.stderr}")
        return False


def setup_version_management() -> bool:
    """Setup version management components"""
    print("\n🏷️ Setting up version management...")

    # Check if setuptools-scm is available
    if not run_command(
        "python3 -c 'import setuptools_scm'",
        "Checking setuptools-scm availability",
        check=False,
    ):
        run_command(
            "python3 -m pip install setuptools-scm packaging",
            "Installing setuptools-scm",
        )

    # Create initial _version.py if it doesn't exist
    version_py = Path("_version.py")
    if not version_py.exists():
        print("   📝 Creating initial _version.py...")
        content = '''# Version file for symbolic-mcp
"""Version information for symbolic-mcp"""

__version__ = "0.1.0.dev0"

# Version metadata
version_info = {
    "version": "0.1.0.dev0",
    "git_version": "0.1.0",
    "is_git_repo": True,
}

# Compatibility information (will be updated by check_fastmcp_compatibility.py)
__fastmcp_compatibility__ = {
    "version": "unknown",
    "compatibility": "unknown",
    "message": "Run scripts/check_fastmcp_compatibility.py to update",
    "required": ">=2.0.0"
}
'''
        version_py.write_text(content)
        print("   ✅ Created _version.py")

    return True


def setup_pre_commit() -> bool:
    """Setup pre-commit hooks"""
    print("\n🪝 Setting up pre-commit hooks...")

    # Install pre-commit
    run_command("python3 -m pip install pre-commit", "Installing pre-commit")

    # Install hooks
    if run_command("pre-commit install", "Installing pre-commit hooks"):
        print("   ✅ Pre-commit hooks installed")
        return True
    else:
        print("   ⚠️ Pre-commit hooks installation failed")
        return False


def validate_configuration() -> bool:
    """Validate the current configuration"""
    print("\n✅ Validating configuration...")

    success = True

    # Check pyproject.toml
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        print("   ❌ pyproject.toml not found")
        success = False
    else:
        content = pyproject_path.read_text()
        has_scm = "setuptools-scm" in content
        has_dynamic = (
            'dynamic = ["version"]' in content or "dynamic = ['version']" in content
        )
        has_config = "[tool.setuptools_scm]" in content

        print("   📋 pyproject.toml found")
        print(f"   📦 setuptools-scm configured: {has_scm}")
        print(f"   🔄 Dynamic version enabled: {has_dynamic}")
        print(f"   ⚙️  SCM config section: {has_config}")

        if not (has_scm and has_dynamic and has_config):
            print("   ⚠️ Version configuration may be incomplete")
            success = False

    # Check version manager
    if run_command(
        "python3 version_manager.py get", "Testing version manager", check=False
    ):
        version = subprocess.getoutput("python3 version_manager.py get")
        print(f"   🏷️ Current version: {version}")
    else:
        print("   ❌ Version manager not working")
        success = False

    # Check FastMCP compatibility
    if run_command(
        "python3 scripts/check_fastmcp_compatibility.py --quiet",
        "Checking FastMCP compatibility",
        check=False,
    ):
        compat = subprocess.getoutput(
            "python3 scripts/check_fastmcp_compatibility.py --quiet"
        )
        print(f"   🔗 FastMCP compatibility: {compat}")
    else:
        print("   ⚠️ FastMCP compatibility check failed")

    return success


def run_initial_tests() -> bool:
    """Run initial tests to verify setup"""
    print("\n🧪 Running initial tests...")

    tests = [
        ("Version validation", "python3 version_manager.py validate --version 0.1.0"),
        ("Version suggestion", "python3 version_manager.py suggest"),
        (
            "Version sync script",
            "python3 scripts/sync_version.py --version 0.1.0 --skip-docs",
        ),
    ]

    passed = 0
    for test_name, cmd in tests:
        if run_command(cmd, f"Testing {test_name}", check=False):
            passed += 1

    print(f"   📊 Tests passed: {passed}/{len(tests)}")
    return passed == len(tests)


def create_dev_environment() -> bool:
    """Create development environment configuration"""
    print("\n🌍 Creating development environment...")

    # Create .env file if it doesn't exist
    env_file = Path(".env")
    if not env_file.exists():
        content = """# Development Environment Configuration
# Copy this file to .env.local and modify as needed

# Symbolic MCP Configuration
SYMBOLIC_MCP_DEBUG=true
SYMBOLIC_MCP_LOG_LEVEL=INFO
SYMBOLIC_MCP_TIMEOUT=30

# FastMCP Configuration
FASTMCP_LOG_LEVEL=INFO
FASTMCP_MAX_CONCURRENT_REQUESTS=10

# Development Settings
PYTHONPATH=.
PYTHONDONTWRITEBYTECODE=1

# Testing
PYTEST_ADDOPTS=--verbose --tb=short
"""
        env_file.write_text(content)
        print("   ✅ Created .env file")

    # Create requirements-dev.txt if needed
    dev_req = Path("requirements-dev.txt")
    if not dev_req.exists():
        content = """# Development requirements
setuptools-scm>=8.0.0
packaging>=23.0.0
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-mock>=3.10.0
pytest-asyncio>=0.21.0
black>=23.0.0
flake8>=6.0.0
isort>=5.12.0
mypy>=1.5.0
bandit>=1.7.0
safety>=2.3.0
pre-commit>=3.4.0
"""
        dev_req.write_text(content)
        print("   ✅ Created requirements-dev.txt")

    return True


def main() -> int:
    """Main setup function"""
    print("🚀 Symbolic MCP Development Setup")
    print("=" * 50)

    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("❌ Error: pyproject.toml not found. Run this script from project root.")
        return 1

    # Run setup steps
    steps = [
        ("Version Management", setup_version_management),
        ("Pre-commit Hooks", setup_pre_commit),
        ("Development Environment", create_dev_environment),
        ("Configuration Validation", validate_configuration),
        ("Initial Tests", run_initial_tests),
    ]

    results = []
    for step_name, step_func in steps:
        try:
            result = step_func()
            results.append((step_name, result))
        except Exception as e:
            print(f"❌ {step_name} failed: {e}")
            results.append((step_name, False))

    # Summary
    print("\n" + "=" * 50)
    print("📊 Setup Summary")

    passed = 0
    for step_name, result in results:
        status = "✅" if result else "❌"
        print(f"   {status} {step_name}")
        if result:
            passed += 1

    print(f"\n🎉 Setup completed: {passed}/{len(results)} steps successful")

    if passed == len(results):
        print("\n🌟 Development environment is ready!")
        print("\nNext steps:")
        print("   1. Activate virtual environment: source venv/bin/activate")
        print("   2. Install dependencies: pip install -r requirements-dev.txt")
        print("   3. Run tests: pytest")
        print("   4. Start development: python3 version_manager.py --help")
        return 0
    else:
        print(
            f"\n⚠️ {len(results) - passed} step(s) failed. Please review and fix issues."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
