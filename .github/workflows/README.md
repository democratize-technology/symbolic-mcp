<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2025 Symbolic MCP Contributors -->
# GitHub Actions Workflows

This directory contains comprehensive GitHub Actions workflows for the symbolic-mcp project, designed to ensure security, quality, and reliability for every commit.

## 📁 Workflow Files

### 1. `ci-cd.yml` - Main CI/CD Pipeline
**Trigger**: Push to main/develop, Pull Requests, Releases

**Jobs**:
- **🔒 Security Scanning**: Bandit static analysis, Safety dependency checks, vulnerability scanning
- **🔍 Code Quality**: Black formatting, isort imports, Flake8 linting, MyPy type checking, Pylint analysis
- **🧪 Test Matrix**: Multi-platform (Linux/macOS/Windows) and multi-version (Python 3.11-3.13) testing
- **🛡️ Security Isolation**: CVE-003-001 specific testing, sandbox escape prevention, memory leak detection
- **🚀 Performance Testing**: Load tests, memory profiling, performance regression checks
- **📦 Build Artifacts**: Package building, validation, SBOM generation
- **🎉 Automated Release**: PyPI publishing, release notes, GitHub releases
- **📊 CI Status Summary**: Comprehensive status reporting and PR comments

### 2. `advanced-security-testing.yml` - Comprehensive Security Testing
**Trigger**: Daily schedule, security-sensitive pushes, manual dispatch

**Jobs**:
- **🎯 CVE-003-001 Simulation**: Specific vulnerability scenario testing
- **🧩 Security Fuzzing**: Atheris-based fuzzing with malformed inputs
- **💾 Memory Safety**: Memory leak detection, resource limit testing
- **🏛️ Sandbox Escape**: Comprehensive escape technique testing

### 3. `integration-testing.yml` - End-to-End Integration Tests
**Trigger**: Push to main/develop, Pull Requests, daily schedule

**Jobs**:
- **🔄 End-to-End Testing**: Full symbolic execution pipeline testing
- **⚡ Load Testing**: Concurrent execution, Locust stress testing
- **🔗 Compatibility Testing**: Multi-version compatibility matrix
- **📊 Performance Testing**: Benchmarking and regression detection

### 4. `semantic-release.yml` - Automated Release Management
**Trigger**: Push to main, manual dispatch

**Jobs**:
- **📋 Prepare Release**: Version calculation, changelog generation
- **🎉 Execute Release**: Package building, PyPI publishing, GitHub releases
- **📬 Post-Release Actions**: Release verification, next version preparation

### 5. `health-check.yml` - Project Health Monitoring
**Trigger**: Weekly schedule, manual dispatch

**Jobs**:
- **🏥 Health Check**: Basic security and quality checks
- **📈 Detailed Reports**: Repository metrics and statistics

## 🔐 Security Features

### CVE-003-001 Protection
- **Sandbox Escape Prevention**: Tests for RestrictedPython bypasses
- **Import Blocking**: Validates dangerous import restrictions
- **Memory Isolation**: Ensures memory limits prevent resource exhaustion
- **Symbolic Execution Security**: Validates CrossHair integration security

### Comprehensive Security Scanning
- **Static Analysis**: Bandit for security vulnerabilities
- **Dependency Scanning**: Safety for known CVEs in dependencies
- **Runtime Security**: Dynamic testing of security boundaries
- **Fuzzing**: Atheris-based randomized input testing

## 🧪 Testing Strategy

### Multi-Platform Testing
- **Operating Systems**: Ubuntu, macOS, Windows
- **Python Versions**: 3.11, 3.12, 3.13
- **FastMCP Versions**: Compatibility with 2.0+ features

### Test Categories
- **Unit Tests**: Core functionality testing
- **Integration Tests**: End-to-end workflow testing
- **Security Tests**: Vulnerability and isolation testing
- **Performance Tests**: Benchmark and regression testing
- **Load Tests**: Concurrent execution and stress testing

## 🚀 Release Process

### Automated Semantic Versioning
- **Conventional Commits**: Automatic version calculation based on commit messages
- **Changelog Generation**: Automated release notes from commit history
- **Multi-Channel Publishing**: PyPI, Test PyPI, GitHub Releases
- **Release Verification**: Post-release installation and functionality testing

### Release Types
- **Major**: Breaking changes (`BREAKING CHANGE` in commits)
- **Minor**: New features (`feat:` in commits)
- **Patch**: Bug fixes and security updates

