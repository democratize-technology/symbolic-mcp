"""Tests for FastMCP security configuration.

This module verifies that the FastMCP server is configured with security best
practices, particularly that error details are masked to prevent internal
implementation details from leaking to clients.
"""

import pytest

from main import mcp


class TestFastMCPSecurityConfiguration:
    """Tests verifying FastMCP server security configuration."""

    @pytest.mark.parametrize(
        "manager_attr",
        ["_tool_manager", "_resource_manager", "_prompt_manager"],
    )
    def test_mask_error_details_enabled(self, manager_attr: str) -> None:
        """Verify that mask_error_details is enabled on all managers.

        Without mask_error_details=True, unhandled exceptions expose full
        Python stack traces to MCP clients, leaking:
        - Internal file paths
        - Library versions
        - Implementation details
        - Potentially sensitive information
        """
        assert hasattr(
            mcp, manager_attr
        ), f"FastMCP instance should have {manager_attr} attribute"

        manager = getattr(mcp, manager_attr)
        assert hasattr(
            manager, "mask_error_details"
        ), f"{manager_attr} should have mask_error_details attribute"

        assert (
            manager.mask_error_details is True
        ), f"{manager_attr} mask_error_details should be True for production security"

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
        assert hasattr(
            mcp, "_lifespan"
        ), "FastMCP instance should have _lifespan attribute"
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
