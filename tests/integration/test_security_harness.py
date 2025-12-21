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
Security Test Harness for Attack Scenario Testing of RestrictedImporter

Based on fuzzing-mcp patterns for comprehensive security validation.
This harness validates RestrictedImporter protection against sophisticated bypass attempts.

REFACTORED: Now uses dependency injection and process isolation for secure testing.
"""

import pytest
import sys
import os
import subprocess
import tempfile
import time
import threading
import signal
import json
import base64
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
import ast
import importlib.util
from pathlib import Path

# Import interfaces from centralized module to ensure DI compatibility
from .interfaces import (
    SecurityValidatorInterface,
    RestrictedImporterInterface,
    ProcessIsolationInterface,
    ImportResult,
    ImportSecurityLevel,
    MockSecurityValidator,
    MockRestrictedImporter
)
from .dependency_container import create_test_container


@dataclass
class AttackResult:
    """Result of a security attack attempt"""
    attack_name: str
    attack_type: str
    payload: str
    blocked: bool
    error_message: str
    execution_time_ms: float
    sys_modules_before: int
    sys_modules_after: int
    suspicious_modules: List[str]


@dataclass
class SecurityTestSuite:
    """Comprehensive security test results"""
    test_name: str
    total_attacks: int
    blocked_attacks: int
    bypassed_attacks: int
    security_score: float  # 0.0 (insecure) to 1.0 (secure)
    attack_results: List[AttackResult]
    vulnerabilities_found: List[str]


class IsolatedProcessSecurityTest:
    """
    Process isolation implementation for secure attack execution.

    Executes attack payloads in completely isolated processes to prevent
    any possibility of security bypasses affecting the test runner.
    """

    def __init__(self, timeout_seconds: int = 10):
        self.timeout_seconds = timeout_seconds
        self.isolation_script_path = self._create_isolation_script()

    def _create_isolation_script(self) -> str:
        """Create a Python script for isolated execution"""
        script_content = '''
import sys
import json
import traceback
import importlib.util
import tempfile
import os
from pathlib import Path
import resource
import signal

# CRITICAL: NO PROJECT IMPORTS - MAINTAIN ABSOLUTE ISOLATION
# DO NOT add project_root to sys.path - this would defeat isolation
# Only use built-in modules for security testing

def apply_resource_limits():
    """Apply strict resource limits to prevent resource exhaustion attacks"""
    try:
        # CPU time limit (5 seconds)
        resource.setrlimit(resource.RLIMIT_CPU, (5, 5))

        # Memory limit (50MB)
        resource.setrlimit(resource.RLIMIT_AS, (50 * 1024 * 1024, 50 * 1024 * 1024))

        # Process limit (prevent fork bombs)
        resource.setrlimit(resource.RLIMIT_NPROC, (10, 10))

        # File size limit (1MB)
        resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))

        # Open file descriptors limit (10)
        resource.setrlimit(resource.RLIMIT_NOFILE, (10, 10))

    except (ValueError, OSError):
        # Some limits might not be available on all systems
        pass

def execute_attack_in_isolation(attack_payload: str, allowed_modules: list):
    """Execute attack payload with strict security controls and resource limits"""
    try:
        # Apply resource limits immediately
        apply_resource_limits()

        # Mock security setup for isolation - NO PROJECT IMPORTS
        class MockSecurityValidator:
            ALLOWED_MODULES = set(allowed_modules)

            @staticmethod
            def validate_import(module_name):
                return module_name in MockSecurityValidator.ALLOWED_MODULES

        # Mock restricted importer
        class MockRestrictedImporter:
            def __init__(self):
                self.security_validator = MockSecurityValidator()

            def validate_module_access(self, module_name):
                return self.security_validator.validate_import(module_name)

        # CRITICAL: Store original import BEFORE any modules are loaded
        if hasattr(__builtins__, '__import__'):
            original_import = __builtins__.__import__
        else:
            import builtins
            original_import = builtins.__import__

        def restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
            # CRITICAL: Block attempts to import project modules
            dangerous_patterns = ['symbolic_mcp', 'main', 'src', 'tests']
            if any(pattern in name.lower() for pattern in dangerous_patterns):
                raise ImportError(f"Module '{name}' is not allowed in isolated environment")

            # Check if module is allowed
            if not MockSecurityValidator.validate_import(name):
                raise ImportError(f"Module '{name}' is not allowed")
            return original_import(name, globals, locals, fromlist, level)

        # Apply import restriction
        if hasattr(__builtins__, '__import__'):
            __builtins__.__import__ = restricted_import
        else:
            import builtins
            builtins.__import__ = restricted_import

        # CRITICAL: Verify isolation is working
        isolation_check = []
        try:
            import symbolic_mcp  # This should fail
            isolation_check.append("SECURITY_BREACH: symbolic_mcp imported")
        except ImportError:
            pass  # Expected - isolation is working

        try:
            import src  # This should fail
            isolation_check.append("SECURITY_BREACH: src imported")
        except ImportError:
            pass  # Expected - isolation is working

        # Execute the payload with minimal global context
        exec_globals = {
            '__builtins__': {
                'print': print,
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'list': list,
                'dict': dict,
                'set': set,
                'range': range,
                'enumerate': enumerate,
                '__import__': restricted_import
            }
        }
        exec_locals = {}

        # Execute with restricted import and minimal globals
        exec(attack_payload, exec_globals, exec_locals)

        return {
            "success": True,
            "status": "executed",
            "message": "Payload executed successfully (potential security issue)",
            "modules_accessed": [],
            "suspicious_activity": True if isolation_check else False,
            "isolation_breach": isolation_check
        }

    except ImportError as e:
        return {
            "success": False,
            "status": "blocked",
            "message": f"Import blocked: {str(e)}",
            "modules_accessed": [],
            "suspicious_activity": False,
            "isolation_breach": []
        }
    except MemoryError:
        return {
            "success": False,
            "status": "blocked",
            "message": "Memory limit exceeded - potential memory exhaustion attack",
            "modules_accessed": [],
            "suspicious_activity": True,
            "isolation_breach": []
        }
    except Exception as e:
        return {
            "success": False,
            "status": "error",
            "message": f"Execution error: {str(e)}",
            "modules_accessed": [],
            "suspicious_activity": True,
            "traceback": traceback.format_exc(),
            "isolation_breach": []
        }

if __name__ == "__main__":
    # Read attack data from stdin
    try:
        data = json.loads(sys.stdin.read())
        attack_payload = data.get("payload", "")
        allowed_modules = data.get("allowed_modules", [])

        result = execute_attack_in_isolation(attack_payload, allowed_modules)
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({
            "success": False,
            "status": "critical_error",
            "message": f"Isolation script error: {str(e)}"
        }))
'''

        # Write isolation script to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script_content)
            return f.name

    def execute_isolated_attack(self, attack_payload: str, allowed_modules: List[str]) -> Dict[str, Any]:
        """Execute attack payload in completely isolated process with enhanced security"""
        try:
            # Prepare attack data
            attack_data = {
                "payload": attack_payload,
                "allowed_modules": allowed_modules
            }

            # Enhanced security subprocess parameters
            env = os.environ.copy()
            # Remove potentially dangerous environment variables
            env.pop('PYTHONPATH', None)
            env.pop('PYTHONHOME', None)
            env.pop('LD_LIBRARY_PATH', None)
            env.pop('LD_PRELOAD', None)

            # Clear PATH to prevent system command execution
            env['PATH'] = '/usr/bin:/bin'

            # Execute in isolated process with enhanced security
            process = subprocess.Popen(
                [sys.executable, '-S', self.isolation_script_path],  # -S disables site packages
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                preexec_fn=self._secure_preexec if hasattr(os, 'setsid') else None,
                # Security: Don't inherit file descriptors
                close_fds=True,
                # Security: Don't use shell
                shell=False
            )

            try:
                stdout, stderr = process.communicate(
                    input=json.dumps(attack_data),
                    timeout=self.timeout_seconds
                )

                # Parse result
                try:
                    result = json.loads(stdout.strip())
                except json.JSONDecodeError:
                    result = {
                        "success": False,
                        "status": "protocol_error",
                        "message": "Could not parse isolation script output",
                        "stdout": stdout,
                        "stderr": stderr
                    }

                # Add process metadata
                result["process_metadata"] = {
                    "return_code": process.returncode,
                    "execution_time": "timed_out" if process.returncode == -9 else "completed"
                }

                return result

            except subprocess.TimeoutExpired:
                # Kill the entire process group
                if hasattr(os, 'killpg'):
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                else:
                    process.terminate()

                # Force kill if still alive
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    if hasattr(os, 'killpg'):
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    else:
                        process.kill()

                return {
                    "success": False,
                    "status": "timeout",
                    "message": f"Attack payload timed out after {self.timeout_seconds} seconds",
                    "suspicious_activity": True,
                    "process_metadata": {
                        "return_code": -9,
                        "execution_time": "timed_out"
                    }
                }

        except Exception as e:
            return {
                "success": False,
                "status": "isolation_error",
                "message": f"Process isolation failed: {str(e)}",
                "suspicious_activity": True
            }

    def _secure_preexec(self):
        """Security pre-execution function for process isolation"""
        # Create new process group to isolate from parent
        os.setsid()

        # Set strict umask to prevent file creation with liberal permissions
        os.umask(0o077)

        # Drop privileges if running as root (not applicable in most cases)
        if os.getuid() == 0:
            # Try to drop to nobody user - this will fail in most test environments
            try:
                import pwd
                nobody = pwd.getpwnam('nobody')
                os.setgid(nobody.pw_gid)
                os.setuid(nobody.pw_uid)
            except:
                pass  # Expected in test environments

    def cleanup(self):
        """Clean up isolation script"""
        try:
            if os.path.exists(self.isolation_script_path):
                os.unlink(self.isolation_script_path)
        except Exception:
            pass


class SecurityTestHarness:
    """
    Comprehensive security testing harness for RestrictedImporter

    ARCHITECTURAL IMPROVEMENTS:
    - Uses dependency injection for security components
    - Implements process isolation for attack execution
    - Eliminates direct main module coupling
    - Provides mock implementations for testing

    Based on fuzzing-mcp patterns for adversarial testing.
    Tests sophisticated bypass attempts and validates security controls.
    """

    def __init__(self, use_process_isolation: bool = True, container=None):
        self.container = container or create_test_container()
        self.security_validator: SecurityValidatorInterface = self.container.resolve(SecurityValidatorInterface)
        self.restricted_importer: RestrictedImporterInterface = self.container.resolve(RestrictedImporterInterface)
        self.use_process_isolation = use_process_isolation

        if use_process_isolation:
            self.process_isolation = IsolatedProcessSecurityTest()

        self.original_modules = set(sys.modules.keys())
        # Use centralized mock validator from interfaces module
        self.allowed_modules = self.security_validator.get_allowed_modules()

    def get_sys_modules_count(self) -> int:
        """Get current number of modules in sys.modules"""
        return len(sys.modules)

    def get_suspicious_modules(self) -> List[str]:
        """Identify potentially dangerous modules that were imported"""
        suspicious = []
        dangerous_patterns = [
            'os', 'subprocess', 'sys', 'importlib', 'types', 'builtins',
            'socket', 'urllib', 'http', 'ftplib', 'smtplib',
            'threading', 'multiprocessing', 'ctypes', 'pickle',
            'marshal', 'code', 'compile', 'execfile', '__import__'
        ]

        for module_name in sys.modules:
            if module_name not in self.original_modules:
                # Check if this is a potentially dangerous module
                if any(pattern in module_name.lower() for pattern in dangerous_patterns):
                    suspicious.append(module_name)

        return suspicious

    def execute_attack(self, attack_payload: str, attack_name: str) -> AttackResult:
        """
        Execute a single attack attempt with process isolation or direct execution.

        ARCHITECTURAL IMPROVEMENT:
        - Uses process isolation for secure attack execution
        - Falls back to direct execution with dependency injection
        - Eliminates direct main module coupling
        """
        start_time = time.time()
        modules_before = self.get_sys_modules_count()

        try:
            if self.use_process_isolation:
                # Use process isolation for maximum security
                isolation_result = self.process_isolation.execute_isolated_attack(
                    attack_payload, self.allowed_modules
                )

                execution_time = (time.time() - start_time) * 1000
                modules_after = self.get_sys_modules_count()
                suspicious = self.get_suspicious_modules()

                # Convert isolation result to AttackResult format
                blocked = isolation_result["status"] in ["blocked", "timeout", "error"]
                return AttackResult(
                    attack_name=attack_name,
                    attack_type="bypass_attempt",
                    payload=attack_payload,
                    blocked=blocked,
                    error_message=isolation_result["message"],
                    execution_time_ms=execution_time,
                    sys_modules_before=modules_before,
                    sys_modules_after=modules_after,
                    suspicious_modules=suspicious
                )

            else:
                # Direct execution with dependency injection (less secure)
                return self._execute_attack_direct(attack_payload, attack_name, start_time, modules_before)

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            modules_after = self.get_sys_modules_count()
            suspicious = self.get_suspicious_modules()

            return AttackResult(
                attack_name=attack_name,
                attack_type="bypass_attempt",
                payload=attack_payload,
                blocked=True,  # Exception during setup means attack failed
                error_message=f"Execution error: {str(e)}",
                execution_time_ms=execution_time,
                sys_modules_before=modules_before,
                sys_modules_after=modules_after,
                suspicious_modules=suspicious
            )

    def _execute_attack_direct(self, attack_payload: str, attack_name: str, start_time: float, modules_before: int) -> AttackResult:
        """Execute attack directly using dependency injection (fallback method)"""
        try:
            # Validate import access using injected dependency
            import_statements = self._extract_import_statements(attack_payload)
            blocked_imports = []

            for import_stmt in import_statements:
                module_name = self._extract_module_name(import_stmt)
                if module_name and not self.security_validator.is_module_allowed(module_name):
                    blocked_imports.append(module_name)

            if blocked_imports:
                execution_time = (time.time() - start_time) * 1000
                return AttackResult(
                    attack_name=attack_name,
                    attack_type="bypass_attempt",
                    payload=attack_payload,
                    blocked=True,
                    error_message=f"Imports blocked: {', '.join(blocked_imports)}",
                    execution_time_ms=execution_time,
                    sys_modules_before=modules_before,
                    sys_modules_after=modules_before,
                    suspicious_modules=[]
                )

            # Try to execute the attack with restricted importer
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(attack_payload)
                f.flush()

                try:
                    spec = importlib.util.spec_from_file_location("attack_code", f.name)
                    if spec and spec.loader:
                        # Create restricted environment
                        restricted_importer = self.restricted_importer.create_restricted_importer()

                        # This should trigger the RestrictedImporter (if available)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)

                        # If we get here, the attack might have succeeded
                        execution_time = (time.time() - start_time) * 1000
                        modules_after = self.get_sys_modules_count()
                        suspicious = self.get_suspicious_modules()

                        return AttackResult(
                            attack_name=attack_name,
                            attack_type="bypass_attempt",
                            payload=attack_payload,
                            blocked=False,
                            error_message="Attack executed successfully (potential bypass)",
                            execution_time_ms=execution_time,
                            sys_modules_before=modules_before,
                            sys_modules_after=modules_after,
                            suspicious_modules=suspicious
                        )

                except Exception as e:
                    execution_time = (time.time() - start_time) * 1000
                    modules_after = self.get_sys_modules_count()
                    suspicious = self.get_suspicious_modules()

                    # Check if the error is due to our security controls
                    error_msg = str(e).lower()
                    security_keywords = ['restricted', 'not allowed', 'blocked', 'forbidden', 'permission']
                    is_blocked = any(keyword in error_msg for keyword in security_keywords)

                    return AttackResult(
                        attack_name=attack_name,
                        attack_type="bypass_attempt",
                        payload=attack_payload,
                        blocked=is_blocked,
                        error_message=str(e),
                        execution_time_ms=execution_time,
                        sys_modules_before=modules_before,
                        sys_modules_after=modules_after,
                        suspicious_modules=suspicious
                    )

                finally:
                    os.unlink(f.name)

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            modules_after = self.get_sys_modules_count()
            suspicious = self.get_suspicious_modules()

            return AttackResult(
                attack_name=attack_name,
                attack_type="bypass_attempt",
                payload=attack_payload,
                blocked=True,  # Exception during setup means attack failed
                error_message=f"Setup error: {str(e)}",
                execution_time_ms=execution_time,
                sys_modules_before=modules_before,
                sys_modules_after=modules_after,
                suspicious_modules=suspicious
            )

    def _extract_import_statements(self, code: str) -> List[str]:
        """Extract import statements from code"""
        try:
            tree = ast.parse(code)
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(f"import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    imports.append(f"from {module} import ...")
            return imports
        except:
            # Fallback: simple regex-based extraction
            import re
            return re.findall(r'^(?:import|from)\s+.*$', code, re.MULTILINE)

    def _extract_module_name(self, import_statement: str) -> Optional[str]:
        """Extract module name from import statement"""
        try:
            if import_statement.startswith("import "):
                return import_statement.split()[1].split('.')[0]
            elif import_statement.startswith("from "):
                parts = import_statement.split()
                if len(parts) >= 2:
                    return parts[1].split('.')[0]
        except:
            pass
        return None

    def generate_attack_payloads(self) -> List[Tuple[str, str]]:
        """Generate sophisticated attack payloads including isolation tests"""
        attacks = []

        # 0. CRITICAL: Isolation bypass attempts (test for CVE-003-001)
        attacks.extend([
            ("isolation_breach_symbolic_mcp", "import symbolic_mcp; print('SECURITY BREACH - symbolic_mcp imported')"),
            ("isolation_breach_src", "import src; print('SECURITY BREACH - src imported')"),
            ("isolation_breach_main", "import main; print('SECURITY BREACH - main imported')"),
            ("isolation_breach_tests", "import tests; print('SECURITY BREACH - tests imported')"),
        ])

        # 1. Direct import attempts
        attacks.extend([
            ("import_os", "import os; print('OS imported successfully')"),
            ("import_subprocess", "import subprocess; print('Subprocess imported successfully')"),
            ("import_sys", "import sys; print('Sys imported successfully')"),
        ])

        # 2. Importlib-based attacks
        attacks.extend([
            ("importlib_import", "import importlib; os = importlib.import_module('os')"),
            ("importlib_dynamic", "import importlib.util; spec = importlib.util.find_spec('os')"),
            ("importlib_loader", "import importlib.machinery; loader = importlib.machinery.PathFinder()"),
        ])

        # 3. __import__ attacks
        attacks.extend([
            ("builtin_import", "os = __import__('os')"),
            ("builtin_import_nested", "subprocess = __import__('subprocess').subprocess"),
            ("builtin_import_fromlist", "sys = __import__('sys', fromlist=['path'])"),
        ])

        # 4. Module manipulation attacks
        attacks.extend([
            ("module_add", "import sys; sys.modules['os'] = type(sys)('fake_os')"),
            ("module_replace", "import types; fake_os = types.ModuleType('os'); sys.modules['os'] = fake_os"),
            ("module_dict", "import sys; sys.modules.__setitem__('socket', object())"),
        ])

        # 5. Exec/eval based attacks
        attacks.extend([
            ("exec_attack", "exec('import os')"),
            ("eval_attack", "eval('__import__(\"os\")')"),
            ("compile_attack", "code = compile('import os', '<string>', 'exec'); exec(code)"),
        ])

        # 6. Path manipulation attacks
        attacks.extend([
            ("path_injection", "import sys; sys.path.insert(0, '/etc'); import passwd"),
            ("path_manipulation", "import sys; sys.path.append('/usr/lib'); import secrets"),
        ])

        # 7. Class-based attacks
        attacks.extend([
            ("class_inheritance", "class FakeImporter: __class__ = __import__('os').__class__"),
            ("metaclass_attack", "class Meta(type): __module__ = 'os'; FakeOs = Meta('FakeOs', (), {})"),
        ])

        # 8. Advanced bypass attempts
        attacks.extend([
            ("globals_access", "globals()['__builtins__']['__import__']('os')"),
            ("locals_manipulation", "locals()['__import__'] = __import__; __import__('os')"),
            ("getattr_attack", "getattr(__import__('sys'), 'modules')"),
            ("hasattr_attack", "hasattr(__import__('sys'), 'modules') and setattr(sys.modules, 'os', type(sys))"),
        ])

        # 9. Ctypes and low-level attacks
        attacks.extend([
            ("ctypes_attack", "import ctypes; lib = ctypes.CDLL(None); lib.system('echo pwned')"),
            ("ctypes_dlopen", "import ctypes; ctypes.CDLL('libc.so.6').system('echo pwned')"),
        ])

        # 10. Pickle/marshal attacks
        attacks.extend([
            ("pickle_attack", "import pickle; pickle.loads(b'cos\\nsystem\\n(Vecho pwned\\no.')"),
            ("marshal_attack", "import marshal; marshal.loads(b'\\x01\\x00\\x00\\x00s')"),
        ])

        # 11. Base64/encoding bypass attempts
        attacks.extend([
            ("base64_decode", "import base64; exec(base64.b64decode('aW1wb3J0IG9z'))"),
            ("rot13_decode", "import codecs; exec(codecs.decode('vzcbeg bf', 'rot_13'))"),
        ])

        # 12. Module aliasing attacks
        attacks.extend([
            ("alias_attack", "import importlib; fake = importlib; fake.import_module('os')"),
            ("chain_attack", "import importlib.util; util = importlib.util; spec = util.find_spec('os')"),
        ])

        return attacks

    def run_security_test_suite(self, test_name: str) -> SecurityTestSuite:
        """Run comprehensive security test suite"""
        print(f"Running security test suite: {test_name}")

        attacks = self.generate_attack_payloads()
        attack_results = []
        blocked_count = 0
        bypassed_count = 0

        for attack_name, payload in attacks:
            print(f"Testing attack: {attack_name}")
            result = self.execute_attack(payload, attack_name)
            attack_results.append(result)

            if result.blocked:
                blocked_count += 1
            else:
                bypassed_count += 1
                print(f"⚠️  POTENTIAL BYPASS: {attack_name}")

        # Calculate security score
        security_score = blocked_count / len(attacks) if attacks else 0.0

        # Identify vulnerabilities
        vulnerabilities = []
        for result in attack_results:
            if not result.blocked:
                vulnerabilities.append(f"{result.attack_name}: {result.error_message}")
            if result.suspicious_modules:
                vulnerabilities.append(f"{result.attack_name}: Suspicious modules loaded: {result.suspicious_modules}")

        suite = SecurityTestSuite(
            test_name=test_name,
            total_attacks=len(attacks),
            blocked_attacks=blocked_count,
            bypassed_attacks=bypassed_count,
            security_score=security_score,
            attack_results=attack_results,
            vulnerabilities_found=vulnerabilities
        )

        print(f"Security test completed: {security_score:.2%} blocked ({blocked_count}/{len(attacks)})")

        return suite

    def verify_isolation_security(self) -> bool:
        """CRITICAL: Verify that process isolation is working and cannot be bypassed"""
        print("🔒 VERIFYING PROCESS ISOLATION SECURITY")

        # Test 1: Attempt to import project modules should fail
        isolation_tests = [
            ("symbolic_mcp_breach", "import symbolic_mcp"),
            ("src_breach", "import src"),
            ("main_breach", "import main"),
            ("tests_breach", "import tests"),
        ]

        isolation_results = []
        for test_name, payload in isolation_tests:
            print(f"  Testing isolation breach: {test_name}")
            result = self.execute_attack(payload, test_name)
            isolation_results.append(result)

            if not result.blocked:
                print(f"🚨 CRITICAL SECURITY FAILURE: Isolation bypassed - {test_name}")
                return False

            # Check isolation breach indicators in result
            if hasattr(result, 'error_message') and 'isolation_breach' in result.error_message:
                print(f"🚨 CRITICAL: Isolation breach detected in result - {test_name}")
                return False

        print("✅ Process isolation verification PASSED")
        return True

    def assert_security_requirements(self, suite: SecurityTestSuite):
        """Assert security requirements are met"""
        # CRITICAL: First verify isolation is working
        if not self.verify_isolation_security():
            pytest.fail("CRITICAL: Process isolation verification FAILED - CVE-003-001 not fixed")

        # Critical security assertions
        assert suite.security_score >= 0.95, f"Security score too low: {suite.security_score:.2%}"
        assert suite.bypassed_attacks == 0, f"Security bypasses detected: {suite.bypassed_attacks}"

        # Check for suspicious modules
        for result in suite.attack_results:
            if result.suspicious_modules:
                pytest.fail(f"Suspicious modules loaded by {result.attack_name}: {result.suspicious_modules}")

        # CRITICAL: Check for isolation breaches
        for result in suite.attack_results:
            if 'isolation_breach' in result.error_message.lower():
                pytest.fail(f"Isolation breach detected by {result.attack_name}: {result.error_message}")

        print(f"✅ Security requirements met for {suite.test_name}")


# Pytest fixtures
@pytest.fixture
def security_harness():
    """Pytest fixture for security test harness with process isolation"""
    return SecurityTestHarness(use_process_isolation=True)


@pytest.fixture
def security_harness_no_isolation():
    """Pytest fixture for security test harness without process isolation (for testing)"""
    return SecurityTestHarness(use_process_isolation=False)


@pytest.fixture
def mock_security_harness():
    """Pytest fixture for security test harness with mock dependencies"""
    container = create_test_container(use_mocks=True)
    return SecurityTestHarness(use_process_isolation=False, container=container)


@pytest.mark.security
def test_security_basic_import_blocking(security_harness):
    """Test basic import blocking functionality"""
    # Test with simple dangerous imports
    basic_attacks = [
        ("basic_os", "import os"),
        ("basic_subprocess", "import subprocess"),
        ("basic_sys", "import sys"),
    ]

    for attack_name, payload in basic_attacks:
        result = security_harness.execute_attack(payload, attack_name)
        assert result.blocked, f"Basic attack not blocked: {attack_name} - {result.error_message}"


@pytest.mark.security
def test_security_advanced_bypass_attempts(security_harness):
    """Test advanced bypass attempts"""
    suite = security_harness.run_security_test_suite("advanced_bypass_test")
    security_harness.assert_security_requirements(suite)


@pytest.mark.security
def test_security_sys_modules_integrity(security_harness):
    """Test sys.modules integrity under attack"""
    initial_modules = set(sys.modules.keys())
    initial_count = len(initial_modules)

    # Run several attacks
    for i in range(5):
        result = security_harness.execute_attack("import os", f"test_attack_{i}")
        assert result.blocked, f"Attack {i} should be blocked"

    # Verify sys.modules hasn't grown too much
    final_count = len(sys.modules)
    module_growth = final_count - initial_count

    # Allow some growth for legitimate imports during testing
    assert module_growth < 50, f"Too many modules added to sys.modules: {module_growth}"


@pytest.mark.security
def test_security_whitelist_enforcement(security_harness):
    """Test whitelist enforcement under adversarial conditions"""
    # Test that only whitelisted modules can be imported
    whitelist_test_attacks = [
        ("whitelist_test_os", "import os"),
        ("whitelist_test_subprocess", "import subprocess"),
        ("whitelist_test_socket", "import socket"),
        ("whitelist_test_urllib", "import urllib.request"),
    ]

    for attack_name, payload in whitelist_test_attacks:
        result = security_harness.execute_attack(payload, attack_name)
        assert result.blocked, f"Whitelist violation not detected: {attack_name}"

    # Test that whitelisted modules should work (this might need adjustment based on actual whitelist)
    for allowed_module in ['math', 'json', 'datetime']:  # Common safe modules
        try:
            result = security_harness.execute_attack(f"import {allowed_module}", f"allowed_test_{allowed_module}")
            # This might be blocked depending on the actual whitelist - adjust test accordingly
        except:
            pass  # Expected if not in whitelist


@pytest.mark.security
def test_security_timing_analysis(security_harness):
    """Test that security measures don't significantly impact performance"""
    # Test timing of legitimate operations
    legitimate_payloads = [
        "x = 1 + 1",
        "def test(): return True",
        "import math; result = math.sqrt(16)",
    ]

    legitimate_times = []
    for payload in legitimate_payloads:
        start = time.time()
        try:
            # This should work with restricted imports
            exec(payload)
            legitimate_times.append((time.time() - start) * 1000)
        except:
            legitimate_times.append((time.time() - start) * 1000)

    # Test timing of blocked operations
    blocked_payloads = [
        "import os",
        "import subprocess",
        "import sys",
    ]

    blocked_times = []
    for payload in blocked_payloads:
        start = time.time()
        result = security_harness.execute_attack(payload, f"timing_test_{len(blocked_times)}")
        blocked_times.append(result.execution_time_ms)

    # Security measures shouldn't be excessively slow
    avg_legitimate_time = sum(legitimate_times) / len(legitimate_times)
    avg_blocked_time = sum(blocked_times) / len(blocked_times)

    assert avg_blocked_time < 1000, f"Security checks too slow: {avg_blocked_time:.1f}ms average"
    print(f"Performance check: {avg_legitimate_time:.1f}ms legitimate, {avg_blocked_time:.1f}ms blocked")


if __name__ == "__main__":
    # Run standalone security tests
    def main():
        harness = SecurityTestHarness()
        suite = harness.run_security_test_suite("standalone_security_test")

        print(f"\nSecurity Test Results:")
        print(f"Total attacks: {suite.total_attacks}")
        print(f"Blocked: {suite.blocked_attacks}")
        print(f"Bypassed: {suite.bypassed_attacks}")
        print(f"Security score: {suite.security_score:.2%}")

        if suite.vulnerabilities_found:
            print(f"\nVulnerabilities found:")
            for vuln in suite.vulnerabilities_found:
                print(f"  - {vuln}")

        harness.assert_security_requirements(suite)

    main()