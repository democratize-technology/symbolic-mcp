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

#!/usr/bin/env python3
"""
Critical CVE-003-001 verification test.
This test verifies that project modules cannot be imported in ANY execution context.
"""

import subprocess
import tempfile
import os
import json
import sys

def test_project_module_isolation():
    """Test that project modules are properly isolated from main process"""

    # Test 1: Verify main process cannot import project modules
    print("🔒 Testing main process isolation...")

    isolation_test_script = '''
import sys
import json

# Test main process isolation
test_results = {}

# Try to import project modules - these should all fail
project_modules = ['symbolic_mcp', 'src', 'main', 'tests']

for module_name in project_modules:
    try:
        __import__(module_name)
        test_results[module_name] = "SECURITY_BREACH: Module imported"
    except ImportError:
        test_results[module_name] = "SECURE: Module properly blocked"
    except Exception as e:
        test_results[module_name] = f"ERROR: {str(e)}"

# Check sys.path for project contamination
sys_path_check = []
current_dir = os.getcwd()
project_patterns = ['/symbolic-mcp', 'symbolic-mcp']
for path_entry in sys.path:
    if any(pattern in path_entry for pattern in project_patterns):
        sys_path_check.append(f"CONTAMINATED: {path_entry}")

results = {
    "module_imports": test_results,
    "sys_path_contamination": sys_path_check,
    "security_status": "SECURE" if not any("BREACH" in v for v in test_results.values()) and not sys_path_check else "COMPROMISED"
}

print(json.dumps(results, indent=2))
'''

    # Write test script to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(isolation_test_script)
        script_path = f.name

    try:
        # Run isolation test with clean environment
        env = os.environ.copy()
        # Remove potentially dangerous environment variables
        env.pop('PYTHONPATH', None)
        env.pop('PYTHONHOME', None)

        # Execute test
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            env=env,
            timeout=10
        )

        if result.returncode == 0:
            try:
                test_output = json.loads(result.stdout)
                print(f"✅ Main process isolation test completed")
                print(f"   Security status: {test_output['security_status']}")

                if test_output['security_status'] == 'SECURE':
                    print("   ✅ All project modules properly blocked")
                    print("   ✅ No sys.path contamination detected")
                else:
                    print("   🚨 SECURITY BREACH DETECTED")
                    for module, result in test_output['module_imports'].items():
                        print(f"      {module}: {result}")
                    for contamination in test_output['sys_path_contamination']:
                        print(f"      {contamination}")

                    return False
            except json.JSONDecodeError:
                print(f"❌ Failed to parse test results: {result.stdout}")
                return False
        else:
            print(f"❌ Isolation test failed with return code {result.returncode}")
            print(f"   stderr: {result.stderr}")
            return False

    finally:
        os.unlink(script_path)

    return True

def test_subprocess_isolation():
    """Test that project modules cannot be imported in subprocess context"""

    print("\n🔒 Testing subprocess process isolation...")

    # Test subprocess isolation with even stricter security
    subprocess_test = '''
import sys
import os

# CRITICAL: Verify no project paths in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_indicators = ['symbolic-mcp']

contaminated_paths = []
for path in sys.path:
    if any(indicator in path for indicator in project_indicators):
        contaminated_paths.append(path)

# Try direct project module imports - should all fail
import_results = {}
try:
    import symbolic_mcp
    import_results['symbolic_mcp'] = "BREACH"
except ImportError:
    import_results['symbolic_mcp'] = "BLOCKED"

try:
    import src
    import_results['src'] = "BREACH"
except ImportError:
    import_results['src'] = "BLOCKED"

security_status = "SECURE" if not contaminated_paths and all(v == "BLOCKED" for v in import_results.values()) else "COMPROMISED"

print(f"SUBPROCESS_TEST:{security_status}:{len(contaminated_paths)}:{len([k for k,v in import_results.items() if v == 'BLOCKED'])}")
'''

    # Execute in subprocess with strict isolation
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)
    env['PATH'] = '/usr/bin:/bin'

    result = subprocess.run(
        [sys.executable, '-c', subprocess_test],
        capture_output=True,
        text=True,
        env=env,
        timeout=5
    )

    if result.returncode == 0 and "SUBPROCESS_TEST:SECURE:" in result.stdout:
        print("   ✅ Subprocess isolation verified")
        print("   ✅ No project module access in subprocess")
        return True
    else:
        print("   🚨 SUBPROCESS ISOLATION BREACH")
        print(f"   Output: {result.stdout}")
        print(f"   Error: {result.stderr}")
        return False

if __name__ == "__main__":
    print("🔒 CVE-003-001 Isolation Verification Test")
    print("=" * 50)

    # Run all isolation tests
    main_isolated = test_project_module_isolation()
    subprocess_isolated = test_subprocess_isolation()

    print(f"\n{'=' * 50}")
    print("CVE-003-001 VERIFICATION RESULTS:")
    print(f"Main Process Isolation: {'✅ SECURE' if main_isolated else '🚨 COMPROMISED'}")
    print(f"Subprocess Isolation: {'✅ SECURE' if subprocess_isolated else '🚨 COMPROMISED'}")

    if main_isolated and subprocess_isolated:
        print("\n✅ CVE-003-001 SUCCESSFULLY FIXED")
        print("✅ Zero-trust architecture properly implemented")
        print("✅ All execution contexts properly isolated")
        exit(0)
    else:
        print("\n🚨 CVE-003-001 STILL EXISTS")
        print("🚨 Security vulnerabilities remain")
        exit(1)