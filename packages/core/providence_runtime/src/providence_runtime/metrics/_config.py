"""Token budget configuration resolution (env vars, pyproject.toml, defaults)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def _load_token_budget_config() -> dict[str, Any]:
    """Load token budget configuration from pyproject.toml or environment.

    Resolution order:
    1. Environment variables (SDD_TOKEN_BUDGET_CEILING, SDD_CONTEXT_COMPRESSION_THRESHOLD, SDD_CONTEXT_COMPRESSION_TARGET)
    2. pyproject.toml [tool.providence.runtime] configuration
    3. Default values

    Returns:
        Dict with keys: token_budget_ceiling, context_compression_threshold, context_compression_target
    """
    # Environment variable overrides
    if os.environ.get("SDD_TOKEN_BUDGET_CEILING"):
        ceiling = int(os.environ.get("SDD_TOKEN_BUDGET_CEILING", "100000"))
    else:
        ceiling = 100000

    if os.environ.get("SDD_CONTEXT_COMPRESSION_THRESHOLD"):
        threshold = float(os.environ.get("SDD_CONTEXT_COMPRESSION_THRESHOLD", "70"))
    else:
        threshold = 70.0

    if os.environ.get("SDD_CONTEXT_COMPRESSION_TARGET"):
        target = float(os.environ.get("SDD_CONTEXT_COMPRESSION_TARGET", "50"))
    else:
        target = 50.0

    # Try to load from pyproject.toml if environment variables not set
    pyproject_path = Path.cwd() / "pyproject.toml"
    if pyproject_path.exists() and not os.environ.get("SDD_TOKEN_BUDGET_CEILING"):
        try:
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib

            with open(pyproject_path, "rb") as f:
                config = tomllib.load(f)

            providence_runtime = (
                config.get("tool", {}).get("sdd", {}).get("runtime", {})
            )
            ceiling = providence_runtime.get("token_budget_ceiling", ceiling)
            threshold = providence_runtime.get(
                "context_compression_threshold", threshold
            )
            target = providence_runtime.get("context_compression_target", target)
        except Exception:  # nosec B110
            # If pyproject.toml reading fails, use defaults
            pass

    return {
        "token_budget_ceiling": ceiling,
        "context_compression_threshold": threshold,
        "context_compression_target": target,
    }
