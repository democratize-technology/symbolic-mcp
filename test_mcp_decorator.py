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

#!/usr/bin/env python3.11
"""
Minimal test to investigate FastMCP 2.0 decorator behavior
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastmcp import FastMCP

# Create minimal FastMCP instance to test decorator behavior
mcp = FastMCP("Test Server")

print("=== FastMCP 2.0 Decorator Investigation ===")
print(f"FastMCP version: {getattr(mcp, '__version__', 'unknown')}")
print()

# Test 1: Basic @mcp.tool() decorator behavior
print("1. Testing @mcp.tool() decorator behavior:")

@mcp.tool()
def test_function_direct_call(x: int, y: int) -> int:
    """Simple function to test decorator behavior"""
    return x + y

print(f"Function type: {type(test_function_direct_call)}")
print(f"Function callable? {callable(test_function_direct_call)}")
try:
    print(f"Function name: {test_function_direct_call.__name__}")
except AttributeError as e:
    print(f"Function name access failed: {e}")
print()

# Test 2: Can we call it directly?
print("2. Testing direct function call:")
try:
    result = test_function_direct_call(5, 3)
    print(f"✅ Direct call successful: {result}")
except Exception as e:
    print(f"❌ Direct call failed: {e}")
    print(f"   Error type: {type(e)}")
print()

# Test 3: Check if it has the original function
print("3. Testing access to underlying function:")
if hasattr(test_function_direct_call, 'fn'):
    print(f"   Has .fn attribute: {test_function_direct_call.fn}")
    print(f"   .fn type: {type(test_function_direct_call.fn)}")
    print(f"   .fn callable? {callable(test_function_direct_call.fn)}")

    try:
        result = test_function_direct_call.fn(5, 3)
        print(f"✅ .fn call successful: {result}")
    except Exception as e:
        print(f"❌ .fn call failed: {e}")
else:
    print("   ❌ No .fn attribute found")

if hasattr(test_function_direct_call, '__wrapped__'):
    print(f"   Has __wrapped__ attribute: {test_function_direct_call.__wrapped__}")
    print(f"   __wrapped__ type: {type(test_function_direct_call.__wrapped__)}")
    print(f"   __wrapped__ callable? {callable(test_function_direct_call.__wrapped__)}")

    try:
        result = test_function_direct_call.__wrapped__(5, 3)
        print(f"✅ __wrapped__ call successful: {result}")
    except Exception as e:
        print(f"❌ __wrapped__ call failed: {e}")
else:
    print("   ❌ No __wrapped__ attribute found")

# Test the .run method if it exists
if hasattr(test_function_direct_call, 'run'):
    import inspect
    print(f"   Has .run method: {test_function_direct_call.run}")
    print(f"   .run signature: {inspect.signature(test_function_direct_call.run)}")
    print(f"   .run callable? {callable(test_function_direct_call.run)}")

    try:
        # Try calling with just arguments (likely expects context)
        result = test_function_direct_call.run({"x": 5, "y": 3})
        print(f"✅ .run call successful: {result}")
    except Exception as e:
        print(f"❌ .run call failed: {e}")
        print(f"   Attempting with context argument...")
        try:
            # Create mock context
            class MockContext:
                def __init__(self):
                    self.request_id = "test"
                    self.session_id = "test_session"

            result = test_function_direct_call.run(MockContext(), {"x": 5, "y": 3})
            print(f"✅ .run call with context successful: {result}")
        except Exception as e2:
            print(f"❌ .run call with context failed: {e2}")
else:
    print("   ❌ No .run attribute found")
print()

# Test 4: Explore the decorator object structure
print("4. Exploring decorator object structure:")
print(f"   Available attributes: {[attr for attr in dir(test_function_direct_call) if not attr.startswith('_')]}")
print()

# Test 5: Check FastMCP internal registry
print("5. Checking FastMCP internal registry:")
print(f"   MCP tools: {getattr(mcp, 'tools', 'No tools attribute')}")
print(f"   MCP _tools: {getattr(mcp, '_tools', 'No _tools attribute')}")

if hasattr(mcp, 'tools') and mcp.tools:
    tool_names = list(mcp.tools.keys())
    print(f"   Registered tool names: {tool_names}")

    if 'test_function_direct_call' in mcp.tools:
        tool_info = mcp.tools['test_function_direct_call']
        print(f"   Tool info type: {type(tool_info)}")
        print(f"   Tool info attributes: {[attr for attr in dir(tool_info) if not attr.startswith('_')]}")

        # Check if the tool object has the original function
        if hasattr(tool_info, 'fn'):
            print(f"   Tool.fn type: {type(tool_info.fn)}")
            print(f"   Tool.fn callable? {callable(tool_info.fn)}")

            try:
                result = tool_info.fn(5, 3)
                print(f"✅ Tool.fn call successful: {result}")
            except Exception as e:
                print(f"❌ Tool.fn call failed: {e}")
        else:
            print("   ❌ Tool has no .fn attribute")

if hasattr(mcp, '_tools') and mcp._tools:
    print(f"   Internal _tools type: {type(mcp._tools)}")
    print(f"   Internal _tools content: {mcp._tools}")
print()

# Test 6: Create a non-decorated version for comparison
print("6. Testing non-decorated function:")
def regular_function(x: int, y: int) -> int:
    """Regular function without decorator"""
    return x + y

print(f"Regular function type: {type(regular_function)}")
print(f"Regular function callable? {callable(regular_function)}")

try:
    result = regular_function(5, 3)
    print(f"✅ Regular function call successful: {result}")
except Exception as e:
    print(f"❌ Regular function call failed: {e}")
print()

print("=== Investigation Complete ===")