# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Symbolic MCP Contributors

"""Configuration and constants for symbolic execution server.

This module contains environment variable handling, memory management,
and all configurable constants used throughout the server.
"""

import os
import resource
import threading

# Default timeout for CrossHair analysis in seconds
DEFAULT_ANALYSIS_TIMEOUT_SECONDS = 30


def _get_int_env_var(
    name: str,
    default: str,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int:
    """Safely parse an integer environment variable with optional bounds checking.

    Args:
        name: Environment variable name
        default: Default value as string
        min_value: Minimum allowed value (inclusive), or None for no minimum
        max_value: Maximum allowed value (inclusive), or None for no maximum

    Returns:
        Parsed integer value, or default if invalid

    Raises:
        ValueError: If the value is outside the allowed bounds
    """
    try:
        value = int(os.environ.get(name, default))
    except (ValueError, TypeError):
        value = int(default)

    if min_value is not None and value < min_value:
        raise ValueError(f"{name} must be at least {min_value}, got {value}")
    if max_value is not None and value > max_value:
        raise ValueError(f"{name} must be at most {max_value}, got {value}")

    return value


# Memory limit in MB for symbolic execution (configurable via environment)
# Min: 128MB, Max: 65536MB (64GB)
MEMORY_LIMIT_MB = _get_int_env_var(
    "SYMBOLIC_MEMORY_LIMIT_MB", "2048", min_value=128, max_value=65536
)

# Code size limit in bytes (configurable via environment)
# Min: 1024 bytes (1KB), Max: 1048576 bytes (1MB)
CODE_SIZE_LIMIT = _get_int_env_var(
    "SYMBOLIC_CODE_SIZE_LIMIT", "65536", min_value=1024, max_value=1048576
)

# Coverage calculation thresholds (configurable via environment)
# Min: 100, Max: 100000
# High confidence threshold: below this count, coverage is considered exhaustive
COVERAGE_EXHAUSTIVE_THRESHOLD = _get_int_env_var(
    "SYMBOLIC_COVERAGE_EXHAUSTIVE_THRESHOLD", "1000", min_value=100, max_value=100000
)

# Coverage degradation factor for logarithmic scaling (see coverage calculation below)
# Derived from: 1.0 - desired_min_coverage
# At max_scale_factor (100): coverage = 1.0 - log(100)/log(100) * 0.23 = 0.77
# This ensures even very large path counts get meaningful (non-zero) coverage estimates
COVERAGE_DEGRADATION_FACTOR = 0.23

# Maximum scale factor for coverage calculation
# At 100x the exhaustive threshold, coverage drops to ~0.77
MAX_COVERAGE_SCALE_FACTOR = 100

# Per-path timeout ratio for CrossHair analysis
# Each path's timeout is this fraction of the total timeout
# A lower value gives more paths a chance to complete before hitting the overall timeout
PER_PATH_TIMEOUT_RATIO = 0.1  # 10% of total timeout per path

# Module-level lock for sys.modules access.
# Protects against race conditions when multiple threads concurrently
# create/delete temporary modules. Without this lock, check-then-act
# patterns like "if key in dict: del dict[key]" can cause KeyError
# when another thread modifies the dict between check and act.
_SYS_MODULES_LOCK = threading.Lock()


def set_memory_limit(limit_mb: int) -> None:
    """Set memory limit for the process to prevent resource exhaustion.

    Args:
        limit_mb: Memory limit in megabytes
    """
    try:
        limit_bytes = limit_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, -1))
    except (ValueError, ImportError):
        pass


# Set memory limit on module import
set_memory_limit(MEMORY_LIMIT_MB)


__all__ = [
    "DEFAULT_ANALYSIS_TIMEOUT_SECONDS",
    "MEMORY_LIMIT_MB",
    "CODE_SIZE_LIMIT",
    "COVERAGE_EXHAUSTIVE_THRESHOLD",
    "COVERAGE_DEGRADATION_FACTOR",
    "MAX_COVERAGE_SCALE_FACTOR",
    "PER_PATH_TIMEOUT_RATIO",
    "_SYS_MODULES_LOCK",
    "set_memory_limit",
]
