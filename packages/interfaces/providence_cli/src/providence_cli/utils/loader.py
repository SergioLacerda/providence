"""Loader."""

import logging
from pathlib import Path
from typing import Any

from providence_cli.utils.providence_authority import (
    PathPolicyViolation,
    enforce_path_policy,
    resolve_workspace_root,
)

logger = logging.getLogger(__name__)


def _required_files(base: Path) -> list[Path]:
    metadata_core = (
        base / "audit" / "metadata-core.json"
        if (base / "audit" / "metadata-core.json").exists()
        else base / "metadata-core.json"
    )
    metadata_client = (
        base / "audit" / "metadata-client-template.json"
        if (base / "audit" / "metadata-client-template.json").exists()
        else base / "metadata-client-template.json"
    )
    return [
        base / "governance-core.compiled.msgpack",
        base / "governance-client-template.compiled.msgpack",
        metadata_core,
        metadata_client,
    ]


def _all_exist(files: list[Path]) -> bool:
    return all(f.exists() for f in files)


def _resolve_compiled_dir(path: str) -> Path | None:  # noqa: C901
    """Resolve governance compiled directory from a user path.

    Contract: .providence is the only source of truth for governance artifacts.
    Legacy /generated resolution is intentionally unsupported.
    """
    try:
        mode = "extraordinary_audit" if path.startswith("extraordinary:") else "normal"
        raw = path.removeprefix("extraordinary:")
        # Resolve workspace root from the provided path (handles .providence walk-up)
        workspace_root = resolve_workspace_root(Path(raw))
        path_obj = enforce_path_policy(
            Path(raw),
            workspace_root=workspace_root,
            mode=mode,
        )
    except PathPolicyViolation as e:
        logger.debug(f"Path policy violation resolving {path}: {e.reason} ({e.hint})")
        return None

    # 1. Direct path has required files.
    if _all_exist(_required_files(path_obj)):
        return path_obj

    # 2. `compiled/` subdirectory.
    compiled_dir = path_obj / "compiled"
    if _all_exist(_required_files(compiled_dir)):
        return compiled_dir

    # 3. Final template nested runtime layout: `.providence/compiled`.
    sdd_compiled_dir = path_obj / ".providence" / "compiled"
    if _all_exist(_required_files(sdd_compiled_dir)):
        return sdd_compiled_dir

    return None


def load_governance_config(path: str) -> dict[str, Any]:
    """Load governance configuration from providence_core loader."""
    try:
        from providence_core.utils.loader import GovernanceLoader

        compiled_dir = _resolve_compiled_dir(path)
        if compiled_dir is None:
            raise ValueError(
                f"Invalid governance path or blocked by path policy: {path}"
            )

        loader = GovernanceLoader(str(compiled_dir))
        # Load core and client separately if needed, or use load_all
        status = loader.load_all()

        core_items = (
            loader.packages_data.get("items", []) if loader.packages_data else []
        )
        client_items = (
            loader._client_data.get("items", []) if loader._client_data else []
        )
        all_items = core_items + client_items

        return {
            "core_fingerprint": status.get("core_fingerprint"),
            "client_fingerprint": status.get("client_fingerprint"),
            "items": all_items,
            "core_items_count": len(core_items),
            "client_items_count": len(client_items),
        }
    except Exception as e:
        raise ValueError(f"Failed to load governance config: {e}") from e


def validate_governance_path(path: str) -> bool:
    """Validate that governance path contains required files."""
    return _resolve_compiled_dir(path) is not None


def resolve_governance_compiled_dir(path: str) -> Path | None:
    """Resolve compiled governance directory from user-provided path."""
    return _resolve_compiled_dir(path)


def get_governance_summary(
    path: str, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Get human-readable governance summary."""
    if config is None:
        config = load_governance_config(path)

    return {
        "Configuration Path": path,
        "Status": "Ready",
        "Core Items": config.get("core_items_count", 0),
        "Customizable Items": config.get("client_items_count", 0),
        "Total Items": len(config.get("items", [])),
        "Core Fingerprint": config.get("core_fingerprint", "N/A")[:16] + "...",
        "Client Fingerprint": config.get("client_fingerprint", "N/A")[:16] + "...",
    }
