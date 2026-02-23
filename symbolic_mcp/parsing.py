# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Symbolic MCP Contributors

"""Parsing utilities for symbolic execution.

This module contains pre-compiled regex patterns and parsing functions
for extracting information from CrossHair analysis messages.
"""

import re

# Pattern for parsing function call messages from CrossHair
_CALL_PATTERN = re.compile(r"calling\s+(\w+)\((.*?)\)(?:\s*\(which|\s*$)")

# Pattern for extracting result values from messages
_RESULT_PATTERN = re.compile(r"which returns\s+(.+)\)$")

# Pattern for extracting exception type from error messages
_EXC_PATTERN = re.compile(r"^(\w+(?:\s+\w+)*)?:")


def _parse_function_args(args_str: str) -> list[str]:
    """Parse function arguments from a string, handling nested expressions.

    This parser properly handles:
    - Simple args: "x, y, z" -> ["x", "y", "z"]
    - Nested calls: "f(x), g(y)" -> ["f(x)", "g(y)"]
    - Complex expressions: "float('nan'), 1" -> ["float('nan')", "1"]
    - Empty strings: "" -> []

    Args:
        args_str: String containing comma-separated arguments

    Returns:
        List of parsed argument strings
    """
    args_str = args_str.strip()
    if not args_str:
        return []

    result = []
    current = []
    paren_depth = 0
    bracket_depth = 0
    brace_depth = 0
    in_string = False
    string_char = None

    i = 0
    while i < len(args_str):
        char = args_str[i]

        # Handle string literals
        if char in ('"', "'"):
            # Check if quote is escaped by odd number of backslashes
            is_escaped = False
            j = i - 1
            while j >= 0 and args_str[j] == "\\":
                is_escaped = not is_escaped
                j -= 1

            if not is_escaped:
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
                    string_char = None
            current.append(char)
        # Inside string, just append
        elif in_string:
            current.append(char)
        # Handle nested structures
        elif char == "(":
            paren_depth += 1
            current.append(char)
        elif char == ")":
            paren_depth -= 1
            current.append(char)
        elif char == "[":
            bracket_depth += 1
            current.append(char)
        elif char == "]":
            bracket_depth -= 1
            current.append(char)
        elif char == "{":
            brace_depth += 1
            current.append(char)
        elif char == "}":
            brace_depth -= 1
            current.append(char)
        # Handle comma separator (only when not in nested structure)
        elif (
            char == "," and paren_depth == 0 and bracket_depth == 0 and brace_depth == 0
        ):
            arg = "".join(current).strip()
            if arg:
                result.append(arg)
            current = []
        # Skip whitespace only when not in a nested structure
        elif (
            char.isspace()
            and paren_depth == 0
            and bracket_depth == 0
            and brace_depth == 0
            and not current
        ):
            pass  # Skip leading whitespace
        else:
            current.append(char)

        i += 1

    # Add the last argument
    arg = "".join(current).strip()
    if arg:
        result.append(arg)

    return result


__all__ = [
    "_CALL_PATTERN",
    "_RESULT_PATTERN",
    "_EXC_PATTERN",
    "_parse_function_args",
]
