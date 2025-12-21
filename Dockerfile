# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Symbolic MCP Contributors

FROM python:3.11-slim

# Z3 solver requires build tools for optimal performance
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Security: run as non-root user
RUN useradd --create-home --shell /bin/bash mcp

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY --chown=mcp:mcp . .

USER mcp

# Environment config
ENV PYTHONUNBUFFERED=1
ENV MCP_TRANSPORT=stdio
# Memory limit for Z3 solver (2GB)
ENV Z3_MEMORY_LIMIT=2048

# Healthcheck ensures CrossHair and Z3 are importable
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import crosshair; import z3; print('ok')" || exit 1

ENTRYPOINT ["python", "main.py"]
