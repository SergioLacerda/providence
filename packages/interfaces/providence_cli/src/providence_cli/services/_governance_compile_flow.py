"""Compile-flow orchestration: metadata sync, seed regeneration, top-level compile flow.

Split out of `_governance_compile_support.py` (T10,
`.analysis/pending/2026-06-15-providence-cli-refactoring-pending-followup.md`).
"""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from providence_cli.services._governance_compile_support import (
    _bridge_client_language_context,
    maybe_regenerate_wizard_contracts,
    normalize_compile_context,
)


def sync_workspace_metadata_from_config(
    workspace_root: Path, config: dict[str, Any]
) -> bool:
    """Align `.providence/metadata.json` with the compiled governance snapshot."""
    import hashlib
    import json

    items = config.get("items", [])
    if not isinstance(items, list) or not items:
        return False

    fingerprint = str(config.get("core_fingerprint") or config.get("fingerprint") or "")
    if not fingerprint:
        return False

    metadata_path = workspace_root / ".providence" / "metadata.json"
    try:
        metadata = (
            json.loads(metadata_path.read_text(encoding="utf-8"))
            if metadata_path.exists()
            else {}
        )
    except json.JSONDecodeError:
        metadata = {}

    mandates = [
        item for item in items if str(item.get("type", "")).strip().upper() == "MANDATE"
    ]
    guidelines = [
        item
        for item in items
        if str(item.get("type", "")).strip().upper() in {"GUIDELINE", "RULE"}
    ]
    mandate_map = {
        str(item.get("id")): str(item.get("title") or item.get("name") or "Unknown")
        for item in mandates
        if item.get("id")
    }
    mandate_fingerprints = {
        str(item.get("id")): hashlib.sha256(
            json.dumps(item, sort_keys=True).encode("utf-8")
        ).hexdigest()[:16]
        for item in mandates
        if item.get("id")
    }

    existing_fingerprints = metadata.get("fingerprints")
    fingerprints_base: dict[str, Any] = (
        existing_fingerprints if isinstance(existing_fingerprints, dict) else {}
    )

    language_context_update = _bridge_client_language_context(workspace_root, metadata)

    metadata.update(
        {
            "version": str(metadata.get("version") or "3.0"),
            "generated_at": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "mandates_count": len(mandates),
            "guidelines_count": len(guidelines),
            "governance_fingerprint": fingerprint[:16],
            "fingerprints": {
                **fingerprints_base,
                "combined": fingerprint[:16],
                "mandates": mandate_fingerprints,
            },
            "mandates": mandate_map,
        }
    )
    if language_context_update is not None:
        metadata["language_context"] = language_context_update
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return True


def regenerate_seeds_flow(
    *,
    console: Any,
    resolve_workspace_root_fn: Callable[[], Path | None],
    validate_governance_path_fn: Callable[[str], bool],
    load_governance_config_fn: Callable[[str], dict[str, Any]],
    resolve_output_base_fn: Callable[[Path], Path],
    generate_agent_instruction_files_fn: Callable[[Path, dict[str, Any]], Any],
    generate_runtime_handbook_fn: Callable[..., list[Path]] | None = None,
) -> None:
    if os.environ.get("SDD_SKIP_SEED_REGEN") == "1":
        return
    workspace_root = resolve_workspace_root_fn()
    if workspace_root is None:
        return
    generate_path = str(workspace_root / ".providence" / "compiled")
    config = (
        load_governance_config_fn(generate_path)
        if validate_governance_path_fn(generate_path)
        else {}
    )
    output_base = resolve_output_base_fn(workspace_root)
    if sync_workspace_metadata_from_config(output_base, config):
        console.print("[cyan].providence/metadata.json synchronized[/cyan]")
    generate_agent_instruction_files_fn(output_base, config)
    console.print("[cyan]Agent instruction files regenerated[/cyan]")
    maybe_regenerate_wizard_contracts(output_base, config, console=console)
    if generate_runtime_handbook_fn is not None:
        written = generate_runtime_handbook_fn(workspace_root, runtime_root=output_base)
        if written:
            console.print(
                f"[cyan]Runtime handbook regenerated ({len(written)} files)[/cyan]"
            )


def run_compile_flow(
    *,
    profile: str | None,
    output_json: bool,
    console: Any,
    panel_cls: Any,
    run_compilation_fn: Callable[..., dict[str, Any]],
    update_profile_hash_fn: Callable[..., Any],
    resolve_workspace_root_fn: Callable[[], Path | None],
    check_artifact_consistency_fn: Callable[[str], tuple[bool, str]],
    run_governance_compile_json_fn: Callable[..., tuple[dict[str, Any], bool]],
    handle_compile_output_fn: Callable[..., Any],
    emit_compile_telemetry_fn: Callable[..., Any],
    regenerate_seeds_fn: Callable[..., Any],
) -> None:
    if not output_json:
        console.print(
            panel_cls(
                "[bold cyan]Compiling Governance Artifacts[/bold cyan]",
                border_style="cyan",
            )
        )
    if profile is not None and profile not in ("master", "client"):
        import typer as _typer
        from rich.console import Console as _Console

        _Console(stderr=True).print(
            f"[red]ERROR: Invalid profile '{profile}'. Use 'master' or 'client'.[/red]"
        )
        raise _typer.Exit(1)
    result = run_compilation_fn(profile=profile, console=console)
    workspace_root = resolve_workspace_root_fn()
    phase_1, phase_2, compiled_path = normalize_compile_context(
        result, workspace_root=workspace_root
    )
    core_fingerprint = str(phase_1.get("core_fingerprint", ""))
    update_profile_hash_fn(core_fingerprint, console=console)
    consistency_ok, consistency_reason = check_artifact_consistency_fn(compiled_path)
    payload, is_error = run_governance_compile_json_fn(
        phase_1=phase_1,
        phase_2=phase_2,
        core_fingerprint=core_fingerprint,
        consistency_ok=consistency_ok,
        consistency_reason=consistency_reason,
    )
    handle_compile_output_fn(
        output_json=output_json,
        payload=payload,
        is_error=is_error,
        phase_1=phase_1,
        phase_2=phase_2,
        core_fingerprint=core_fingerprint,
        consistency_reason=consistency_reason,
        console=console,
        artifact_path=compiled_path,
    )
    emit_compile_telemetry_fn(
        core_fingerprint=core_fingerprint,
        is_error=is_error,
        consistency_ok=consistency_ok,
        profile=profile,
    )
    regenerate_seeds_fn(console=console)
