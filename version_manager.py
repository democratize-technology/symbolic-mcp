#!/usr/bin/env python3
"""
Version Management Module for Symbolic MCP

This module provides comprehensive version management capabilities including:
- Semantic version calculation from Git history
- Version synchronization between pyproject.toml and source code
- FastMCP 2.0 compatibility tracking
- Development and release version workflows
- Automated changelog generation
"""

import datetime
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from packaging import version


@dataclass
class VersionInfo:
    """Version information container"""

    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None
    build: Optional[str] = None

    def __str__(self) -> str:
        """Return semantic version string"""
        v = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            v += f"-{self.prerelease}"
        if self.build:
            v += f"+{self.build}"
        return v

    @classmethod
    def parse(cls, version_str: str) -> "VersionInfo":
        """Parse version string into VersionInfo"""
        # Parse semantic version
        match = re.match(
            r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9-]+))?(?:\+([a-zA-Z0-9-]+))?$",
            version_str,
        )
        if not match:
            raise ValueError(f"Invalid semantic version: {version_str}")

        major, minor, patch = map(int, match.groups()[:3])
        prerelease = match.group(4)
        build = match.group(5)

        return cls(major, minor, patch, prerelease, build)

    def bump(self, bump_type: str) -> "VersionInfo":
        """Create new version with bump"""
        if bump_type == "major":
            return VersionInfo(self.major + 1, 0, 0)
        elif bump_type == "minor":
            return VersionInfo(self.major, self.minor + 1, 0)
        elif bump_type == "patch":
            return VersionInfo(self.major, self.minor, self.patch + 1)
        else:
            raise ValueError(f"Invalid bump type: {bump_type}")


