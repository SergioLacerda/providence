"""Generate-phase governance handlers."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel

from providence_cli.generators.agent_seeds import generate_agent_seeds
from providence_cli.services._governance_generate_support import (
    generate_artifacts_flow,
    run_generate_flow,
)
from providence_cli.services.governance_artifact_handlers import (
    render_generate_table,
    run_governance_generate_json,
)
from providence_cli.services.governance_bootstrap_handlers import (
    complete_bootstrap_handshake,
    run_bootstrap_signing,
)
from providence_cli.services.governance_command_output import fail_generate_precondition
from providence_cli.services.governance_compile_handlers import resolve_output_base
from providence_cli.services.governance_generate_prereqs import (
    generate_adapters_safe,
    generate_runtime_handbook_required,
    write_instruction_files_safe,
    write_prompt_commands_safe,
)
from providence_cli.utils.loader import load_governance_config, validate_governance_path
from providence_cli.utils.output import emit_json
from providence_cli.utils.providence_authority import (
    enforce_path_policy,
    resolve_workspace_root,
)

logger = logging.getLogger(__name__)


def resolve_generate_path(path: str) -> str:
    """Resolve the output path for `providence governance generate`."""
    if path:
        return path
    ws_root = resolve_workspace_root()
    if ws_root is None:
        raise typer.Exit(1)
    ws_root = enforce_path_policy(ws_root, workspace_root=ws_root, mode="normal")
    return str(ws_root / ".providence" / "compiled")


def generate_seeds(
    output_dir: str, config: dict[str, Any]
) -> tuple[list[tuple[str, Path, str]], Path]:
    """Generate agent seed files into the output directory's `.vscode/agents`."""
    seeds_dir = Path(output_dir) / ".vscode" / "agents"
    seeds_info = generate_agent_seeds(seeds_dir, config)
    return seeds_info, seeds_dir


def run_generate_phases(
    output_base: str, config: dict[str, Any]
) -> tuple[bool, bool, bool]:
    """Run skill/command registry and index generation phases."""
    from providence_cli.generators._commands import generate_commands_registry
    from providence_cli.generators._indices import (
        generate_cli_commands_index,
        generate_skill_index,
    )
    from providence_cli.generators._skills import generate_skills_registry

    try:
        skills_result = generate_skills_registry(output_base, config)
        skills_generated = skills_result.get("skill_count", 0) > 0
    except Exception as e:
        logger.debug(f"Skills registry generation failed: {e}")
        skills_generated = False

    try:
        generate_commands_registry(output_base, config)
    except Exception as e:
        logger.debug(f"Commands registry generation failed: {e}")

    try:
        skill_index_result = generate_skill_index(output_base, config)
        skill_index_generated = skill_index_result.get("skill_count", 0) > 0
    except Exception as e:
        logger.debug(f"Skill index generation failed: {e}")
        skill_index_generated = False

    try:
        cli_index_result = generate_cli_commands_index(output_base, config)
        cli_index_generated = cli_index_result.get("command_count", 0) > 0
    except Exception as e:
        logger.debug(f"CLI commands index generation failed: {e}")
        cli_index_generated = False

    return skills_generated, skill_index_generated, cli_index_generated


def generate_artifacts(
    *, output_dir: str | None, path: str, output_json: bool, console: Console
) -> None:
    """Generate agent artifacts (seeds, instructions, prompt commands, adapters)."""
    generate_artifacts_flow(
        output_dir=output_dir,
        path=path,
        output_json=output_json,
        console=console,
        resolve_workspace_root_fn=resolve_workspace_root,
        resolve_generate_path_fn=resolve_generate_path,
        validate_governance_path_fn=validate_governance_path,
        fail_generate_precondition_fn=fail_generate_precondition,
        load_governance_config_fn=load_governance_config,
        resolve_output_base_fn=resolve_output_base,
        generate_seeds_fn=generate_seeds,
        run_generate_phases_fn=run_generate_phases,
        run_governance_generate_json_fn=run_governance_generate_json,
        emit_json_fn=emit_json,
        render_generate_table_fn=render_generate_table,
        write_instruction_files_safe_fn=write_instruction_files_safe,
        write_prompt_commands_safe_fn=write_prompt_commands_safe,
        generate_adapters_safe_fn=generate_adapters_safe,
        generate_runtime_handbook_fn=generate_runtime_handbook_required,
        panel_cls=Panel,
    )


def run_generate(
    *,
    output_dir: str | None,
    path: str,
    full_bootstrap: bool,
    key_id: str,
    profile: str,
    output_json: bool,
    console: Console,
    compile_fn: Any = None,
    keygen_fn: Any = None,
    sign_fn: Any = None,
) -> None:
    """Run the `providence governance generate` command flow."""
    run_generate_flow(
        output_dir=output_dir,
        path=path,
        full_bootstrap=full_bootstrap,
        key_id=key_id,
        profile=profile,
        output_json=output_json,
        console=console,
        compile_fn=compile_fn,
        keygen_fn=keygen_fn,
        sign_fn=sign_fn,
        generate_artifacts_fn=generate_artifacts,
        run_bootstrap_signing_fn=run_bootstrap_signing,
        complete_bootstrap_handshake_fn=complete_bootstrap_handshake,
        panel_cls=Panel,
    )
