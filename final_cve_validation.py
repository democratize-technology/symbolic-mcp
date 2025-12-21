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
Final CVE-003-001 validation test.
Validates that the security harness properly isolates project modules.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# Import the security harness directly to test it
from tests.integration.test_security_harness import SecurityTestHarness

def test_security_harness_isolation():
    """Test that the security harness properly isolates project modules"""
    print("🔒 Testing Security Harness Isolation")
    print("=" * 50)

    # Create security harness with process isolation enabled
    harness = SecurityTestHarness(use_process_isolation=True)

    # Test 1: Isolation verification
    print("\n1. Testing process isolation verification...")
    isolation_verified = harness.verify_isolation_security()
    print(f"   Isolation verification: {'✅ PASSED' if isolation_verified else '🚨 FAILED'}")

    # Test 2: Run specific isolation breach attacks
    print("\n2. Testing isolation breach attacks...")
    isolation_attacks = [
        ("symbolic_mcp_breach", "import symbolic_mcp"),
        ("src_breach", "import src"),
        ("main_breach", "import main"),
        ("tests_breach", "import tests"),
    ]

    all_blocked = True
    for attack_name, payload in isolation_attacks:
        print(f"   Testing: {attack_name}")
        result = harness.execute_attack(payload, attack_name)
        blocked = result.blocked
        print(f"     Result: {'✅ BLOCKED' if blocked else '🚨 BYPASSED'}")
        if not blocked:
            all_blocked = False
            print(f"     Error: {result.error_message}")

    # Test 3: Full security test suite
    print("\n3. Running full security test suite...")
    suite = harness.run_security_test_suite("cve_validation_test")

    print(f"   Total attacks: {suite.total_attacks}")
    print(f"   Blocked: {suite.blocked_attacks}")
    print(f"   Bypassed: {suite.bypassed_attacks}")
    print(f"   Security score: {suite.security_score:.2%}")

    # Test 4: Verify no vulnerabilities found
    print(f"   Vulnerabilities found: {len(suite.vulnerabilities_found)}")
    if suite.vulnerabilities_found:
        print("   🚨 Vulnerabilities:")
        for vuln in suite.vulnerabilities_found:
            print(f"     - {vuln}")

    # Final assessment
    print(f"\n{'=' * 50}")
    print("CVE-003-001 VALIDATION RESULTS:")
    print(f"Process Isolation: {'✅ SECURE' if isolation_verified else '🚨 COMPROMISED'}")
    print(f"Isolation Attacks: {'✅ BLOCKED' if all_blocked else '🚨 BYPASSED'}")
    print(f"Security Score: {suite.security_score:.2%}")

    # Check CVE requirements
    cve_fixed = (
        isolation_verified and
        all_blocked and
        suite.bypassed_attacks == 0 and
        suite.security_score >= 0.95
    )

    if cve_fixed:
        print(f"\n✅ CVE-003-001 SUCCESSFULLY FIXED")
        print("✅ Zero-trust architecture properly implemented")
        print("✅ All execution contexts properly isolated")
        print("✅ No false confidence in security testing")
        return True
    else:
        print(f"\n🚨 CVE-003-001 STILL EXISTS")
        print("🚨 Security vulnerabilities remain")
        return False

if __name__ == "__main__":
    success = test_security_harness_isolation()
    sys.exit(0 if success else 1)