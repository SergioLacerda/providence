"""Compile-phase governance handlers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from providence_cli.services._governance_compile_flow import run_compile_flow
from providence_cli.services._governance_compile_support import (
    compliance_components,
    maybe_load_artifact_fingerprint,
    resolve_output_base_path,
)
from providence_cli.services.governance_compile_telemetry import (
    emit_compile_telemetry,
    regenerate_seeds,
)
from providence_cli.utils.providence_authority import (
    compiled_active_dir,
    resolve_workspace_root,
)


def compute_compliance_score(
    *, compile_ok: bool, consistency_ok: bool, drift_detected: bool
) -> tuple[int, dict[str, bool]]:
    """Compute the governance compliance score and its components."""
    return compliance_components(
        compile_ok=compile_ok,
        consistency_ok=consistency_ok,
        drift_detected=drift_detected,
    )


def resolve_output_base(output_dir: Path) -> Path:
    """Resolve the base output directory for compiled governance artifacts."""
    return resolve_output_base_path(
        output_dir,
        override=os.environ.get("SDD_TEST_OUTPUT_DIR", "").strip(),
        resolve_workspace_root_fn=resolve_workspace_root,
    )


def run_compilation(
    profile: str | None = None, *, console: Console | None = None
) -> Any:
    """Run GovernanceOrchestrator full pipeline. Raises typer.Exit(1) on failure."""
    if console is None:
        console = Console()
    from providence_core.governance_orchestrator import (
        GovernanceOrchestrator,
        PipelineResult,
    )

    orchestrator = GovernanceOrchestrator(profile=profile)
    result: PipelineResult = orchestrator.run_full_pipeline()
    if not result or not result.get("full_pipeline_success"):
        console.print("[red]ERROR: governance compilation failed[/red]")
        console.print(
            "  Next: check .providence/source artifacts or run 'providence governance validate'"
        )
        raise typer.Exit(1)
    return result


def update_profile_hash(
    core_fingerprint: str, *, console: Console | None = None
) -> None:
    """Update the `.providence/profile` core_hash with the given fingerprint."""
    if console is None:
        console = Console()
    if not core_fingerprint:
        return
    try:
        import configparser

        ws_root = resolve_workspace_root()
        core_fingerprint = maybe_load_artifact_fingerprint(
            core_fingerprint,
            workspace_root=ws_root,
            compiled_active_dir_fn=compiled_active_dir,
        )

        output_base = resolve_output_base(ws_root)
        profile_path = output_base / ".providence" / "profile"
        if profile_path.exists():
            parser = configparser.ConfigParser()
            parser.read(profile_path)
            if "sdd" in parser:
                parser["sdd"]["core_hash"] = core_fingerprint[:16]
                with open(profile_path, "w", encoding="utf-8") as f:
                    parser.write(f)
                console.print(
                    f"[cyan]core_hash updated in .providence/profile ({core_fingerprint[:16]})[/cyan]"
                )
    except Exception as _e:
        console.print(
            f"[yellow]WARN: could not update core_hash in .providence/profile: {_e}[/yellow]"
        )


def run_compile(
    *, profile: str | None, output_json: bool, console: Console | None = None
) -> None:
    """Run the `providence governance compile` command flow."""
    if console is None:
        console = Console()
    from rich.panel import Panel

    from providence_cli.services.governance_artifact_handlers import (
        check_artifact_consistency,
        run_governance_compile_json,
    )
    from providence_cli.services.governance_command_output import handle_compile_output
    from providence_cli.utils.providence_authority import resolve_workspace_root

    run_compile_flow(
        profile=profile,
        output_json=output_json,
        console=console,
        panel_cls=Panel,
        run_compilation_fn=run_compilation,
        update_profile_hash_fn=update_profile_hash,
        resolve_workspace_root_fn=resolve_workspace_root,
        check_artifact_consistency_fn=check_artifact_consistency,
        run_governance_compile_json_fn=run_governance_compile_json,
        handle_compile_output_fn=handle_compile_output,
        emit_compile_telemetry_fn=emit_compile_telemetry,
        regenerate_seeds_fn=regenerate_seeds,
    )
