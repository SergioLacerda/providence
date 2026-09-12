"""Artifact-oriented governance handlers (compile/generate/consistency)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from providence_cli.services._governance_artifact_consistency import (
    _count_items_by_type,
    _has_malformed_titles,
    _load_consistency_artifacts,
    _safe_json,
    _validate_payload_vs_metadata,
)
from providence_cli.services._governance_artifact_consistency import (
    check_artifact_consistency as _check_artifact_consistency,
)
from providence_cli.services.governance_payloads import (
    build_governance_compile_data,
    build_governance_generate_data,
    governance_error,
    governance_ok,
)
from providence_cli.utils.loader import resolve_governance_compiled_dir
from providence_cli.utils.output import emit_json

__all__ = [
    "check_artifact_consistency",
    "emit_generate_invalid_path_error",
    "emit_generate_missing_items_error",
    "render_generate_table",
    "render_governance_compile_table",
    "run_governance_compile_json",
    "run_governance_generate_json",
    "_count_items_by_type",
    "_has_malformed_titles",
    "_load_consistency_artifacts",
    "_safe_json",
    "_validate_payload_vs_metadata",
]


def run_governance_compile_json(
    *,
    phase_1: dict[str, Any],
    phase_2: dict[str, Any],
    core_fingerprint: str,
    consistency_ok: bool,
    consistency_reason: str,
) -> tuple[dict[str, Any], bool]:
    """Build canonical JSON payload for compile command.

    Returns `(payload, is_error)`.
    """
    if not consistency_ok:
        data = build_governance_compile_data(
            core_items=int(phase_1.get("core_item_count", 0)),
            client_items=int(phase_1.get("client_item_count", 0)),
            core_msgpack=str(phase_2.get("core_msgpack_file", "N/A")),
            client_msgpack=str(phase_2.get("client_msgpack_file", "N/A")),
            core_fingerprint=core_fingerprint,
            consistency_reason=consistency_reason,
            exit_code=1,
        )
        return (
            governance_error(
                "governance compile",
                data,
                code="artifact_consistency_failed",
                message=f"Artifact consistency failed: {consistency_reason}",
            ),
            True,
        )

    data = build_governance_compile_data(
        core_items=int(phase_1.get("core_item_count", 0)),
        client_items=int(phase_1.get("client_item_count", 0)),
        core_msgpack=str(phase_2.get("core_msgpack_file", "N/A")),
        client_msgpack=str(phase_2.get("client_msgpack_file", "N/A")),
        core_fingerprint=core_fingerprint,
        exit_code=0,
    )
    return governance_ok("governance compile", data), False


def render_governance_compile_table(
    *,
    console: Console,
    phase_1: dict[str, Any],
    phase_2: dict[str, Any],
    core_fingerprint: str,
) -> None:
    """Render human-readable compile summary."""
    table = Table(title="Compilation Summary", show_header=True, header_style="bold")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Core items", str(int(phase_1.get("core_item_count", 0))))
    table.add_row("Client items", str(int(phase_1.get("client_item_count", 0))))
    table.add_row("Core msgpack", str(phase_2.get("core_msgpack_file", "N/A")))
    table.add_row("Client msgpack", str(phase_2.get("client_msgpack_file", "N/A")))
    console.print(table)


def run_governance_generate_json(
    *,
    resolved_path: str,
    output_base: Path,
    seeds_dir: Path,
    rows: list[dict[str, Any]],
    skills_generated: bool,
    skill_index_generated: bool,
    cli_index_generated: bool,
) -> dict[str, Any]:
    """Build canonical JSON payload for generate command."""
    data = build_governance_generate_data(
        path=resolved_path,
        output_base=str(output_base),
        seeds_dir=str(seeds_dir),
        generated_files=rows,
        skills_generated=skills_generated,
        skill_index_generated=skill_index_generated,
        cli_index_generated=cli_index_generated,
        exit_code=0,
    )
    return governance_ok("governance generate", data)


def emit_generate_invalid_path_error(*, resolved_path: str, output_dir: str) -> None:
    """Emit canonical invalid-path error for governance generate."""
    data = {"path": resolved_path, "output_base": output_dir, "exit_code": 1}
    payload = governance_error(
        "governance generate",
        data,
        code="invalid_governance_path",
        message=f"Invalid governance path: {resolved_path}",
    )
    emit_json(payload, err=True)
    raise typer.Exit(1)


def emit_generate_missing_items_error(*, resolved_path: str, output_dir: str) -> None:
    """Emit canonical missing-items error for governance generate."""
    data = {"path": resolved_path, "output_base": output_dir, "exit_code": 1}
    payload = governance_error(
        "governance generate",
        data,
        code="missing_governance_items",
        message=(
            "No governance items loaded. Run 'providence governance compile' "
            "before 'providence governance generate'."
        ),
    )
    emit_json(payload, err=True)
    raise typer.Exit(1)


def render_generate_table(
    *, console: Console, rows: list[dict[str, Any]], seeds_dir: Path
) -> None:
    """Render human-readable generated files table."""
    table = Table(title="Generated Files", show_header=True, header_style="bold")
    table.add_column("Agent Template", style="cyan")
    table.add_column("Location", style="green")
    table.add_column("Status", style="green")
    for row in rows:
        table.add_row(row["agent_template"], row["location"], row["status"])
    console.print(table)
    console.print(
        Panel(
            f"[green]Agent seeds generated to {seeds_dir}[/green]",
            border_style="green",
        )
    )


def check_artifact_consistency(path: str) -> tuple[bool, str]:
    """Check compiled governance artifacts for consistency issues."""
    return _check_artifact_consistency(
        path,
        resolve_compiled_dir_fn=resolve_governance_compiled_dir,
    )
