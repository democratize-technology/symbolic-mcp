<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2025 Symbolic MCP Contributors -->

# Linting and Code Quality Configuration

This document explains the comprehensive linting and code quality setup for the Symbolic MCP project.

## Overview

The Symbolic MCP project uses a multi-layered approach to code quality and security:

1. **Git Integration**: Pre-commit hooks for automated quality checks
2. **Static Analysis**: Multiple linters for comprehensive code analysis
3. **Security Scanning**: Automated vulnerability detection
4. **Type Checking**: Static type analysis for reliability
5. **Formatting**: Consistent code formatting across the team

## Configuration Files

### Core Linting Configuration

| File | Purpose | Key Features |
|------|---------|--------------|
| `.gitignore` | Comprehensive exclusions for security and development artifacts | Security-sensitive files, build artifacts, IDE files |
| `.pre-commit-config.yaml` | Automated pre-commit hooks | Security scanning, formatting, type checking |
| `.flake8` | Python code style and complexity checking | Security-focused rules, symbolic execution patterns |
| `.pylintrc` | Advanced Python static analysis | Security extensions, complexity limits |
| `.bandit` | Security vulnerability scanning | Custom security rules for symbolic execution |
| `.commitlint.yaml` | Commit message standards | Conventional commits with security types |

### Development Environment Configuration

| File | Purpose | Key Features |
|------|---------|--------------|
| `.editorconfig` | Cross-editor consistency | Python-specific formatting rules |
| `pyproject.toml` | Python project configuration | Integration with tool configurations |

## Pre-commit Hooks

The pre-commit configuration provides automated quality checks:

### Security Hooks
- **Bandit**: Security vulnerability scanning
- **Safety**: Dependency vulnerability checking
- **Detect-secrets**: Secret detection in code
- **Semgrep**: Advanced static analysis

### Code Quality Hooks
- **Black**: Code formatting (88 characters line length)
- **isort**: Import sorting and organization
- **Flake8**: Style and complexity checking
- **MyPy**: Static type checking
- **Pylint**: Comprehensive static analysis

### Custom Symbolic MCP Hooks
- **CrossHair Integration**: Symbolic execution tool verification
- **Memory Leak Detection**: Memory usage analysis
- **FastMCP Compliance**: MCP protocol compliance checking
- **Security Test Runner**: Automated security test execution

## Security-Specific Configuration

### Symbolic Execution Security Considerations

The configuration includes special handling for symbolic execution code:

- **Controlled Code Execution**: Allows limited use of `eval` and `exec` in controlled contexts
- **Resource Monitoring**: Checks for resource exhaustion vulnerabilities
- **Path Traversal Protection**: Prevents file system attacks
- **Command Injection Prevention**: Validates subprocess usage

### CVE and Vulnerability Management

- **Automated Scanning**: Continuous dependency vulnerability checking
- **Security Test Integration**: Automated security test execution
- **Compliance Reporting**: Security audit trail generation

## Usage

### Initial Setup

```bash
# Install pre-commit hooks
pre-commit install

# Install development dependencies
pip install -e ".[dev]"

# Run initial checks
pre-commit run --all-files
```

### Manual Execution

```bash
# Run all quality checks
pre-commit run --all-files

# Run specific tools
black --check main.py
flake8 main.py
mypy main.py
bandit -r main.py

# Security scanning
bandit -r main.py -f json -o bandit-report.json
safety check
semgrep --config=auto main.py
```

### Git Hooks Integration

The pre-commit hooks automatically run on:
- Every commit
- Manual execution with `pre-commit run`
- CI/CD pipeline integration

## Tool Configuration Details

### Black Configuration
- Line length: 88 characters
- Target versions: Python 3.11, 3.12, 3.13
- Excludes build artifacts and cache directories

### Flake8 Configuration
- Max line length: 88 characters
- Security-focused rules enabled
- Custom symbolic execution patterns
- Complexity limits: 10 (cyclomatic), 15 (cognitive)

### MyPy Configuration
- Strict type checking enabled
- Python 3.11+ target
- Custom overrides for symbolic execution libraries

### Bandit Configuration
- Low severity and confidence checks
- Custom security rules for symbolic execution
- Exclusions for test files and controlled usage

### Pylint Configuration
- Comprehensive static analysis
- Security extensions enabled
- Complexity and maintainability checks
- Custom rules for symbolic execution patterns

## CI/CD Integration

The configuration is designed for seamless CI/CD integration:

```yaml
# Example GitHub Actions usage
- name: Run quality checks
  run: |
    pre-commit run --all-files
    python -m pytest tests/security/
```

## Security Considerations

### Protected Files
The `.gitignore` excludes:
- Credentials and secrets (`.env*`, `*.key`, `*.pem`)
- Security reports and vulnerability scans
- CrossHair symbolic execution artifacts
- Development and debug files

### Sensitive Operations
Some security-related operations require special handling:
- Symbolic execution may use controlled `eval` operations
- Memory monitoring for resource exhaustion prevention
- Path validation for symbolic execution file operations

## Troubleshooting

### Common Issues

1. **Pre-commit hook failures**:
   ```bash
   # Update hooks
   pre-commit autoupdate

   # Clean hooks
   pre-commit clean

   # Reinstall
   pre-commit install
   ```

2. **Type checking failures**:
   ```bash
   # Install stubs
   pip install types-psutil types-requests

   # Check specific files
   mypy main.py --follow-imports=silent
   ```

3. **Security scan false positives**:
   - Add `# nosec` comments for controlled usage
   - Update `.bandit` configuration for project-specific rules
   - Use `# bandit: skip` for specific lines

## Maintenance

### Regular Updates

```bash
# Update pre-commit hooks
pre-commit autoupdate

# Update security tools
pip install --upgrade bandit safety semgrep

# Review configuration quarterly
pre-commit run --all-files
```

### Configuration Reviews

- Quarterly review of security rules
- Annual update of tool versions
- Regular assessment of complexity thresholds
- Update of dependency scanning rules

## Contributing

When contributing to the Symbolic MCP project:

1. Install pre-commit hooks: `pre-commit install`
2. Run quality checks: `pre-commit run --all-files`
3. Ensure all security tests pass
4. Follow commit message standards (conventional commits)
5. Maintain type annotations and documentation

## Additional Resources

- [Black Documentation](https://black.readthedocs.io/)
- [Flake8 Documentation](https://flake8.pycqa.org/)
- [MyPy Documentation](https://mypy.readthedocs.io/)
- [Bandit Security Scanner](https://bandit.readthedocs.io/)
- [Pre-commit Framework](https://pre-commit.com/)
- [Conventional Commits](https://www.conventionalcommits.org/)