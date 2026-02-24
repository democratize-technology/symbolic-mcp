"""Tests for MCP Resources and Prompts.

This module verifies that MCP resources and prompts are properly
registered and accessible.
"""

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from symbolic_mcp import mcp

# --- Type-safe helpers for FastMCP internal access ---


@runtime_checkable
class _HasCallableFn(Protocol):
    """Protocol for objects with a callable fn attribute.

    FastMCP's FunctionResource and FunctionPrompt have a 'fn' attribute
    that holds the underlying callable, but this isn't exposed in their
    type stubs. This protocol provides type-safe access for tests.
    """

    fn: Callable[..., Any]


def _get_mcp_resource_fn(mcp_instance: Any, uri: str) -> Callable[..., Any]:
    """Type-safe accessor for MCP resource function."""
    resource = mcp_instance._resource_manager._resources.get(uri)
    assert resource is not None, f"Resource {uri} not found"
    assert isinstance(
        resource, _HasCallableFn
    ), f"Resource {uri} should have fn attribute"
    return resource.fn


def _get_mcp_prompt_fn(mcp_instance: Any, name: str) -> Callable[..., Any]:
    """Type-safe accessor for MCP prompt function."""
    prompt = mcp_instance._prompt_manager._prompts.get(name)
    assert prompt is not None, f"Prompt {name} not found"
    assert isinstance(prompt, _HasCallableFn), f"Prompt {name} should have fn attribute"
    return prompt.fn


class TestResources:
    """Tests verifying MCP Resources."""

    def test_expected_resources_registered(self) -> None:
        """Verify that all expected resources are registered.

        Given: The MCP server is initialized
        When: Resources are queried
        Then: All expected resources are present
        """
        expected_resources = {
            "config://security",
            "config://server",
            "info://capabilities",
        }
        actual_resources = set(mcp._resource_manager._resources.keys())  # type: ignore[attr-defined]
        assert (
            actual_resources == expected_resources
        ), f"Expected {expected_resources}, got {actual_resources}"

    def test_security_resource_returns_correct_values(self) -> None:
        """Verify that security resource returns correct values.

        Given: The security resource is registered
        When: The resource function is called
        Then: It returns a dict with correct allowed/blocked modules
        """
        resource_fn = _get_mcp_resource_fn(mcp, "config://security")
        result = resource_fn()

        assert isinstance(result, dict), "Security resource should return dict"
        assert "allowed_modules" in result
        assert "blocked_modules" in result
        assert "dangerous_builtins" in result

        # Verify specific values
        assert "math" in result["allowed_modules"], "math should be allowed"
        assert "os" in result["blocked_modules"], "os should be blocked"
        assert "eval" in result["dangerous_builtins"], "eval should be dangerous"
        assert "exec" in result["dangerous_builtins"], "exec should be dangerous"

    def test_server_resource_returns_correct_values(self) -> None:
        """Verify that server resource returns correct values.

        Given: The server resource is registered
        When: The resource function is called
        Then: It returns a dict with server configuration
        """
        resource_fn = _get_mcp_resource_fn(mcp, "config://server")
        result = resource_fn()

        assert isinstance(result, dict), "Server resource should return dict"
        assert "version" in result
        assert "mask_error_details" in result
        assert "transport" in result

        # Verify types of values
        assert isinstance(result["version"], str), "version should be string"
        assert isinstance(
            result["mask_error_details"], bool
        ), "mask_error_details should be bool"
        assert isinstance(result["transport"], str), "transport should be string"

    def test_capabilities_resource_returns_correct_values(self) -> None:
        """Verify that capabilities resource returns correct values.

        Given: The capabilities resource is registered
        When: The resource function is called
        Then: It returns a dict with correct tool and resource counts
        """
        resource_fn = _get_mcp_resource_fn(mcp, "info://capabilities")
        result = resource_fn()

        assert isinstance(result, dict), "Capabilities resource should return dict"
        assert "tools" in result
        assert "resources" in result
        assert len(result["tools"]) == 5, "Should have 5 tools"

        # Verify tool names are present
        tool_names = {tool["name"] for tool in result["tools"]}
        expected_tools = {
            "symbolic_check",
            "find_path_to_exception",
            "compare_functions",
            "analyze_branches",
            "health_check",
        }
        assert (
            tool_names == expected_tools
        ), f"Expected tools {expected_tools}, got {tool_names}"


class TestPrompts:
    """Tests verifying MCP Prompts."""

    def test_expected_prompts_registered(self) -> None:
        """Verify that all expected prompts are registered.

        Given: The MCP server is initialized
        When: Prompts are queried
        Then: All expected prompts are present
        """
        expected_prompts = {
            "symbolic_check_template",
            "find_exception_path_template",
            "compare_functions_template",
            "analyze_branches_template",
        }
        actual_prompts = set(mcp._prompt_manager._prompts.keys())  # type: ignore[attr-defined]
        assert (
            actual_prompts == expected_prompts
        ), f"Expected {expected_prompts}, got {actual_prompts}"

    def test_prompts_return_strings(self) -> None:
        """Verify that all prompts return strings.

        Given: Prompts are registered
        When: Each prompt function is called
        Then: It returns a string
        """
        for name in mcp._prompt_manager._prompts.keys():  # type: ignore[attr-defined]
            prompt_fn = _get_mcp_prompt_fn(mcp, name)
            result = prompt_fn()
            assert isinstance(result, str), f"Prompt {name} should return str"

    def test_prompt_contains_placeholders(self) -> None:
        """Verify that prompts contain expected placeholders.

        Given: The symbolic_check_template prompt is registered
        When: The prompt function is called
        Then: It contains {{code}} and {{function_name}} placeholders
        """
        prompt_fn = _get_mcp_prompt_fn(mcp, "symbolic_check_template")
        symbolic_check = prompt_fn()
        assert "{{code}}" in symbolic_check
        assert "{{function_name}}" in symbolic_check

    def test_all_prompts_have_required_placeholders(self) -> None:
        """Verify all prompts have their required placeholders.

        Given: All prompts are registered
        When: Each prompt is retrieved
        Then: Each contains its specific required placeholders
        """
        prompt_requirements = {
            "symbolic_check_template": ["{{code}}", "{{function_name}}"],
            "find_exception_path_template": [
                "{{code}}",
                "{{function_name}}",
                "{{exception_type}}",
            ],
            "compare_functions_template": [
                "{{code}}",
                "{{function_a}}",
                "{{function_b}}",
            ],
            "analyze_branches_template": ["{{code}}", "{{function_name}}"],
        }

        for prompt_name, required_placeholders in prompt_requirements.items():
            prompt_fn = _get_mcp_prompt_fn(mcp, prompt_name)
            result = prompt_fn()
            for placeholder in required_placeholders:
                assert (
                    placeholder in result
                ), f"Prompt {prompt_name} should contain {placeholder}"
