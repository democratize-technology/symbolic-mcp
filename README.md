<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2025 Symbolic MCP Contributors -->

# Symbolic MCP Server

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://github.com/democratize-technology/symbolic-mcp/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP 2.0](https://img.shields.io/badge/FastMCP-2.0+-blue.svg)](https://fastmcp.readthedocs.io/)
[![Security](https://img.shields.io/badge/security-passing-brightgreen.svg)](SECURITY.md)

> **Production-ready symbolic execution server for the Model Context Protocol (MCP)**

A secure, sandboxed symbolic execution engine built on the FastMCP 2.0 framework that discovers edge cases and hidden bugs in Python code through mathematical path analysis. Unlike traditional fuzzing, symbolic execution treats inputs as symbolic variables and explores all possible execution paths algebraically.

## 🎯 What Makes This Special

**Symbolic execution finds bugs that fuzzing misses:**

- **Path-sensitive analysis**: Explores ALL possible code paths, not just random ones
- **Constraint solving**: Uses Z3 solver to find exact inputs that trigger edge cases
- **Mathematical guarantees**: Proves properties about code behavior
- **Edge case discovery**: Finds inputs that reach deep, conditional bugs

**Perfect for:**
- Security researchers finding vulnerability conditions
- Developers proving function correctness
- QA teams discovering hidden edge cases
- Code review teams verifying mathematical properties

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/democratize-technology/symbolic-mcp.git
cd symbolic-mcp

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -m pytest tests/test_integration.py -v
```

### Basic Usage

**1. Check function contracts:**
```python
code = """
def divide(a: int, b: int) -> float:
    '''Divides two numbers, raises ZeroDivisionError if b is 0'''
    return a / b
"""

result = symbolic_check(code, "divide")
# Returns counterexample if contract violations found
```

**2. Find inputs that cause exceptions:**
```python
# Find inputs that cause ZeroDivisionError
result = find_path_to_exception(code, "divide", "ZeroDivisionError")
# Returns: {"found": True, "example_inputs": {"a": 5, "b": 0}}
```

**3. Prove function equivalence:**
```python
code = """
def add_one_v1(x: int) -> int:
    return x + 1

def add_one_v2(x: int) -> int:
    y = x
    y += 1
    return y
"""

result = compare_functions(code, "add_one_v1", "add_one_v2")
# Returns: {"equivalent": True, "reasoning": "All paths produce same result"}
```

## 🛠️ MCP Tools

The server provides these MCP tools:

| Tool | Description | Use Case |
|------|-------------|----------|
| `symbolic_check` | Verify function contracts | Property-based testing, correctness proofs |
| `find_path_to_exception` | Find inputs causing exceptions | Security analysis, error handling validation |
| `compare_functions` | Check semantic equivalence | Refactoring verification, optimization proof |
| `analyze_branches` | Enumerate reachable code paths | Coverage analysis, dead code detection |
| `health_check` | Server health monitoring | Production monitoring, performance metrics |

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastMCP 2.0   │────│  Security Layer  │────│   CrossHair     │
│   Transport     │    │  - Sandboxing    │    │   + Z3 Solver   │
│   - Stdio/SSE   │    │  - Import Filter │    │   - Symbolic     │
│   - MCP Schema  │    │  - Memory Limits │    │     Execution    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Security Architecture

**Defense-in-depth isolation:**
- **Import filtering**: Whitelist-only access to 21 vetted modules
- **Resource limits**: 2GB memory cap prevents DoS attacks
- **Process isolation**: Each analysis runs in sandboxed context
- **Input validation**: All user code undergoes security validation
- **Timeout protection**: Configurable execution timeouts

**Allowed modules for symbolic execution:**
```
math, random, string, collections, itertools, functools, operator,
typing, re, json, datetime, decimal, fractions, statistics,
dataclasses, enum, copy, heapq, bisect, typing_extensions, abc
```

## 📖 Usage Examples

### Security Analysis

Find conditions that could lead to security vulnerabilities:

```python
code = """
def authenticate(user_id: int, token: str) -> bool:
    if len(token) < 8:
        return False
    if user_id == 0:
        return False
    # Complex authentication logic
    return verify_token(token)

def verify_token(token: str) -> bool:
    return "admin" in token  # Simulated vulnerability
"""

# Find inputs that bypass authentication
result = find_path_to_exception(code, "authenticate", "Exception")
```

### Mathematical Verification

Prove mathematical properties of algorithms:

```python
code = """
def is_prime(n: int) -> bool:
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0:
        return False
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True
"""

# Find counterexamples if any exist
result = symbolic_check(code, "is_prime")
```

### Code Refactoring Safety

Verify that optimized code preserves behavior:

```python
code = """
def find_max_slow(lst: List[int]) -> int:
    max_val = lst[0]
    for item in lst[1:]:
        if item > max_val:
            max_val = item
    return max_val

def find_max_fast(lst: List[int]) -> int:
    return max(lst)  # "Optimized" version
"""

result = compare_functions(code, "find_max_slow", "find_max_fast")
```

### Resource Templates

FastMCP supports RFC 6570 URI templates for dynamic resources:

```python
# Static resource (no parameters)
@mcp.resource("config://security")
def get_security_config() -> dict:
    return {"allowed_modules": ["math", "random"]}

# Path parameter: matches "file://code/foo.py"
@mcp.resource("file://code/{function_name}.py")
def get_function_code(function_name: str) -> str:
    return f"# {function_name} implementation"

# Wildcard path: matches "file://code/utils/helpers.py"
@mcp.resource("file://code/{filepath*}.py")
def get_nested_code(filepath: str) -> str:
    return f"# {filepath} implementation"

# Query parameters: "file://code/foo.py?format=raw&limit=100"
@mcp.resource("file://code/{filename}.py{?format,limit}")
def get_code_with_options(
    filename: str, format: str | None = None, limit: int | None = None
) -> str:
    return fetch_code(filename, format=format, max_lines=limit)
```

### Lifecycle Events

FastMCP servers support lifecycle management for startup/shutdown:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan():
    # Startup: Initialize resources
    print("Symbolic Execution Server starting...")
    yield
    # Shutdown: Clean up resources
    print("Symbolic Execution Server shutting down...")

# Create server with lifespan
mcp = FastMCP("Symbolic Execution Server", lifespan=lifespan)
```

## 🔧 Development Setup

### Prerequisites
- Python 3.11 or higher
- Git
- 4GB+ RAM (Z3 solver requirements)

### Development Environment

```bash
# Clone repository
git clone https://github.com/democratize-technology/symbolic-mcp.git
cd symbolic-mcp

# Set up development environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .

# Install development tools
pip install black flake8 mypy pytest-cov bandit

# Run test suite
python -m pytest tests/ -v --cov=symbolic_mcp

# Run security checks
bandit -r main.py
mypy main.py --strict
```

### Running the Server

```bash
# Development mode (stdio)
python main.py

# Production mode with logging
python main.py --log-level INFO --timeout 60

# With custom memory limit
python main.py --memory-limit 4096
```

### Testing

```bash
# Run all tests
pytest

# Run integration tests only
pytest tests/integration/

# Run security verification tests
pytest tests/test_security_*.py

# Generate coverage report
pytest --cov=main --cov-report=html
```

## 📊 Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| Memory Limit | 2GB (configurable) | Prevents DoS attacks |
| Default Timeout | 30s | Per-analysis limit |
| Supported Code Size | ~10K LOC | Practical limit for Z3 |
| Concurrency | Single-threaded | Safety isolation |
| Warm-up Time | ~2s | CrossHair initialization |

## 🛡️ Security Model

### Threat Mitigation

| Threat | Mitigation | Implementation |
|--------|------------|----------------|
| Code injection | Import whitelist | 21 vetted modules only |
| Memory exhaustion | Resource limits | 2GB hard limit |
| Path explosion | Timeouts + heuristics | Configurable timeouts |
| System access | Process isolation | RestrictedPython wrapper |
| Information leakage | Output sanitization | Error message filtering |

### Security Assumptions

- **Trusted environment**: Host system is secure
- **Limited side-channels**: No network, file system, or system calls
- **Resource constraints**: Attacker cannot exceed memory/time limits
- **Z3 solver trust**: Assumes Z3 is free from critical vulnerabilities

## 🔍 Advanced Configuration

### Custom Analysis Options

```python
# Extended timeout for complex analysis
result = symbolic_check(
    code="complex_algorithm",
    function_name="process_data",
    timeout_seconds=120  # 2 minutes
)

# Memory-aware analysis for large codebases
result = analyze_branches(
    code="large_function",
    function_name="complex_logic",
    timeout_seconds=60
)
```

### Integration with MCP Clients

```python
# Claude Desktop configuration
{
  "mcpServers": {
    "symbolic-execution": {
      "command": "python",
      "args": ["/path/to/symbolic-mcp/main.py"],
      "env": {
        "MEMORY_LIMIT": "4096",
        "TIMEOUT": "60"
      }
    }
  }
}
```

## 📚 Specification & Documentation

- **[Complete Specification](spec/Symbolic%20Execution%20MCP%20Specification.md)** - Technical design and requirements
- **[Security Documentation](SECURITY.md)** - Detailed security analysis and threat model
- **[API Reference](docs/api.md)** - Complete tool reference
- **[Examples](docs/examples.md)** - Comprehensive usage examples

### Architecture Decision Records

This project maintains a comprehensive ADR system following NASA-style documentation standards:

- **[ADR Directory](docs/adr/)** - All architectural decisions with rationale
- **[ADR Summary](docs/adr/SUMMARY.md)** - Quick reference for all 23 ADRs

Key architectural decisions include:
- **ADR-012**: Single-file monolith architecture for security auditability
- **ADR-022**: Dangerous builtins blocking with AST bypass detection
- **ADR-023**: Defense-in-depth security with 6 independent layers

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Write tests for your changes
4. Implement the feature with tests passing
5. Run security validation: `bandit -r main.py`
6. Submit a pull request

### Code Standards

- **Style**: Black formatting, PEP 8 compliance
- **Type hints**: Strict mypy checking required
- **Testing**: 100% test coverage for new features
- **Security**: All code must pass security scanning
- **Documentation**: Docstrings for all public functions

## 📋 Requirements

### Core Dependencies

- **fastmcp>=2.0.0** - MCP server framework
- **crosshair-tool>=0.0.70** - Symbolic execution engine
- **z3-solver>=4.12.0** - SMT solver backend
- **icontract>=2.6.0** - Design by contracts
- **RestrictedPython>=8.1** - Code sandboxing

### Development Dependencies

- **pytest>=7.0.0** - Testing framework
- **bandit>=1.9.0** - Security linting
- **mypy** - Static type checking
- **black** - Code formatting

## 🗺️ Roadmap

### Version 1.1 (Planned)
- [ ] Multi-threaded analysis with isolation
- [ ] Caching for repeated analyses
- [ ] Enhanced error reporting
- [ ] Performance profiling

### Version 1.2 (Research)
- [ ] Loop invariant detection
- [ ] Automatic test generation
- [ ] Symbolic debugger integration
- [ ] Contract synthesis

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **CrossHair team** - Excellent symbolic execution framework
- **Z3 Solver team** - Powerful constraint solving
- **FastMCP team** - Clean MCP server framework
- **Security researchers** - For vulnerability insights and threat models

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/democratize-technology/symbolic-mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/democratize-technology/symbolic-mcp/discussions)
- **Security**: [Security Policy](SECURITY.md)

---

<div align="center">

**Built with ❤️ by the Symbolic MCP Team**

*Making symbolic execution accessible and secure for everyone*

</div>
