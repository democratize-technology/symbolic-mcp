<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2025 Symbolic MCP Contributors -->

---
name: ❓ Question
about: Ask a question about using or developing Symbolic MCP
title: "[QUESTION]: "
labels: ["question", "needs-triage"]
assignees: ""

---

# ❓ Question

**Welcome to the Symbolic MCP community!** This template helps you get the best answers to your questions.

## 🎯 Question Context

### What are you trying to accomplish?

<!-- Describe your goal or what you're trying to achieve -->

```python
# Example of what you're trying to do
code_to_analyze = """
def function_to_analyze(param: str) -> bool:
    # Your code here
    pass
"""

# What you want to know
result = symbolic_check(code_to_analyze, "function_to_analyze")
# Question: How do I interpret these results?
```

### Question Category

- [ ] **Usage Question**: How to use the tool
- [ ] **Development Question**: How to contribute or extend
- [ ] **Security Question**: Security-related concerns
- [ ] **Performance Question**: Performance optimization
- [ ] **Integration Question**: Integration with other tools
- [ ] **Architecture Question**: Design or implementation questions
- [ ] **General Question**: Other inquiries

## 🔍 What You've Tried

### Code Attempts

<!-- Show what you've already tried -->

```python
# Your attempt #1
result = symbolic_check(code, "function")
print(result)
# Output: {...}

# Your attempt #2 (if applicable)
# ...
```

### Documentation Reviewed

- [ ] **README.md**: Project overview and quick start
- [ ] **Contributing Guidelines**: Development practices
- [ ] **Security Documentation**: Security considerations
- [ ] **API Documentation**: Function references
- [ ] **Examples**: Usage examples
- [ ] **Issues**: Searched existing questions

### Commands Run

<!-- Show commands you've tried -->

```bash
# Commands you've run
python main.py --help
echo '{"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 1}' | python main.py
# Output or errors received
```

## 💡 Expected vs Actual Behavior

### What you expected to happen

<!-- Describe what you thought would happen -->

### What actually happened

<!-- Describe what actually occurred -->

### Error messages

<!-- Paste any error messages -->

```
Error messages here
```

## 🧪 Environment Details

### Your Setup

- **OS**: [e.g., macOS 14.0, Ubuntu 22.04, Windows 11]
- **Python Version**: [e.g., 3.11.7, 3.12.1]
- **Symbolic MCP Version**: [e.g., v1.0.0, main branch]
- **Installation Method**: [pip install, git clone, docker]

### Dependencies

```bash
# Show your installed versions
pip list | grep -E "(fastmcp|crosshair|z3|icontract|RestrictedPython)"
```

### Configuration

```yaml
# Your configuration if applicable
symbolic_mcp:
  memory_limit: "2GB"
  timeout: "30s"
  # other settings
```

## 📚 Additional Context

### Related Work

- **Research**: Any relevant research papers or articles
- **Similar Tools**: Other tools you've tried
- **Use Case**: Specific application or project

### Constraints or Requirements

- **Performance**: Specific performance requirements
- **Security**: Security constraints or requirements
- **Integration**: Integration with specific tools or systems
- **Compliance**: Regulatory or compliance requirements

---

## 🚀 Quick Start Help

If you're new to Symbolic MCP, here are some quick resources:

### Basic Usage Examples

```python
# Check function contracts
result = symbolic_check("""
def divide(a: int, b: int) -> float:
    return a / b
""", "divide")

# Find exception paths
exception_result = find_path_to_exception("""
def authenticate(user_id: int, token: str) -> bool:
    if len(token) < 8:
        return False
    return verify_token(token)
""", "authenticate", "ValueError")
```

### Common Questions

**Q: How do I analyze multiple functions?**
```python
# Analyze each function separately
functions = ["func1", "func2", "func3"]
for func in functions:
    result = symbolic_check(code, func)
```

**Q: What modules are available for symbolic execution?**
A: Only 21 vetted modules: `math`, `random`, `string`, `collections`, `itertools`, `functools`, `operator`, `typing`, `re`, `json`, `datetime`, `decimal`, `fractions`, `statistics`, `dataclasses`, `enum`, `copy`, `heapq`, `bisect`, `typing_extensions`, `abc`

**Q: How do I handle timeouts?**
```python
# Increase timeout for complex analysis
result = symbolic_check(complex_code, "function", timeout_seconds=120)
```

---

## 📞 Getting Help

### Community Resources

- **GitHub Discussions**: [General questions and discussions](https://github.com/your-org/symbolic-mcp/discussions)
- **Documentation**: [Complete documentation](https://symbolic-mcp.readthedocs.io/)
- **Examples**: [Usage examples](https://github.com/your-org/symbolic-mcp/tree/main/examples)
- **Security Policy**: [Security questions and reporting](../SECURITY.md)

### Debug Commands

```bash
# Check server health
echo '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "health_check", "arguments": {}}, "id": 1}' | python main.py

# Test with debug logging
python main.py --log-level DEBUG

# Verify dependencies
python -c "import fastmcp, crosshair, z3; print('All dependencies OK')"
```

### Learning Resources

- **Symbolic Execution**: [Learn about symbolic execution](https://en.wikipedia.org/wiki/Symbolic_execution)
- **CrossHair**: [CrossHair documentation](https://crosshair.readthedocs.io/)
- **Z3 Solver**: [Z3 theorem prover](https://github.com/Z3Prover/z3)
- **FastMCP**: [MCP server framework](https://fastmcp.readthedocs.io/)

---

**Thank you for your question!** Our community is here to help you succeed with symbolic execution.

### 🏷️ Post-Question Actions

Once your question is answered:

- [ ] **Mark as answered**: Close the issue with a comment
- [ ] **Share solution**: Help others by sharing what worked
- [ ] **Improve docs**: Suggest documentation improvements
- [ ] **Contribute**: Consider contributing if you have expertise

### 🤝 Contributing Back

If you become knowledgeable about Symbolic MCP:

- **Answer questions**: Help others in discussions
- **Improve docs**: Update documentation with what you learned
- **Share examples**: Contribute usage examples
- **Report issues**: Help identify and fix bugs

---

## 📖 Additional Resources

### Technical Documentation

- [API Reference](../docs/api.md): Complete function documentation
- [Security Guide](../SECURITY.md): Security considerations and best practices
- [Contributing Guide](../CONTRIBUTING.md): Development guidelines
- [Architecture Overview](../docs/architecture.md): System design and architecture

### Community

- **GitHub Discussions**: [Community discussions](https://github.com/your-org/symbolic-mcp/discussions)
- **Discord/Slack**: [Join our community chat](https://discord.gg/symbolic-mcp)
- **Twitter/X**: [@SymbolicMCP](https://twitter.com/SymbolicMCP)
- **Blog**: [Symbolic MCP Blog](https://blog.symbolic-mcp.org)

**Happy symbolic execution!** 🚀