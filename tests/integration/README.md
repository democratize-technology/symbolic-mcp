<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2025 Symbolic MCP Contributors -->
# Symbolic Execution MCP Integration Test Suite

A comprehensive integration test suite for the symbolic execution Model Context Protocol (MCP) server, based on fuzzing-mcp patterns for production-ready testing.

## Overview

This integration test suite validates the reliability, security, performance, and resilience of the symbolic execution MCP server under real-world conditions. It implements the same testing patterns used in fuzzing-mcp to ensure robust, production-ready behavior.

## Test Architecture

### Core Test Harnesses

#### 1. E2E Test Harness (`test_e2e_harness.py`)
- **Purpose**: Complete MCP session lifecycle testing
- **Features**:
  - Session initialization and cleanup
  - Request-response validation
  - Load testing with concurrent requests
  - Error handling and recovery
  - Metrics collection and analysis

#### 2. Load Test Harness (`test_load_harness.py`)
- **Purpose**: Performance monitoring with psutil integration
- **Features**:
  - Real-time resource monitoring (CPU, memory, I/O)
  - Concurrent request testing
  - Performance baseline validation
  - Scalability testing
  - Resource usage analysis

#### 3. Security Test Harness (`test_security_harness.py`)
- **Purpose**: Attack scenario testing of RestrictedImporter
- **Features**:
  - Sophisticated bypass attempt testing
  - Sys.modules integrity validation
  - Whitelist enforcement verification
  - Adversarial pattern testing
  - CVSS 0.0 security claim validation

#### 4. Memory Leak Detector (`test_memory_leak_detector.py`)
- **Purpose**: Memory usage validation under load
- **Features**:
  - Long-running memory monitoring
  - Memory leak detection
  - Garbage collection verification
  - Memory pattern analysis
  - Resource limit compliance (Section 5.2)

#### 5. CrossHair Failure Test Harness (`test_crosshair_failure_harness.py`)
- **Purpose**: Integration failure scenario testing
- **Features**:
  - Timeout handling validation
  - Z3 solver exhaustion testing
  - Graceful degradation verification
  - Error recovery testing
  - CrossHair availability validation

#### 6. Failing Integration Tests (`test_failing_integration_tests.py`)
- **Purpose**: Demonstrates current integration issues
- **Features**:
  - Expected failure scenarios
  - Integration problem identification
  - Regression testing framework
  - Current limitations documentation

## Test Categories

### Integration Tests (标记: `@pytest.mark.integration`)
- Basic MCP functionality validation
- End-to-end workflow testing
- Session management verification

### Load Tests (标记: `@pytest.mark.load`)
- Performance under concurrent load
- Resource usage monitoring
- Scalability validation
- Response time analysis

### Security Tests (标记: `@pytest.mark.security`)
- RestrictedImporter attack testing
- Bypass attempt validation
- Security control verification
- Adversarial scenario testing

### Memory Tests (标记: `@pytest.mark.memory`)
- Memory leak detection
- Long-running stability testing
- Resource limit compliance
- Garbage collection verification

### Resilience Tests (标记: `@pytest.mark.resilience`)
- Timeout handling testing
- Error recovery validation
- Graceful degradation testing
- Failure scenario testing

### Failing Tests (标记: `@pytest.mark.failing`)
- Current integration issues
- Expected failure documentation
- Problem demonstration
- Regression prevention

## Running Tests

### Quick Start

```bash
# Activate virtual environment
source venv/bin/activate

# Run all integration tests
python tests/integration/test_runner.py

# Run with verbose output
python tests/integration/test_runner.py --verbose

# Generate detailed report
python tests/integration/test_runner.py --output test_report.md
```

### Category-Specific Testing

```bash
# Run only basic integration tests
python tests/integration/test_runner.py --category basic

# Run security tests
python tests/integration/test_runner.py --category security

# Run performance tests
python tests/integration/test_runner.py --category load

# Run memory tests (may take longer)
python tests/integration/test_runner.py --category memory --include-memory
```

### Using Pytest Directly

```bash
# Run all integration tests
python -m pytest tests/integration/ -v

# Run specific test file
python -m pytest tests/integration/test_e2e_harness.py -v

# Run with markers
python -m pytest tests/integration/ -m "not slow" -v  # Skip slow tests
python -m pytest tests/integration/ -m "security" -v   # Security tests only

# Include slow tests
python -m pytest tests/integration/ --run-slow -v

# Include memory tests
python -m pytest tests/integration/ --run-memory -v
```

## Test Configuration

### Environment Setup

1. **Dependencies**: Ensure all requirements are installed
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Environment Variables**: Optional configuration
   ```bash
   export INTEGRATION_TEST_TIMEOUT=30      # Default test timeout
   export INTEGRATION_TEST_VERBOSE=1       # Verbose output
   ```

### Performance Baselines

The test suite includes performance expectations defined in `conftest.py`:

- **Response Times**:
  - Simple functions: < 5 seconds
  - Complex functions: < 15 seconds
  - Timeout scenarios: < 30 seconds

