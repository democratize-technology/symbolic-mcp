"""Tests for MCP Resources and Prompts.

This module verifies that MCP resources and prompts are properly
registered and accessible.
"""

from main import mcp


class TestResources:
    """Tests verifying MCP Resources."""

    def test_security_resource_registered(self) -> None:
        """Verify that config://security resource is registered."""
        assert "config://security" in mcp._resource_manager._resources

    def test_server_resource_registered(self) -> None:
        """Verify that config://server resource is registered."""
        assert "config://server" in mcp._resource_manager._resources

    def test_capabilities_resource_registered(self) -> None:
        """Verify that info://capabilities resource is registered."""
        assert "info://capabilities" in mcp._resource_manager._resources

    def test_total_resources_count(self) -> None:
        """Verify that expected number of resources are registered."""
        expected_resources = {
            "config://security",
            "config://server",
            "info://capabilities",
        }
        actual_resources = set(mcp._resource_manager._resources.keys())
        assert (
            actual_resources == expected_resources
        ), f"Expected {expected_resources}, got {actual_resources}"

    def test_security_resource_returns_dict(self) -> None:
        """Verify that security resource returns valid dict."""
        resource = mcp._resource_manager._resources["config://security"]
        assert callable(resource.fn), "Resource should be callable"
        result = resource.fn()
        assert isinstance(result, dict), "Security resource should return dict"
        assert "allowed_modules" in result
        assert "blocked_modules" in result
        assert "dangerous_builtins" in result

    def test_server_resource_returns_dict(self) -> None:
        """Verify that server resource returns valid dict."""
        resource = mcp._resource_manager._resources["config://server"]
        assert callable(resource.fn), "Resource should be callable"
        result = resource.fn()
        assert isinstance(result, dict), "Server resource should return dict"
        assert "version" in result
        assert "mask_error_details" in result
        assert "transport" in result

    def test_capabilities_resource_returns_dict(self) -> None:
        """Verify that capabilities resource returns valid dict."""
        resource = mcp._resource_manager._resources["info://capabilities"]
        assert callable(resource.fn), "Resource should be callable"
        result = resource.fn()
        assert isinstance(result, dict), "Capabilities resource should return dict"
        assert "tools" in result
        assert "resources" in result
        assert len(result["tools"]) == 5, "Should have 5 tools"


class TestPrompts:
    """Tests verifying MCP Prompts."""

    def test_symbolic_check_prompt_registered(self) -> None:
        """Verify that symbolic_check_template prompt is registered."""
        assert "symbolic_check_template" in mcp._prompt_manager._prompts

    def test_find_exception_path_prompt_registered(self) -> None:
        """Verify that find_exception_path_template prompt is registered."""
        assert "find_exception_path_template" in mcp._prompt_manager._prompts

    def test_compare_functions_prompt_registered(self) -> None:
        """Verify that compare_functions_template prompt is registered."""
        assert "compare_functions_template" in mcp._prompt_manager._prompts

    def test_analyze_branches_prompt_registered(self) -> None:
        """Verify that analyze_branches_template prompt is registered."""
        assert "analyze_branches_template" in mcp._prompt_manager._prompts

    def test_total_prompts_count(self) -> None:
        """Verify that expected number of prompts are registered."""
        expected_prompts = {
            "symbolic_check_template",
            "find_exception_path_template",
            "compare_functions_template",
            "analyze_branches_template",
        }
        actual_prompts = set(mcp._prompt_manager._prompts.keys())
        assert (
            actual_prompts == expected_prompts
        ), f"Expected {expected_prompts}, got {actual_prompts}"

    def test_prompt_returns_string(self) -> None:
        """Verify that prompts return strings."""
        for name in mcp._prompt_manager._prompts.keys():
            prompt = mcp._prompt_manager._prompts[name]
            assert callable(prompt.fn), f"Prompt {name} should be callable"
            result = prompt.fn()
            assert isinstance(result, str), f"Prompt {name} should return str"

    def test_prompt_contains_placeholders(self) -> None:
        """Verify that prompts contain expected placeholders."""
        prompt = mcp._prompt_manager._prompts["symbolic_check_template"]
        assert callable(prompt.fn), "Prompt should be callable"
        symbolic_check = prompt.fn()
        assert "{{code}}" in symbolic_check
        assert "{{function_name}}" in symbolic_check
