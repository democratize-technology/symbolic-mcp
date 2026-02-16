"""Tests for FastMCP security configuration.

This module verifies that the FastMCP server is configured with security best
practices, particularly that error details are masked to prevent internal
implementation details from leaking to clients.
"""

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