- **Throughput**:
  - Light load: > 0.5 req/s
  - Medium load: > 0.2 req/s
  - Heavy load: > 0.1 req/s

- **Memory Limits**:
  - Max growth: < 100MB during tests
  - Peak usage: < 500MB
  - Leak threshold: > 50MB indicates potential leak

- **Security Requirements**:
  - Attack block rate: > 95%
  - Security bypasses: 0 allowed
  - Security response time: < 1 second

## Test Scenarios

### 1. E2E Session Lifecycle Testing

**Objective**: Validate complete MCP session management
**Tests**:
- Session initialization and cleanup
- Request-response cycle validation
- Concurrent session handling
- Error recovery and cleanup
- Resource management

### 2. Performance Under Load

**Objective**: Ensure performance characteristics meet production requirements
**Tests**:
- Concurrent request handling
- Resource usage monitoring
- Response time validation
- Scalability limits
- Memory usage stability

### 3. Security Validation

**Objective**: Verify RestrictedImporter protection against bypass attempts
**Tests**:
- Import restriction enforcement
- Sys.modules protection
- Whitelist compliance
- Advanced bypass attempts
- Attack pattern resistance

### 4. Memory Leak Detection

**Objective**: Ensure no memory leaks under sustained operation
**Tests**:
- Long-running operation testing
- Memory growth monitoring
- Garbage collection verification
- Resource limit compliance
- Pattern analysis

### 5. CrossHair Integration Resilience

**Objective**: Validate graceful handling of CrossHair failures
**Tests**:
- Timeout handling
- Z3 solver exhaustion
- Error recovery
- Graceful degradation
- Availability validation

## Interpreting Results

### Success Criteria

✅ **All Tests Pass**: System is production-ready
⚠️ **Some Tests Fail**: Review specific areas
❌ **Critical Failures**: System not ready for production

### Common Issues and Solutions

#### Symbolic Execution Returns 'unknown'
**Issue**: Tests expecting specific counterexamples get 'unknown' status
**Cause**: CrossHair integration issues or solver limitations
**Solution**: Review CrossHair configuration and timeout settings

#### Security Tests Fail
**Issue**: Security bypasses detected
**Cause**: RestrictedImporter vulnerabilities
**Solution**: Review and strengthen import restrictions

#### Memory Leak Detection
**Issue**: Memory growth exceeds thresholds
**Cause**: Object accumulation or resource retention
**Solution**: Review object lifecycle and cleanup procedures

#### Performance Degradation
**Issue**: Response times exceed baselines
**Cause**: Resource contention or inefficient algorithms
**Solution**: Profile and optimize critical paths

### Reporting

The test suite generates comprehensive reports:

1. **Console Summary**: Quick overview of test results
2. **Markdown Report**: Detailed analysis (use `--output report.md`)
3. **JSON Results**: Machine-readable results (use `--json results.json`)

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'

    - name: Install dependencies
      run: |
        python -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt

    - name: Run integration tests
      run: |
        source venv/bin/activate
        python tests/integration/test_runner.py --output integration_report.md

    - name: Upload test report
      uses: actions/upload-artifact@v2
      with:
        name: integration-report
        path: integration_report.md
```

### Docker Testing

```dockerfile
FROM python:3.9

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN source venv/bin/activate && python tests/integration/test_runner.py

CMD ["source", "venv/bin/activate", "python", "tests/integration/test_runner.py"]
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure virtual environment is activated
2. **Timeout Issues**: Increase timeout values in test configuration
3. **Resource Limits**: Ensure sufficient system resources for testing
4. **CrossHair Availability**: Some tests work even without CrossHair (graceful degradation)

### Debug Mode

```bash
# Run with maximum verbosity
python -m pytest tests/integration/ -v -s --tb=long

# Run specific failing test
python -m pytest tests/integration/test_failing_integration_tests.py::TestFailingIntegrationScenarios::test_symbolic_check_returns_expected_status -v -s

# Run with debugger
python -m pytest tests/integration/ --pdb
```

## Contributing

When adding new tests:

1. **Follow the Pattern**: Use existing harnesses and patterns
2. **Add Markers**: Use appropriate pytest markers
3. **Document Scenarios**: Clearly document what each test validates
4. **Include Cleanup**: Ensure proper resource cleanup
5. **Update Baselines**: Adjust performance baselines if needed

## Security Considerations

- Tests include actual security attack scenarios
- Ensure testing environment is isolated
- Review test payloads before execution
- Monitor for unexpected system behavior during security tests

## Performance Considerations

- Memory tests are resource-intensive
- Use appropriate markers to control test execution
- Monitor system resources during test execution
- Consider parallel test execution for faster results

## License

This test suite is part of the symbolic execution MCP server project and follows the same licensing terms.

---

**Note**: This integration test suite is designed to catch real-world issues that may not be apparent in unit testing. Regular execution is recommended to ensure system reliability.