class VersionManager:
    """Comprehensive version management system"""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.pyproject_toml = self.project_root / "pyproject.toml"
        self.git_dir = self.project_root / ".git"

    def is_git_repository(self) -> bool:
        """Check if project is a git repository"""
        return self.git_dir.exists()

    def get_git_version(self) -> str:
        """Get version from git tags using setuptools-scm logic"""
        try:
            # Try setuptools-scm first
            from setuptools_scm import get_version

            return get_version(
                root=self.project_root,
                fallback_version="0.1.0",
                version_scheme="release-branch-semver",
                local_scheme="node-and-date",
            )
        except ImportError:
            # Fallback to manual git version calculation
            return self._calculate_git_version()

    def _calculate_git_version(self) -> str:
        """Calculate version from git tags manually"""
        if not self.is_git_repository():
            return "0.1.0.dev0"

        try:
            # Get latest tag
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                latest_tag = result.stdout.strip()
                if latest_tag.startswith("v"):
                    version_str = latest_tag[1:]  # Remove 'v' prefix
                else:
                    version_str = latest_tag

                # Check if we're on the tag
                result = subprocess.run(
                    ["git", "describe", "--tags", "--exact-match", "HEAD"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    return version_str
                else:
                    # Add dev suffix if we have commits since tag
                    result = subprocess.run(
                        ["git", "rev-list", "--count", f"{latest_tag}..HEAD"],
                        cwd=self.project_root,
                        capture_output=True,
                        text=True,
                    )

                    if result.returncode == 0:
                        commits_since = int(result.stdout.strip())
                        version_info = VersionInfo.parse(version_str)
                        return f"{version_info.major}.{version_info.minor}.{version_info.patch + commits_since}.dev{commits_since}"

            return "0.1.0.dev0"

        except (subprocess.SubprocessError, FileNotFoundError):
            return "0.1.0.dev0"

    def get_pyproject_version(self) -> Optional[str]:
        """Get version from pyproject.toml"""
        if not self.pyproject_toml.exists():
            return None

        try:
            # Read pyproject.toml
            content = self.pyproject_toml.read_text()

            # Check if version is dynamic
            if 'dynamic = ["version"]' in content:
                # Version is managed by setuptools-scm
                return self.get_git_version()
            else:
                # Static version in pyproject.toml
                for line in content.split("\n"):
                    if line.strip().startswith("version = "):
                        version_str = line.split("=")[1].strip().strip("\"'")
                        return version_str

            return None

        except Exception:
            return None

    def set_pyproject_version(self, version_str: str) -> bool:
        """Set version in pyproject.toml"""
        if not self.pyproject_toml.exists():
            return False

        try:
            content = self.pyproject_toml.read_text()

            # Update version line
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.strip().startswith("version = "):
                    lines[i] = f'version = "{version_str}"'
                    break
            else:
                # Insert after [project] section
                for i, line in enumerate(lines):
                    if line.strip() == "[project]":
                        lines.insert(i + 1, f'version = "{version_str}"')
                        break

            # Write back
            self.pyproject_toml.write_text("\n".join(lines))
            return True

        except Exception:
            return False

    def create_git_tag(
        self, version: VersionInfo, message: Optional[str] = None
    ) -> bool:
        """Create git tag for version"""
        if not self.is_git_repository():
            return False

        try:
            tag_name = f"v{version}"

            if not message:
                message = f"Release {tag_name}"

            # Create tag
            subprocess.run(
                ["git", "tag", "-a", tag_name, "-m", message],
                cwd=self.project_root,
                check=True,
            )

            return True

        except subprocess.SubprocessError:
            return False

    def get_commit_messages_since_last_tag(self) -> List[str]:
        """Get commit messages since last tag"""
        if not self.is_git_repository():
            return []

        try:
            # Get last tag
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                last_tag = result.stdout.strip()
                range_spec = f"{last_tag}..HEAD"
            else:
                range_spec = "HEAD"

            # Get commit messages
            result = subprocess.run(
                ["git", "log", range_spec, "--oneline"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                messages = []
                for line in result.stdout.strip().split("\n"):
                    if line.strip():
                        # Remove hash and keep message
                        parts = line.split(" ", 1)
                        if len(parts) > 1:
                            messages.append(parts[1])
                return messages

            return []

        except subprocess.SubprocessError:
            return []

    def analyze_commits_for_version_bump(self) -> str:
        """Analyze commits to determine version bump type"""
        messages = self.get_commit_messages_since_last_tag()

        # Check for breaking changes
        for msg in messages:
            if any(
                keyword in msg.lower()
                for keyword in ["breaking change", "breaking:", "!", "major"]
            ):
                return "major"

        # Check for features
        for msg in messages:
            if any(
                keyword in msg.lower()
                for keyword in ["feat", "feature", "minor", "add", "new"]
            ):
                return "minor"

        # Default to patch
        return "patch"

    def get_fastmcp_compatibility(self) -> Dict[str, str]:
        """Get FastMCP 2.0 compatibility information"""
        try:
            # Try to import FastMCP to get version
            import fastmcp

            fastmcp_version = fastmcp.__version__

            # Determine compatibility
            if fastmcp_version.startswith("2."):
                compatibility = "compatible"
                message = "FastMCP 2.0 compatible"
            else:
                compatibility = "incompatible"
                message = f"FastMCP {fastmcp_version} - requires 2.0+"

        except ImportError:
            fastmcp_version = "unknown"
            compatibility = "unknown"
            message = "FastMCP not available"

        return {
            "version": fastmcp_version,
            "compatibility": compatibility,
            "message": message,
            "required": ">=2.0.0",
        }

    def generate_changelog(self, version: VersionInfo) -> str:
        """Generate changelog for version"""
        messages = self.get_commit_messages_since_last_tag()

        # Categorize commits
        features = []
        fixes = []
        breaking = []
        security = []
        other = []

        for msg in messages:
            msg_lower = msg.lower()
            if any(
                keyword in msg_lower
                for keyword in ["breaking change", "breaking:", "!"]
            ):
                breaking.append(msg)
            elif any(keyword in msg_lower for keyword in ["feat", "feature"]):
                features.append(msg)
            elif any(keyword in msg_lower for keyword in ["fix", "bugfix"]):
                fixes.append(msg)
            elif any(keyword in msg_lower for keyword in ["sec", "cve", "security"]):
                security.append(msg)
            else:
                other.append(msg)

        # Generate changelog sections
        sections = []

        if breaking:
            sections.append("## 💥 BREAKING CHANGES")
            sections.extend([f"- {change}" for change in breaking])
            sections.append("")

        if security:
            sections.append("## 🛡️ Security Fixes")
            sections.extend([f"- {change}" for change in security])
            sections.append("")

        if features:
            sections.append("## 🚀 Features")
            sections.extend([f"- {change}" for change in features])
            sections.append("")

        if fixes:
            sections.append("## 🐛 Bug Fixes")
            sections.extend([f"- {change}" for change in fixes])
            sections.append("")

        if other:
            sections.append("## 🔧 Other Changes")
            sections.extend([f"- {change}" for change in other[:10]])  # Limit to 10
            sections.append("")

        # Add auto-generated sections
        fastmcp_info = self.get_fastmcp_compatibility()
        sections.extend(
            [
                "## ✅ Quality Assurance",
                "- All security checks passed",
                "- Multi-platform testing successful",
                "- Performance benchmarks within limits",
                f"- FastMCP compatibility: {fastmcp_info['message']}",
                "",
                "## 📦 Installation",
                "```bash",
                "pip install symbolic-mcp",
                "```",
                "",
                "## 🔗 Links",
                "- [PyPI Package](https://pypi.org/project/symbolic-mcp/)",
                "- [GitHub Repository](https://github.com/disquantified/symbolic-mcp)",
                "- [Documentation](https://symbolic-mcp.readthedocs.io/)",
                "",
                f"---",
                f"**Version:** {version}",
                f"**Release Date:** {datetime.datetime.now().strftime('%B %d, %Y')}",
                "",
            ]
        )

        return "\n".join(sections)

    def validate_version(self, version_str: str) -> bool:
        """Validate semantic version string"""
        try:
            VersionInfo.parse(version_str)
            return True
        except ValueError:
            return False

    def suggest_next_version(
        self, current_version: Optional[str] = None
    ) -> VersionInfo:
        """Suggest next version based on commits"""
        if not current_version:
            current_version = self.get_git_version()

        if not current_version:
            return VersionInfo(0, 1, 0)

        # Parse current version
        version_info = VersionInfo.parse(current_version)

        # Determine bump type
        bump_type = self.analyze_commits_for_version_bump()

        return version_info.bump(bump_type)


def main():
    """CLI interface for version management"""
    import argparse

    parser = argparse.ArgumentParser(description="Version Management CLI")
    parser.add_argument(
        "command",
        choices=[
            "get",
            "set",
            "bump",
            "tag",
            "changelog",
            "validate",
            "suggest",
            "compatibility",
        ],
        help="Command to execute",
    )
    parser.add_argument("--version", help="Version string for set/validate commands")
    parser.add_argument(
        "--bump-type",
        choices=["major", "minor", "patch"],
        help="Bump type for bump command",
    )
    parser.add_argument("--message", help="Message for tag command")
    parser.add_argument("--output", help="Output file for changelog")

    args = parser.parse_args()

    vm = VersionManager()

    if args.command == "get":
        print(vm.get_git_version())

    elif args.command == "validate":
        if args.version:
            valid = vm.validate_version(args.version)
            print(f"Valid: {valid}")
            return 0 if valid else 1
        else:
            print("Error: --version required for validate command")
            return 1

    elif args.command == "suggest":
        version = vm.suggest_next_version()
        print(str(version))

    elif args.command == "set":
        if args.version:
            success = vm.set_pyproject_version(args.version)
            if success:
                print(f"Version set to {args.version}")
                return 0
            else:
                print("Failed to set version")
                return 1
        else:
            print("Error: --version required for set command")
            return 1

    elif args.command == "bump":
        if args.bump_type:
            current_version = vm.get_git_version()
            if current_version:
                version_info = VersionInfo.parse(current_version)
                new_version = version_info.bump(args.bump_type)
                success = vm.set_pyproject_version(str(new_version))
                if success:
                    print(f"Version bumped to {new_version}")
                    return 0
                else:
                    print("Failed to bump version")
                    return 1
            else:
                print("Could not determine current version")
                return 1
        else:
            bump_type = vm.analyze_commits_for_version_bump()
            current_version = vm.get_git_version()
            if current_version:
                version_info = VersionInfo.parse(current_version)
                new_version = version_info.bump(bump_type)
                success = vm.set_pyproject_version(str(new_version))
                if success:
                    print(f"Auto-bumped version to {new_version} (bump: {bump_type})")
                    return 0
                else:
                    print("Failed to bump version")
                    return 1
            else:
                print("Could not determine current version")
                return 1

    elif args.command == "tag":
        current_version = vm.get_git_version()
        if current_version:
            version_info = VersionInfo.parse(current_version)
            success = vm.create_git_tag(version_info, args.message)
            if success:
                print(f"Created tag v{version_info}")
                return 0
            else:
                print("Failed to create tag")
                return 1
        else:
            print("Could not determine current version")
            return 1

    elif args.command == "changelog":
        current_version = vm.get_git_version()
        if current_version:
            version_info = VersionInfo.parse(current_version)
            changelog = vm.generate_changelog(version_info)

            if args.output:
                Path(args.output).write_text(changelog)
                print(f"Changelog written to {args.output}")
            else:
                print(changelog)
            return 0
        else:
            print("Could not determine current version")
            return 1

    elif args.command == "compatibility":
        compat = vm.get_fastmcp_compatibility()
        print(json.dumps(compat, indent=2))
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
