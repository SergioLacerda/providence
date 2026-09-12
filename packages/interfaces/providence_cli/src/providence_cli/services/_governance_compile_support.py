from __future__ import annotations

import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def compliance_components(
    *, compile_ok: bool, consistency_ok: bool, drift_detected: bool
) -> tuple[int, dict[str, bool]]:
    components = {
        "governance_compile": compile_ok,
        "consistency": consistency_ok,
        "drift_detected": not drift_detected,
        "lint_gate": True,
    }
    return sum(25 for value in components.values() if value), components


def resolve_output_base_path(
    output_dir: Path,
    *,
    override: str,
    resolve_workspace_root_fn: Callable[[], Path | None],
) -> Path:
    output = output_dir.resolve()
    if not override:
        return output
    redirected = Path(override).resolve()
    env_workspace = os.environ.get("SDD_WORKSPACE_ROOT", "").strip()
    if env_workspace:
        try:
            workspace_root = Path(env_workspace).expanduser().resolve()
        except Exception:
            workspace_root = None
    else:
        workspace_root = None
    try:
        resolved_workspace = resolve_workspace_root_fn()
    except Exception:
        resolved_workspace = None
    if workspace_root is None:
        workspace_root = resolved_workspace
    if workspace_root is not None and output == workspace_root.resolve():
        redirected.mkdir(parents=True, exist_ok=True)
        return redirected
    if (
        env_workspace
        and resolved_workspace is not None
        and output == resolved_workspace.resolve()
        and not _is_session_default_override(redirected)
    ):
        redirected.mkdir(parents=True, exist_ok=True)
        return redirected
    return output


def _is_session_default_override(path: Path) -> bool:
    return path.name == f"sdd-test-output-{os.getpid()}"


def maybe_load_artifact_fingerprint(
    core_fingerprint: str,
    *,
    workspace_root: Path,
    compiled_active_dir_fn: Callable[[Path | None], Path],
) -> str:
    import json

    artifact = compiled_active_dir_fn(workspace_root) / "governance-core.json"
    if not artifact.exists():
        return core_fingerprint
    try:
        artifact_fp = str(
            json.loads(artifact.read_text(encoding="utf-8")).get("fingerprint", "")
        ).strip()
        return artifact_fp or core_fingerprint
    except Exception as exc:
        logger.debug("Failed to read artifact fingerprint from %s: %s", artifact, exc)
        return core_fingerprint


def maybe_regenerate_wizard_contracts(
    output_base: Path, config: dict[str, Any], *, console: Any
) -> None:
    try:
        from providence_wizard.contracts import (
            generate_agent_instructions_from_config,
            generate_root_bootstrap_from_config,
        )

        generate_agent_instructions_from_config(output_base, config)
        console.print("[cyan].providence/agent-instructions.md regenerated[/cyan]")
        generate_root_bootstrap_from_config(output_base, config)
        console.print("[cyan]Root bootstrap files regenerated[/cyan]")
    except ImportError:
        console.print(
            "[yellow]WARN: providence_wizard not available, skipping agent-instructions.md regeneration[/yellow]"
        )


def _bridge_client_language_context(
    workspace_root: Path, metadata: dict[str, Any]
) -> dict[str, str] | None:
    """Synthesize `language_context` from `.providence/profile`'s `language` key.

    Only applies when the wizard hasn't already populated `language_context`
     wizard output always wins (it may distinguish interaction vs. docs
    language, which a bare client `language` value cannot). Returns None when
    there is nothing to bridge (no client `language` key, or wizard data
    already present), so the caller leaves `metadata["language_context"]`
    untouched in either case.
    """
    existing = metadata.get("language_context")
    if isinstance(existing, dict) and existing:
        return None

    from providence_core.utils.environment import (
        WorkspaceNotInitializedError,
        resolve_profile,
    )

    try:
        profile = resolve_profile(root=workspace_root)
    except WorkspaceNotInitializedError:
        return None

    if not profile.language:
        return None

    return {
        "preferred_human_language": profile.language,
        "preferred_chat_language": profile.language,
        "preferred_ui_language": profile.language,
        "preferred_local_docs_language": profile.language,
    }


def normalize_compile_context(
    result: dict[str, Any], *, workspace_root: Path | None
) -> tuple[dict[str, Any], dict[str, Any], str]:
    phase_1 = result.get("phase_1", {})
    phase_2 = result.get("phase_2", {})
    compiled_path = (
        str(workspace_root / ".providence" / "compiled") if workspace_root else ""
    )
    return phase_1, phase_2, compiled_path
