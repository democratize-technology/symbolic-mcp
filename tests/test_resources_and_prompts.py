"""Tests for MCP Resources and Prompts.

This module verifies that MCP resources and prompts are properly
registered and accessible.
"""

from main import mcp


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
        actual_resources = set(mcp._resource_manager._resources.keys())
        assert (
            actual_resources == expected_resources
        ), f"Expected {expected_resources}, got {actual_resources}"

    def test_security_resource_returns_correct_values(self) -> None:
        """Verify that security resource returns correct values.

        Given: The security resource is registered
        When: The resource function is called
        Then: It returns a dict with correct allowed/blocked modules
        """
        resource = mcp._resource_manager._resources["config://security"]
        assert callable(resource.fn), "Resource should be callable"  # type: ignore[attr-defined]
        result = resource.fn()  # type: ignore[attr-defined]

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
        resource = mcp._resource_manager._resources["config://server"]
        assert callable(resource.fn), "Resource should be callable"  # type: ignore[attr-defined]
        result = resource.fn()  # type: ignore[attr-defined]

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
        resource = mcp._resource_manager._resources["info://capabilities"]
        assert callable(resource.fn), "Resource should be callable"  # type: ignore[attr-defined]
        result = resource.fn()  # type: ignore[attr-defined]

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
        actual_prompts = set(mcp._prompt_manager._prompts.keys())
        assert (
            actual_prompts == expected_prompts
        ), f"Expected {expected_prompts}, got {actual_prompts}"

    def test_prompts_return_strings(self) -> None:
        """Verify that all prompts return strings.

        Given: Prompts are registered
        When: Each prompt function is called
        Then: It returns a string
        """
        for name in mcp._prompt_manager._prompts.keys():
            prompt = mcp._prompt_manager._prompts[name]
            assert callable(prompt.fn), f"Prompt {name} should be callable"  # type: ignore[attr-defined]
            result = prompt.fn()  # type: ignore[attr-defined]
            assert isinstance(result, str), f"Prompt {name} should return str"

    def test_prompt_contains_placeholders(self) -> None:
        """Verify that prompts contain expected placeholders.

        Given: The symbolic_check_template prompt is registered
        When: The prompt function is called
        Then: It contains {{code}} and {{function_name}} placeholders
        """
        prompt = mcp._prompt_manager._prompts["symbolic_check_template"]
        assert callable(prompt.fn), "Prompt should be callable"  # type: ignore[attr-defined]
        symbolic_check = prompt.fn()  # type: ignore[attr-defined]
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
            prompt = mcp._prompt_manager._prompts[prompt_name]
            result = prompt.fn()  # type: ignore[attr-defined]
            for placeholder in required_placeholders:
                assert (
                    placeholder in result
                ), f"Prompt {prompt_name} should contain {placeholder}"