## 📊 Quality Gates

### Code Quality Requirements
- **Formatting**: Black code formatting enforced
- **Import Sorting**: isort import organization required
- **Linting**: Flake8 rules must pass
- **Type Checking**: MyPy strict mode validation
- **Static Analysis**: Pylint quality metrics

### Security Requirements
- **No High Severity**: Bandit high-severity issues block releases
- **No Known CVEs**: Safety dependency validation required
- **Sandbox Integrity**: Security isolation tests must pass
- **Memory Safety**: No memory leaks or resource exhaustion

### Performance Requirements
- **Response Time**: < 5 seconds for typical analyses
- **Memory Usage**: < 2GB for standard operations
- **Concurrency**: Support for multiple simultaneous analyses
- **Resource Limits**: Timeout and memory protection enforced

## 🔧 Configuration

### Environment Variables
- `PYTHON_DEFAULT_VERSION`: Default Python version (3.12)
- `SECURITY_TEST_TIMEOUT`: Security test timeout (300s)
- `FUZZING_DURATION`: Fuzzing test duration (120s)
- `MEMORY_LIMIT_MB`: Default memory limit (2048MB)
- `PERFORMANCE_THRESHOLD`: Performance threshold (5.0s)

### Required Secrets
- `PYPI_API_TOKEN`: For publishing to PyPI
- `TEST_PYPI_API_TOKEN`: For publishing to Test PyPI
- `GITHUB_TOKEN`: For GitHub API access (automatically provided)

## 📈 Monitoring and Reporting

### CI/CD Status
- **Real-time Status**: GitHub Actions dashboard
- **PR Comments**: Automated test result summaries
- **Artifact Storage**: Test results and reports for 30-90 days
- **Coverage Tracking**: Test coverage reports and trends

### Security Monitoring
- **Daily Security Scans**: Automated vulnerability detection
- **CVE Monitoring**: Dependency vulnerability tracking
- **Security Reports**: Comprehensive security testing results
- **Compliance Documentation**: Security posture documentation

## 🛠️ Maintenance

### Workflow Updates
- **Review Monthly**: Check for outdated actions and dependencies
- **Performance Optimization**: Monitor and optimize workflow execution times
- **Security Updates**: Keep security tools and actions updated
- **Coverage Expansion**: Add new test categories as features evolve

### Troubleshooting
- **Time-Out Issues**: Adjust timeouts for complex analyses
- **Memory Issues**: Monitor memory usage patterns
- **Dependency Conflicts**: Use explicit version pinning
- **Platform-Specific Issues**: Handle OS-specific test requirements

## 📚 Best Practices

### For Developers
1. **Conventional Commits**: Use `feat:`, `fix:`, `BREAKING CHANGE:` prefixes
2. **Security First**: Consider security implications in all changes
3. **Performance Awareness**: Monitor performance impact of new features
4. **Test Coverage**: Maintain comprehensive test coverage
5. **Documentation**: Update documentation with new features

### For Security
1. **Sandbox Integrity**: Never compromise security isolation
2. **Input Validation**: Validate all user inputs
3. **Resource Limits**: Enforce memory and time limits
4. **Audit Trails**: Maintain security audit logs
5. **Regular Updates**: Keep dependencies updated for security patches

### For Releases
1. **Semantic Versioning**: Follow semantic versioning principles
2. **Changelog Quality**: Maintain clear, informative changelogs
3. **Release Verification**: Test releases before publishing
4. **Rollback Planning**: Have rollback procedures ready
5. **Communication**: Announce releases and changes clearly

## 🔗 Integration with Development Tools

### IDE Integration
- **Pre-commit Hooks**: Run formatting and linting locally
- **IDE Extensions**: Black, isort, MyPy IDE integrations
- **Local Testing**: Replicate CI tests locally for faster feedback

### Development Workflow
1. **Feature Branch**: Create branch for new features
2. **Local Testing**: Run tests and security checks locally
3. **Pull Request**: Open PR for review and CI testing
4. **Merge**: Merge after all checks pass
5. **Release**: Automated release on version bumps

### Monitoring and Alerts
- **CI Failures**: Immediate notifications for failed builds
- **Security Issues**: Alert on security vulnerabilities
- **Performance Issues**: Alert on performance regressions
- **Release Issues**: Alert on release failures

---

This comprehensive CI/CD setup ensures that symbolic-mcp maintains high security, quality, and reliability standards throughout the development lifecycle.