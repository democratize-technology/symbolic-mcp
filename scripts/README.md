# Development Scripts

This directory contains utility scripts for symbolic-mcp development.

## Available Scripts

### setup_dev.py
**Purpose**: Set up the development environment for symbolic-mcp.

**Usage**:
```bash
# From project root
python3 scripts/setup_dev.py
```

**What it does**:
- Sets up version management with setuptools-scm
- Installs and configures pre-commit hooks
- Creates `.env` file with development configuration
- Creates `requirements-dev.txt` with development dependencies
- Validates configuration
- Runs initial tests

**Requirements**:
- Python 3.8+
- Should be run from project root directory
- Requires pip to be available (or uses virtualenv)

### check_fastmcp_compatibility.py
**Purpose**: Check FastMCP version compatibility.

**Usage**:
```bash
python3 scripts/check_fastmcp_compatibility.py
```

### sync_version.py
**Purpose**: Synchronize version numbers across the project.

**Usage**:
```bash
python3 scripts/sync_version.py --version 0.1.0
```

## Deleted Scripts

The following scripts were removed as vaporware (they checked for non-existent configurations):
- `verify-dependabot-config.py` - Checked for workflows that don't exist
