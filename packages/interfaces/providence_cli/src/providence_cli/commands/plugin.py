"""Plugin registry commands  list and validate analysis provider plugins."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click
import typer

from providence_cli.services.command_group_output import show_command_group
from providence_cli.utils.output import emit_json, is_json_mode
from providence_cli.utils.providence_authority import resolve_workspace_root


def _ctx_json() -> bool:
    return is_json_mode(click.get_current_context(silent=True))


app = typer.Typer(help="Plugin registry management", invoke_without_command=True)


@app.callback(invoke_without_command=True)
def plugin_default(
    ctx: typer.Context,
    list_commands: bool = typer.Option(False, "--list", help="List plugin commands."),
) -> None:
    """Plugin registry operations."""
    if list_commands or ctx.invoked_subcommand is None:
        show_command_group("Plugin", ["list", "validate"])
        raise typer.Exit(0)


_REQUIRED_FIELDS = [
    "id",
    "type",
    "version",
    "status",
    "entrypoint",
    "contract",
    "sdd_injection",
]
_REQUIRED_INJECTION_FIELDS = [
    "base_path",
    "execution_provider",
    "approval_gate",
]
_KNOWN_TYPES = {"analysis_orchestrator", "analysis_provider", "execution_provider"}


def _registry_path(ws_root: Path) -> Path:
    return ws_root / ".providence" / "plugins" / "registry.yaml"


def _load_registry(ws_root: Path) -> dict[str, Any]:
    path = _registry_path(ws_root)
    if not path.exists():
        return {"schema_version": "1.0.0", "plugins": []}
    try:
        import yaml

        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {"schema_version": "1.0.0", "plugins": []}


def _strategist_active_base_path(ws_root: Path) -> str | None:
    active_path = ws_root / ".strategist" / "active.yaml"
    if not active_path.exists():
        return None
    try:
        import yaml

        payload = yaml.safe_load(active_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    base_path = payload.get("base_path")
    return str(base_path).strip() if base_path else None


def _validate_entry(entry: dict[str, Any], ws_root: Path | None = None) -> list[str]:
    violations: list[str] = []
    for field in _REQUIRED_FIELDS:
        if field not in entry:
            violations.append(f"missing field: {field}")
    plugin_type = entry.get("type", "")
    if plugin_type and plugin_type not in _KNOWN_TYPES:
        violations.append(f"unknown_plugin_type: {plugin_type!r}")
    injection = entry.get("sdd_injection", {})
    if isinstance(injection, dict):
        for inj_field in _REQUIRED_INJECTION_FIELDS:
            if inj_field not in injection:
                violations.append(f"missing sdd_injection field: {inj_field}")
        if entry.get("id") == "strategist" and ws_root is not None:
            injected_base = str(injection.get("base_path", "")).strip()
            active_base = _strategist_active_base_path(ws_root)
            if active_base and injected_base and active_base != injected_base:
                violations.append(
                    "strategist_base_path_mismatch: "
                    f"sdd_injection.base_path={injected_base} "
                    f"strategist.active.base_path={active_base}; "
                    "automatic delegation must block or use an explicit mapping"
                )
    return violations


@app.command("list")
def list_plugins(
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output"),
) -> None:
    """List all registered analysis provider plugins."""
    ws_root = resolve_workspace_root()
    if ws_root is None:
        typer.echo("Error: workspace root not found.", err=True)
        raise typer.Exit(1)

    registry = _load_registry(ws_root)
    plugins: list[dict[str, Any]] = registry.get("plugins", [])

    if _ctx_json() or json_output:
        emit_json({"command": "plugin list", "ok": True, "data": {"plugins": plugins}})
        return

    if not plugins:
        typer.echo("No plugins registered.")
        return

    header = f"{'ID':<20} {'TYPE':<22} {'VERSION':<10} {'STATUS'}"
    typer.echo(header)
    typer.echo("-" * 65)
    for p in plugins:
        typer.echo(
            f"{p.get('id', ''):<20} {p.get('type', ''):<22} {p.get('version', ''):<10} {p.get('status', '')}"
        )


@app.command("validate")
def validate_plugin(
    plugin_id: str = typer.Argument(..., help="Plugin id to validate"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output"),
) -> None:
    """Validate a plugin entry against analysis-provider.schema.yaml."""
    ws_root = resolve_workspace_root()
    if ws_root is None:
        typer.echo("Error: workspace root not found.", err=True)
        raise typer.Exit(1)

    registry = _load_registry(ws_root)
    plugins: list[dict[str, Any]] = registry.get("plugins", [])
    entry = next((p for p in plugins if p.get("id") == plugin_id), None)

    if entry is None:
        msg = f"Plugin '{plugin_id}' not found in registry."
        if _ctx_json() or json_output:
            emit_json(
                {
                    "command": "plugin validate",
                    "ok": False,
                    "data": {},
                    "error": {"code": "plugin_not_found", "message": msg},
                }
            )
        else:
            typer.echo(f"Error: {msg}", err=True)
        raise typer.Exit(1)

    violations = _validate_entry(entry, ws_root=ws_root)
    passed = len(violations) == 0

    if _ctx_json() or json_output:
        emit_json(
            {
                "command": "plugin validate",
                "ok": passed,
                "data": {
                    "plugin_id": plugin_id,
                    "result": "pass" if passed else "fail",
                    "violations": violations,
                },
            }
        )
        return

    if passed:
        typer.echo(f"pass  {plugin_id}")
    else:
        typer.echo(f"fail  {plugin_id}")
        for v in violations:
            typer.echo(f"  - {v}")
        raise typer.Exit(1)
