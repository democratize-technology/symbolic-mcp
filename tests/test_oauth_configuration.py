"""Tests for OAuth authentication configuration.

This module verifies that the GitHub OAuth authentication is properly
configured when environment variables are set, and falls back to stdio
transport when they are not.
"""

import pytest
from fastmcp import FastMCP
from pytest import MonkeyPatch

from main import _get_github_auth


class TestOAuthConfiguration:
    """Tests verifying GitHub OAuth authentication configuration."""

    @pytest.mark.parametrize(
        "client_id,client_secret,expected_result",
        [
            (None, None, None),
            ("test_id", "test_secret", "GitHubProvider"),
            ("test_id", None, None),
            (None, "test_secret", None),
        ],
        ids=["no_env_vars", "both_set", "only_client_id", "only_secret"],
    )
    def test_get_github_auth_env_combinations(
        self,
        client_id: str | None,
        client_secret: str | None,
        expected_result: str | None,
        monkeypatch: MonkeyPatch,
    ) -> None:
        """Verify _get_github_auth behavior with various env var combinations."""
        monkeypatch.delenv("GITHUB_CLIENT_ID", raising=False)
        monkeypatch.delenv("GITHUB_CLIENT_SECRET", raising=False)

        if client_id is not None:
            monkeypatch.setenv("GITHUB_CLIENT_ID", client_id)
        if client_secret is not None:
            monkeypatch.setenv("GITHUB_CLIENT_SECRET", client_secret)

        result = _get_github_auth()

        if expected_result is None:
            assert result is None
        else:
            assert result is not None
            from fastmcp.server.auth.providers.github import GitHubProvider

            assert isinstance(result, GitHubProvider)

    def test_server_configured_for_oauth(self, monkeypatch: MonkeyPatch) -> None:
        """Verify that FastMCP server accepts auth parameter."""
        # Set env vars for OAuth
        monkeypatch.setenv("GITHUB_CLIENT_ID", "test_client_id")
        monkeypatch.setenv("GITHUB_CLIENT_SECRET", "test_secret")

        # Import fresh to get OAuth configured
        # We can't reconfigure the existing mcp instance, so we test the function
        auth = _get_github_auth()
        assert auth is not None, "Auth should be configured"

        # Verify we can create a FastMCP server with auth
        test_server = FastMCP(
            "Test Server",
            auth=auth,
            mask_error_details=True,
        )
        assert test_server is not None
        assert test_server.name == "Test Server"

    def test_server_works_without_oauth(self, monkeypatch: MonkeyPatch) -> None:
        """Verify that FastMCP server works without auth (stdio)."""
        # Ensure env vars are not set
        monkeypatch.delenv("GITHUB_CLIENT_ID", raising=False)
        monkeypatch.delenv("GITHUB_CLIENT_SECRET", raising=False)

        auth = _get_github_auth()
        assert auth is None, "Auth should be None for stdio"

        # Verify server works without auth
        test_server = FastMCP(
            "Test Server",
            auth=auth,
            mask_error_details=True,
        )
        assert test_server is not None
        assert test_server.name == "Test Server"
