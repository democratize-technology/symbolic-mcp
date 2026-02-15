"""Tests for OAuth authentication configuration.

This module verifies that the GitHub OAuth authentication is properly
configured when environment variables are set, and falls back to stdio
transport when they are not.
"""

import os

import pytest
from fastmcp import FastMCP

from main import _get_github_auth, mcp


class TestOAuthConfiguration:
    """Tests verifying GitHub OAuth authentication configuration."""

    def test_get_github_auth_returns_none_without_env_vars(self, monkeypatch) -> None:
        """Verify that _get_github_auth returns None when env vars not set."""
        # Ensure env vars are not set
        monkeypatch.delenv("GITHUB_CLIENT_ID", raising=False)
        monkeypatch.delenv("GITHUB_CLIENT_SECRET", raising=False)

        result = _get_github_auth()
        assert result is None, "Should return None when env vars not set"

    def test_get_github_auth_returns_provider_with_env_vars(self, monkeypatch) -> None:
        """Verify that _get_github_auth returns GitHubProvider when env vars set."""
        # Set env vars
        monkeypatch.setenv("GITHUB_CLIENT_ID", "test_client_id")
        monkeypatch.setenv("GITHUB_CLIENT_SECRET", "test_secret")

        result = _get_github_auth()
        assert result is not None, "Should return provider when env vars set"

        # Verify it's a GitHubProvider
        from fastmcp.server.auth.providers.github import GitHubProvider

        assert isinstance(result, GitHubProvider), "Should be GitHubProvider instance"

    def test_get_github_auth_returns_none_with_only_client_id(
        self, monkeypatch
    ) -> None:
        """Verify that _get_github_auth returns None when only client_id set."""
        monkeypatch.setenv("GITHUB_CLIENT_ID", "test_client_id")
        monkeypatch.delenv("GITHUB_CLIENT_SECRET", raising=False)

        result = _get_github_auth()
        assert result is None, "Should return None when only client_id set"

    def test_get_github_auth_returns_none_with_only_secret(self, monkeypatch) -> None:
        """Verify that _get_github_auth returns None when only secret set."""
        monkeypatch.delenv("GITHUB_CLIENT_ID", raising=False)
        monkeypatch.setenv("GITHUB_CLIENT_SECRET", "test_secret")

        result = _get_github_auth()
        assert result is None, "Should return None when only secret set"

    def test_server_configured_for_oauth(self, monkeypatch) -> None:
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

    def test_server_works_without_oauth(self, monkeypatch) -> None:
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
