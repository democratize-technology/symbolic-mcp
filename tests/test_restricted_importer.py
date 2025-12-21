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


import sys
import pytest
from unittest.mock import patch

# Import the actual RestrictedImporter from main.py
from main import RestrictedImporter

@pytest.fixture(autouse=True)
def managed_importer():
    """Ensures the importer is installed for each test and uninstalled after."""
    RestrictedImporter.install()
    yield
    RestrictedImporter.uninstall()

def test_importer_blocks_disallowed_modules():
    """Verify that importing a module from the blocklist raises ImportError."""
    with pytest.raises(ImportError, match="Import of 'os' is blocked"):
        import os
    
    with pytest.raises(ImportError, match="Import of 'subprocess' is blocked"):
        import subprocess

def test_importer_does_not_interfere_with_allowed_modules():
    """Verify that allowed modules can be imported without interference."""
    try:
        import math
        import collections
        assert 'math' in sys.modules
        assert 'collections' in sys.modules
    except ImportError:
        pytest.fail("RestrictedImporter blocked an allowed module.")

def test_importer_does_not_interfere_with_standard_modules_not_in_lists():
    """Verify that modules not on any list are handled by the standard machinery."""
    try:
        import json
        assert 'json' in sys.modules
    except ImportError:
        pytest.fail("RestrictedImporter blocked a standard, unlisted module.")

def test_importer_handles_submodules_of_blocked_modules():
    """Verify that 'os.path' is blocked if 'os' is blocked."""
    with pytest.raises(ImportError, match="Import of 'os.path' is blocked"):
        __import__('os.path')

def test_install_and_uninstall():
    """Verify that install() and uninstall() correctly manipulate sys.meta_path."""
    # Uninstall first (the fixture already installed it)
    RestrictedImporter.uninstall()
    assert not any(isinstance(p, RestrictedImporter) for p in sys.meta_path)
    
    # Install
    RestrictedImporter.install()
    assert isinstance(sys.meta_path[0], RestrictedImporter)
    
    # Uninstall again
    RestrictedImporter.uninstall()
    assert not any(isinstance(p, RestrictedImporter) for p in sys.meta_path)

    # Test idempotency
    RestrictedImporter.uninstall() # should not raise error
    RestrictedImporter.install()
    RestrictedImporter.install() # should not add a duplicate
    assert len([p for p in sys.meta_path if isinstance(p, RestrictedImporter)]) == 1
