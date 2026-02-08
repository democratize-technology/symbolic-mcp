"""Tests for FastMCP security configuration.

This module verifies that the FastMCP server is configured with security best
practices, particularly that error details are masked to prevent internal
implementation details from leaking to clients.
"""

import sys

import pytest
from fastmcp import FastMCP

# Import the main module to access the configured mcp instance
if __name__ == "__main__":
    # When run as a script, add the parent directory to the path
    sys.path.insert(0, "/Users/eringreen/Development/symbolic-mcp")
    from main import mcp
else:
    from main import mcp


class TestFastMCPSecurityConfiguration:
    """Tests verifying FastMCP server security configuration."""

    def test_mask_error_details_enabled_on_tool_manager(self) -> None:
        """Verify that mask_error_details is enabled on the FastMCP server.

        Without mask_error_details=True, unhandled exceptions expose full
        Python stack traces to MCP clients, leaking:
        - Internal file paths
        - Library versions
        - Implementation details
        - Potentially sensitive information

        This test verifies the production security best practice is enabled.

        Note: FastMCP stores mask_error_details on the _tool_manager,
        _resource_manager, and _prompt_manager objects, not on the main instance.
        """
        # FastMCP stores mask_error_details on the tool manager
        assert hasattr(
            mcp, "_tool_manager"
        ), "FastMCP instance should have _tool_manager attribute"

        assert hasattr(
            mcp._tool_manager, "mask_error_details"
        ), "ToolManager should have mask_error_details attribute"

        # Verify it's set to True for production security
        assert (
            mcp._tool_manager.mask_error_details is True
        ), "mask_error_details should be True for production security"

    def test_mask_error_details_enabled_on_resource_manager(self) -> None:
        """Verify that mask_error_details is also enabled on the resource manager.

        Resources also need error masking to prevent information leakage.
        """
        assert hasattr(
            mcp, "_resource_manager"
        ), "FastMCP instance should have _resource_manager attribute"

        assert hasattr(
            mcp._resource_manager, "mask_error_details"
        ), "ResourceManager should have mask_error_details attribute"

        assert (
            mcp._resource_manager.mask_error_details is True
        ), "ResourceManager mask_error_details should be True"

    def test_mask_error_details_enabled_on_prompt_manager(self) -> None:
        """Verify that mask_error_details is also enabled on the prompt manager.

        Prompts also need error masking to prevent information leakage.
        """
        assert hasattr(
            mcp, "_prompt_manager"
        ), "FastMCP instance should have _prompt_manager attribute"

        assert hasattr(
            mcp._prompt_manager, "mask_error_details"
        ), "PromptManager should have mask_error_details attribute"

        assert (
            mcp._prompt_manager.mask_error_details is True
        ), "PromptManager mask_error_details should be True"

    def test_server_name_is_set(self) -> None:
        """Verify that the server has a proper name set.

        A named server is important for:
        - Client identification
        - Logging/debugging clarity
        - Multiple server instance management
        """
        assert hasattr(mcp, "name"), "FastMCP instance should have name attribute"
        assert mcp.name == "Symbolic Execution Server"

    def test_lifespan_configured(self) -> None:
        """Verify that the server has a lifespan context manager configured.

        The lifespan handler ensures proper cleanup of resources like
        temporary modules, preventing memory leaks in long-running processes.
        """
        assert hasattr(mcp, "_lifespan"), "FastMCP instance should have _lifespan attribute"
        assert mcp._lifespan is not None, "lifespan should be configured for cleanup"

    def test_tools_are_registered(self) -> None:
        """Verify that expected tools are registered on the server.

        This ensures the server was properly initialized with all expected
        functionality.
        """
        # FastMCP uses the tool_manager._tools dict to store tools
        # Keys are tool names, values are Tool objects
        tool_names = set(mcp._tool_manager._tools.keys())

        expected_tools = {
            "symbolic_check",
            "find_path_to_exception",
            "compare_functions",
            "analyze_branches",
            "health_check",
        }

        missing_tools = expected_tools - tool_names
        assert not missing_tools, f"Missing expected tools: {missing_tools}"


class TestErrorMaskingBehavior:
    """Tests verifying actual error masking behavior when tools fail."""

    def test_mask_error_details_is_passed_to_managers(self) -> None:
        """Verify that mask_error_details is properly passed to all managers."""
        # Create a test server with mask_error_details=True
        test_server = FastMCP("Test Server", mask_error_details=True)

        assert test_server._tool_manager.mask_error_details is True
        assert test_server._resource_manager.mask_error_details is True
        assert test_server._prompt_manager.mask_error_details is True

    def test_mask_error_details_false_is_honored(self) -> None:
        """Verify that mask_error_details=False is properly applied."""
        # Create a test server WITHOUT mask_error_details
        test_server = FastMCP("Test Server", mask_error_details=False)

        assert test_server._tool_manager.mask_error_details is False
        assert test_server._resource_manager.mask_error_details is False
        assert test_server._prompt_manager.mask_error_details is False

    def test_default_mask_error_details_is_false(self) -> None:
        """Verify that default behavior has masking disabled (unsafe for production).

        This documents the default behavior - when mask_error_details is not
        explicitly set, it defaults to False, which is why we must explicitly
        enable it in production.
        """
        # Create a test server without specifying mask_error_details
        test_server = FastMCP("Test Server")

        # Default should be False (documenting this unsafe default)
        assert test_server._tool_manager.mask_error_details is False


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v"])
