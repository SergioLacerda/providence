from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import typer


def collect_challenge_skills(challenge: Any) -> list[str]:
    names: list[str] = []
    for skill in challenge.available_skills:
        if isinstance(skill, dict):
            name = skill.get("name")
            if isinstance(name, str):
                names.append(name)
    return names


def run_bootstrap_signing_flow(
    key_id: str,
    *,
    keygen_fn: Any,
    sign_fn: Any,
    resolve_workspace_root_fn: Callable[[], Path | None],
) -> None:
    try:
        keygen_fn(key_id=key_id, output_dir=".providence/trust")
    except typer.Exit as exc:
        if int(exc.exit_code or 0) != 0:
            raise
    sign_fn(key_id=key_id, key_path=None, compiled_dir=None, source=False)
    ws_root = resolve_workspace_root_fn()
    if (
        ws_root is not None
        and (ws_root / ".providence" / "source" / "governance-core.json").exists()
    ):
        sign_fn(key_id=key_id, key_path=None, compiled_dir=None, source=True)


def normalize_run_generate_args(
    full_bootstrap: Any, key_id: Any, profile: Any
) -> tuple[bool, str, str]:
    return (
        full_bootstrap if isinstance(full_bootstrap, bool) else False,
        key_id if isinstance(key_id, str) else "dev-01",
        profile if isinstance(profile, str) else "client",
    )


def bootstrap_response(challenge: Any) -> dict[str, Any]:
    return {
        "agent_id": os.environ.get("SDD_AGENT_ID", "bootstrap"),
        "understood_mandates": challenge.active_mandates,
        "skills_to_use": collect_challenge_skills(challenge),
        "acknowledged_signature": True,
        "plan_summary": "bootstrap handshake auto-registered",
        "compliance_declaration": True,
    }


def generate_artifacts_flow(
    *,
    output_dir: str | None,
    path: str,
    output_json: bool,
    console: Any,
    resolve_workspace_root_fn: Callable[[], Path | None],
    resolve_generate_path_fn: Callable[[str], str],
    validate_governance_path_fn: Callable[[str], bool],
    fail_generate_precondition_fn: Callable[..., Any],
    load_governance_config_fn: Callable[[str], dict[str, Any]],
    resolve_output_base_fn: Callable[[Path], Path],
    generate_seeds_fn: Callable[
        [str, dict[str, Any]], tuple[list[tuple[str, Path, str]], Path]
    ],
    run_generate_phases_fn: Callable[[str, dict[str, Any]], tuple[bool, bool, bool]],
    run_governance_generate_json_fn: Callable[..., dict[str, Any]],
    emit_json_fn: Callable[[dict[str, Any]], Any],
    render_generate_table_fn: Callable[..., Any],
    write_instruction_files_safe_fn: Callable[..., Any],
    write_prompt_commands_safe_fn: Callable[..., Any],
    generate_adapters_safe_fn: Callable[..., Any],
    generate_runtime_handbook_fn: Callable[..., Any],
    panel_cls: Any,
) -> None:
    if output_dir is None:
        output_dir = str(resolve_workspace_root_fn())
    resolved_path = resolve_generate_path_fn(path)
    if not validate_governance_path_fn(resolved_path):
        fail_generate_precondition_fn(
            output_json=output_json,
            code="invalid_governance_path",
            message=f"Invalid governance path: {resolved_path}",
            data={"resolved_path": resolved_path, "output_dir": str(output_dir or "")},
            console=console,
        )
    if not output_json:
        console.print(
            panel_cls(
                "[bold cyan]Generating Agent Seeds[/bold cyan]", border_style="cyan"
            )
        )
    config = load_governance_config_fn(resolved_path)
    items = config.get("items", []) if isinstance(config, dict) else []
    if not isinstance(items, list) or len(items) == 0:
        fail_generate_precondition_fn(
            output_json=output_json,
            code="missing_governance_items",
            message="No governance items loaded. Run 'providence governance compile' before 'providence governance generate'.",
            data={"resolved_path": resolved_path, "output_dir": str(output_dir or "")},
            console=console,
        )
    output_base = resolve_output_base_fn(Path(output_dir))
    seeds_info, seeds_dir = generate_seeds_fn(str(output_base), config)
    skills_generated, skill_index_generated, cli_index_generated = (
        run_generate_phases_fn(str(output_base), config)
    )
    rows = [
        {"agent_template": agent, "location": str(file_path), "status": status}
        for agent, file_path, status in seeds_info
    ]
    generate_runtime_handbook_fn(output_base, console=console, quiet=output_json)
    if output_json:
        emit_json_fn(
            run_governance_generate_json_fn(
                resolved_path=resolved_path,
                output_base=output_base,
                seeds_dir=seeds_dir,
                rows=rows,
                skills_generated=skills_generated,
                skill_index_generated=skill_index_generated,
                cli_index_generated=cli_index_generated,
            )
        )
        return
    render_generate_table_fn(console=console, rows=rows, seeds_dir=seeds_dir)
    write_instruction_files_safe_fn(output_base, config, console=console)
    write_prompt_commands_safe_fn(output_base, config, console=console)
    generate_adapters_safe_fn(output_base, console=console)


def run_generate_flow(
    *,
    output_dir: str | None,
    path: str,
    full_bootstrap: Any,
    key_id: Any,
    profile: Any,
    output_json: bool,
    console: Any,
    compile_fn: Any,
    keygen_fn: Any,
    sign_fn: Any,
    generate_artifacts_fn: Callable[..., Any],
    run_bootstrap_signing_fn: Callable[..., Any],
    complete_bootstrap_handshake_fn: Callable[[], Any],
    panel_cls: Any,
) -> None:
    full_bootstrap, key_id, profile = normalize_run_generate_args(
        full_bootstrap, key_id, profile
    )
    if not full_bootstrap:
        generate_artifacts_fn(
            output_dir=output_dir, path=path, output_json=output_json, console=console
        )
        return
    if not output_json:
        console.print(
            panel_cls(
                "[bold cyan]Full Bootstrap[/bold cyan]\nRunning compile + generate + keygen + sign steps",
                border_style="cyan",
            )
        )
    if compile_fn is not None:
        compile_fn(profile=profile)
    generate_artifacts_fn(
        output_dir=output_dir, path=path, output_json=output_json, console=console
    )
    run_bootstrap_signing_fn(key_id, keygen_fn=keygen_fn, sign_fn=sign_fn)
    complete_bootstrap_handshake_fn()
    if not output_json:
        console.print(
            "[dim]Full bootstrap refreshed the active session handshake "
            "(M015) — a handshake response completed before this run is "
            "no longer valid and must be redone.[/dim]"
        )
