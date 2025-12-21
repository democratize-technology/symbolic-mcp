<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2025 Symbolic MCP Contributors -->

# Contributing to Symbolic MCP Server

Thank you for your interest in contributing to the Symbolic MCP Server! This document provides comprehensive guidelines for contributing to our production-ready symbolic execution engine.

## Table of Contents

1. [Development Environment Setup](#development-environment-setup)
2. [Code Standards and Testing](#code-standards-and-testing)
3. [Pull Request Process](#pull-request-process)
4. [Security Development Practices](#security-development-practices)
5. [Debugging and Testing Procedures](#debugging-and-testing-procedures)
6. [FastMCP 2.0 Development Patterns](#fastmcp-20-development-patterns)
7. [Integration Testing Requirements](#integration-testing-requirements)
8. [Code Review Process](#code-review-process)
9. [Release and Contribution Guidelines](#release-and-contribution-guidelines)
10. [Development Tools and Resources](#development-tools-and-resources)

---

## Development Environment Setup

### Prerequisites

- **Python 3.11+** (required for type hints and modern features)
- **Git** for version control
- **4GB+ RAM** (Z3 solver requirements)
- **Docker** (for containerized development and testing)

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/your-org/symbolic-mcp.git
cd symbolic-mcp

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode for local changes
pip install -e .
```

### Development Tools Installation

```bash
# Install development dependencies
pip install black flake8 mypy pytest-cov bandit pre-commit

# Set up pre-commit hooks (optional but recommended)
pre-commit install
```

### Verification

```bash
# Verify installation by running core tests
python -m pytest tests/test_integration.py -v

# Check that symbolic execution works
python main.py --help
```

### IDE Configuration

For optimal development experience, configure your IDE with:

- **Python 3.11+** interpreter
- **Black** code formatter
- **mypy** type checker
- **pytest** test runner

Recommended VS Code extensions:
- Python
- Black Formatter
- Mypy Type Checker
- Python Test Explorer

---

## Code Standards and Testing

### Code Formatting

We use **Black** for consistent code formatting:

```bash
# Format code
black .

# Check formatting without changing files
black --check .
```

### Type Checking

Strict type checking is enforced with **mypy**:

```bash
# Run type checking
mypy main.py --strict

# Check all Python files
mypy . --strict
```

### Linting

Code quality is enforced with **flake8**:

```bash
# Run linting
flake8 main.py tests/

# With configuration
flake8 --max-line-length=88 --extend-ignore=E203,W503 .
```

### Security Scanning

All code must pass security scanning:

```bash
# Run security linter
bandit -r main.py -f json

# Check for common security issues
bandit -r . --severity-level medium
```

### Testing Standards

#### Unit Tests

- **100% test coverage** for new features
- Test file naming: `test_*.py`
- Use descriptive test names
- Include edge cases and error conditions

```python
import pytest
from main import symbolic_check

def test_symbolic_check_division_by_zero():
    """Test that symbolic_check identifies division by zero."""
    code = """
    def divide(a: int, b: int) -> float:
        return a / b
    """
    result = symbolic_check(code, "divide")
    assert result["found_issues"] is True
    assert "division by zero" in str(result["issues"]).lower()
```

#### Integration Tests

Integration tests are located in `tests/integration/`:

```bash
# Run all integration tests
python tests/integration/test_runner.py

# Run specific categories
python tests/integration/test_runner.py --category security
python tests/integration/test_runner.py --category load
```

#### Test Categories

- **Unit Tests**: Individual function testing
- **Integration Tests**: End-to-end MCP functionality
- **Security Tests**: Attack scenario validation
- **Load Tests**: Performance under concurrent requests
- **Memory Tests**: Long-running stability validation

### Test Execution

```bash
# Run all tests with coverage
pytest --cov=main --cov-report=html --cov-report=term

# Run specific test file
pytest tests/test_symbolic_execution.py -v

# Run with markers
pytest -m "not slow" -v  # Skip slow tests
pytest -m "security" -v   # Security tests only
```

---

## Pull Request Process

### Branch Naming

Use descriptive branch names:

```bash
# Feature branches
feature/symbolic-function-comparison
feature/enhanced-error-reporting

# Bug fix branches
fix/memory-leak-in-crosshair
fix/security-bypass-in-importer

# Documentation branches
docs/api-reference-update
docs/contributing-guide
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add symbolic function comparison capability
fix: resolve memory leak in CrossHair integration
sec: strengthen RestrictedImporter against bypass attempts
docs: update API documentation for new tools
test: add integration tests for timeout handling
refactor: simplify symbolic execution context management
```

### Pull Request Template

```markdown
## Description
Brief description of changes and motivation.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Security fix

## Testing
- [ ] Unit tests pass locally
- [ ] Integration tests pass locally
- [ ] Security tests pass locally
- [ ] Manual testing completed

## Security Considerations
- [ ] Code reviewed for security vulnerabilities
- [ ] No hardcoded secrets or credentials
- [ ] Input validation implemented
- [ ] Error messages don't leak sensitive information

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] Security scanning passed
```

### PR Submission Process

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Develop and Test**
   ```bash
   # Make changes
   # Run tests
   pytest
   # Check formatting
   black .
   # Type check
   mypy . --strict
   # Security scan
   bandit -r main.py
   ```

3. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

4. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   # Create PR on GitHub with proper template
   ```

---

## Security Development Practices

### Security-First Development

This project handles arbitrary code execution and must prioritize security:

#### 1. Import Restriction Compliance

All code must respect the RestrictedImporter whitelist:

```python
# ALLOWED_MODULES (21 modules only)
ALLOWED_MODULES = {
    'math', 'random', 'string', 'collections', 'itertools', 'functools', 'operator',
    'typing', 're', 'json', 'datetime', 'decimal', 'fractions', 'statistics',
    'dataclasses', 'enum', 'copy', 'heapq', 'bisect', 'typing_extensions', 'abc'
}

# Never expand this list without security review
# Never use dynamic imports or eval() on user code
```

#### 2. Memory and Resource Limits

Always enforce resource limits:

```python
def set_memory_limit(limit_mb: int = 2048):
    """Enforce 2GB memory limit as per Section 5.2 specification."""
    limit_bytes = 2 * 1024 * 1024 * 1024  # 2GB
    resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, -1))
```

#### 3. Input Validation

Validate all user inputs:

```python
def validate_code_input(code: str) -> bool:
    """Validate user-provided code for safety."""
    try:
        # Parse AST to ensure valid Python
        ast.parse(code)
        # Check for dangerous patterns
        dangerous_keywords = ['eval', 'exec', 'compile', '__import__']
        return not any(keyword in code for keyword in dangerous_keywords)
    except SyntaxError:
        return False
```

### Security Testing

#### Attack Scenario Testing

```python
def test_restricted_importer_security():
    """Test that RestrictedImporter blocks dangerous imports."""
    dangerous_code = """
    import os
    os.system('rm -rf /')
    """
    # This should be blocked
    with pytest.raises(ImportError):
        execute_symbolic(dangerous_code)
```

#### Memory Limit Testing

```python
def test_memory_limit_enforcement():
    """Test that memory limits are enforced."""
    memory_intensive_code = """
    huge_list = [0] * (10**9)  # Should exceed 2GB limit
    """
    # Should hit memory limit
    with pytest.raises(MemoryError):
        execute_symbolic(memory_intensive_code)
```

### Security Review Checklist

Before submitting code, verify:

- [ ] No new import statements outside ALLOWED_MODULES
- [ ] All user inputs are validated
- [ ] Memory limits are enforced
- [ ] Error messages don't leak implementation details
- [ ] No hardcoded secrets or credentials
- [ ] All code paths are tested for security bypasses
- [ ] Bandit security scan passes

---

## Debugging and Testing Procedures

### Debugging Symbolic Execution Issues

#### 1. CrossHair Integration Debugging

```bash
# Test CrossHair directly
python -c "
import crosshair
crosshair.enforce_examples()
print('CrossHair working')
"
```

#### 2. Z3 Solver Debugging

```bash
# Test Z3 installation
python -c "
import z3
s = z3.Solver()
s.add(z3.Int('x') > 0)
print(s.check())
print('Z3 working')
"
```

#### 3. FastMCP Transport Debugging

```bash
# Test MCP server directly
python main.py --log-level DEBUG

# In another terminal, test with MCP client
echo '{"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 1}' | python main.py
```

### Common Debugging Scenarios

#### Symbolic Execution Returns 'unknown'

```python
# Debug symbolic execution issues
def debug_symbolic_check(code: str, function_name: str):
    """Debug symbolic execution when it returns 'unknown'."""
    try:
        # Check if CrossHair is available
        import crosshair
        crosshair.enforce_examples()

        # Try simple analysis first
        result = analyze_function(code, function_name, AnalysisOptions(per_condition_timeout=5.0))
        print(f"Analysis result: {result}")

        # Check if function exists and is callable
        module = ast.parse(code)
        for node in ast.walk(module):
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                print(f"Function found: {function_name}")
                break
        else:
            print(f"Function not found: {function_name}")

    except Exception as e:
        print(f"Debug error: {e}")
        import traceback
        traceback.print_exc()
```

#### Memory Limit Issues

```python
# Monitor memory usage
import psutil
import os

def monitor_memory():
    """Monitor current memory usage."""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    print(f"Memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")
```

### Performance Testing

#### Load Testing

```bash
# Run load tests
python tests/integration/test_runner.py --category load

# Monitor system resources
htop  # or Activity Monitor on macOS
```

#### Memory Testing

```bash
# Run memory leak tests
python tests/integration/test_runner.py --category memory --run-memory

# Monitor for memory growth
watch -n 5 'ps aux | grep python'
```

---

## FastMCP 2.0 Development Patterns

### MCP Tool Development

When adding new MCP tools, follow this pattern:

```python
@mcp.tool()
def your_new_tool(
    code: str,
    function_name: str,
    timeout_seconds: int = 30,
    memory_limit_mb: int = 2048
) -> Dict[str, Any]:
    """
    Description of what this tool does.

    Args:
        code: Python code containing the function to analyze
        function_name: Name of the function to analyze
        timeout_seconds: Maximum time for analysis (default: 30)
        memory_limit_mb: Memory limit in MB (default: 2048)

    Returns:
        Dictionary with analysis results
    """
    try:
        # Input validation
        if not validate_code_input(code):
            return {"error": "Invalid code provided"}

        # Security check
        if not is_safe_for_symbolic_execution(code):
            return {"error": "Code contains unsafe operations"}

        # Symbolic execution with limits
        with resource_limits(memory_mb=memory_limit_mb, timeout=timeout_seconds):
            result = perform_symbolic_analysis(code, function_name)

        return format_result(result)

    except TimeoutError:
        return {"error": f"Analysis timed out after {timeout_seconds} seconds"}
    except MemoryError:
        return {"error": f"Memory limit exceeded ({memory_limit_mb} MB)"}
    except Exception as e:
        return {"error": f"Analysis failed: {str(e)}"}
```

### Error Handling Patterns

Use consistent error handling:

```python
class SymbolicExecutionError(Exception):
    """Base exception for symbolic execution errors."""
    pass

class TimeoutError(SymbolicExecutionError):
    """Analysis timeout exceeded."""
    pass

class MemoryLimitError(SymbolicExecutionError):
    """Memory limit exceeded."""
    pass

class SecurityError(SymbolicExecutionError):
    """Security violation detected."""
    pass
```

### Response Format Standards

All tool responses should follow this structure:

```python
{
    "success": bool,
    "result": Any,
    "issues": List[str],
    "metadata": {
        "execution_time": float,
        "memory_used": int,
        "paths_explored": int
    },
    "error": Optional[str]
}
```

---

## Integration Testing Requirements

### Test Categories

#### 1. E2E Session Testing

```python
@pytest.mark.integration
def test_mcp_session_lifecycle():
    """Test complete MCP session from init to cleanup."""
    # Session initialization
    # Tool discovery
    # Request execution
    # Session cleanup
```

#### 2. Security Testing

```python
@pytest.mark.security
def test_import_restriction_enforcement():
    """Test that RestrictedImporter blocks dangerous imports."""
    # Attempt to import blocked modules
    # Verify security violations are caught
    # Test attack scenarios
```

#### 3. Load Testing

```python
@pytest.mark.load
def test_concurrent_request_handling():
    """Test server under concurrent load."""
    # Send multiple concurrent requests
    # Monitor response times
    # Check for resource exhaustion
```

#### 4. Memory Testing

```python
@pytest.mark.memory
def test_memory_leak_prevention():
    """Test for memory leaks under sustained operation."""
    # Run symbolic execution repeatedly
    # Monitor memory growth
    # Verify cleanup works
```

### Running Integration Tests

```bash
# Quick test run
python tests/integration/test_runner.py

# Specific categories
python tests/integration/test_runner.py --category integration
python tests/integration/test_runner.py --category security
python tests/integration/test_runner.py --category load
python tests/integration/test_runner.py --category memory

# Include slow/memory-intensive tests
python tests/integration/test_runner.py --run-slow --run-memory

# Generate detailed report
python tests/integration/test_runner.py --output test_report.md
```

### Test Configuration

Environment variables for testing:

```bash
export INTEGRATION_TEST_TIMEOUT=30      # Test timeout
export INTEGRATION_TEST_VERBOSE=1       # Verbose output
export MEMORY_LIMIT_TEST=4096          # Memory limit for tests (MB)
```

---

## Code Review Process

### Review Guidelines

#### For Authors

1. **Self-Review First**: Review your own code before requesting reviews
2. **Small PRs**: Keep pull requests focused and manageable
3. **Clear Descriptions**: Explain the "why" not just the "what"
4. **Test Coverage**: Ensure comprehensive test coverage
5. **Documentation**: Update relevant documentation

#### For Reviewers

1. **Security First**: Pay special attention to security implications
2. **Code Quality**: Check adherence to project standards
3. **Test Coverage**: Verify adequate testing
4. **Performance**: Consider performance implications
5. **Documentation**: Ensure documentation is updated

### Review Checklist

#### Security Review
- [ ] No new security vulnerabilities introduced
- [ ] Input validation is comprehensive
- [ ] Error messages don't leak sensitive information
- [ ] Resource limits are properly enforced
- [ ] No hardcoded secrets or credentials

#### Code Quality Review
- [ ] Code follows project style guidelines
- [ ] Functions are small and focused
- [ ] Variable names are descriptive
- [ ] Comments explain "why" not "what"
- [ ] No dead code or commented-out code

#### Testing Review
- [ ] Tests cover all new functionality
- [ ] Edge cases are tested
- [ ] Error conditions are tested
- [ ] Integration tests are updated
- [ ] Test names are descriptive

#### Performance Review
- [ ] No obvious performance regressions
- [ ] Memory usage is reasonable
- [ ] Resource limits are respected
- [ ] Scalability considerations addressed

---

## Release and Contribution Guidelines

### Version Management

- **Semantic Versioning**: Follow MAJOR.MINOR.PATCH pattern
- **Changelog**: Maintain detailed changelog
- **Tagging**: Use git tags for releases
- **Branching**: Use feature branches, develop for integration

### Release Process

1. **Pre-Release Checklist**
   ```bash
   # All tests pass
   pytest
   # Security scan passes
   bandit -r main.py
   # Documentation updated
   # Version number updated
   ```

2. **Release Preparation**
   ```bash
   # Update version in main.py
   # Update CHANGELOG.md
   # Create release notes
   git tag -a v1.0.0 -m "Release version 1.0.0"
   ```

3. **Release Verification**
   ```bash
   # Test release build
   docker build -t symbolic-mcp:v1.0.0 .
   # Verify installation
   docker run symbolic-mcp:v1.0.0 python main.py --help
   ```

### Contribution Types

#### Bug Reports
- Use GitHub Issues with detailed reproduction steps
- Include environment information (Python version, OS, etc.)
- Provide minimal reproducible example

#### Feature Requests
- Open issue for discussion before implementation
- Describe use case and expected behavior
- Consider breaking changes and backward compatibility

#### Documentation
- API documentation updates
- Example code improvements
- README and contributing guide updates

#### Security Issues
- Report security issues privately (see SECURITY.md)
- Include detailed vulnerability description
- Provide proof-of-concept if possible

---

## Development Tools and Resources

### Essential Tools

#### Development Environment
- **Python 3.11+**: Core runtime
- **pip**: Package management
- **venv**: Virtual environments
- **git**: Version control

#### Code Quality
- **Black**: Code formatting
- **mypy**: Type checking
- **flake8**: Linting
- **bandit**: Security scanning

#### Testing
- **pytest**: Test framework
- **pytest-cov**: Coverage reporting
- **psutil**: System monitoring (for load testing)

#### Debugging
- **pdb**: Python debugger
- **pytest --pdb**: Test debugging
- **logging**: Structured logging

### Useful Commands

```bash
# Development setup
make dev-setup  # If Makefile exists
python -m venv venv && source venv/bin/activate && pip install -r requirements.txt

# Code quality
black . && mypy . --strict && flake8 . && bandit -r main.py

# Testing
pytest --cov=main --cov-report=html

# Docker
docker build -t symbolic-mcp .
docker run -it symbolic-mcp bash

# Performance monitoring
python tests/integration/test_runner.py --category load

# Security testing
python tests/integration/test_runner.py --category security
```

### Documentation Resources

- [FastMCP Documentation](https://fastmcp.readthedocs.io/)
- [CrossHair Documentation](https://crosshair.readthedocs.io/)
- [Z3 Solver Documentation](https://z3prover.github.io/)
- [Python Type Hinting](https://docs.python.org/3/library/typing.html)
- [Pytest Documentation](https://docs.pytest.org/)

### Community and Support

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Security Issues**: Private vulnerability reporting
- **Documentation**: Project documentation and examples

### Getting Help

If you need help with development:

1. Check existing documentation and issues
2. Search for similar problems in GitHub issues
3. Ask questions in GitHub Discussions
4. For security issues, follow private reporting process

---

## License and Contributing Agreement

By contributing to this project, you agree that your contributions will be licensed under the same license as the project (MIT License).

Please ensure you have the right to contribute any code you submit and that it doesn't violate any third-party licenses or intellectual property rights.

---

Thank you for contributing to the Symbolic MCP Server! Your contributions help make symbolic execution accessible and secure for everyone. 🚀