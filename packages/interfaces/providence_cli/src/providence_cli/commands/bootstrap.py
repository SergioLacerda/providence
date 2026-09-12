"""sdd bootstrap  initialize/refresh local runtime bootstrap state."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import typer

from providence_cli.services.command_group_output import show_command_group

app = typer.Typer(invoke_without_command=True)


@app.callback(invoke_without_command=True)
def _(
    ctx: typer.Context,
    list_commands: bool = typer.Option(
        False, "--list", help="List bootstrap commands."
    ),
) -> None:
    """Bootstrap workspace runtime state."""
    if list_commands or ctx.invoked_subcommand is None:
        show_command_group("Bootstrap", ["run"])
        raise typer.Exit(0)


def _read_json(path: Path) -> dict[str, object]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    normalized = ts.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@app.command("run")
def run(
    session_guard_hours: int = typer.Option(
        4,
        "--session-guard-hours",
        min=1,
        help="Minimum hours before forcing bootstrap refresh with same fingerprint.",
    ),
) -> None:
    """Create/update `.providence/runtime/bootstrap-state.json` with governance fingerprint."""
    try:
        from providence_core.utils.environment import find_workspace_root
    except ImportError as exc:
        typer.echo(f"ERROR: providence_core not installed  {exc}", err=True)
        raise typer.Exit(2) from exc

    root = find_workspace_root() or Path.cwd()
    metadata_path = root / ".providence" / "metadata.json"
    governance_path = root / ".providence" / "source" / "governance-core.json"
    state_path = root / ".providence" / "runtime" / "bootstrap-state.json"

    if not metadata_path.exists() or not governance_path.exists():
        typer.echo(
            "ERROR: bootstrap requires `.providence/metadata.json` and `.providence/source/governance-core.json`.",
            err=True,
        )
        raise typer.Exit(1)

    metadata = _read_json(metadata_path)
    governance = _read_json(governance_path)
    version = str(metadata.get("version", "unknown"))
    mandates_count_raw = metadata.get("mandates_count")
    if isinstance(mandates_count_raw, int | str):
        mandates_count = int(mandates_count_raw)
    else:
        items = governance.get("items")
        mandates_count = len(items) if isinstance(items, list) else 0

    metadata_fp = metadata.get("spec_fingerprint")
    governance_spec_fp = governance.get("spec_fingerprint")
    governance_fp = governance.get("fingerprint")
    fingerprint = next(
        (
            val
            for val in (metadata_fp, governance_spec_fp, governance_fp)
            if isinstance(val, str) and val
        ),
        "unknown",
    )

    previous = _read_json(state_path) if state_path.exists() else {}
    now = datetime.now(timezone.utc)
    last_success_raw = previous.get("last_success_at")
    last_run = _parse_iso(
        last_success_raw if isinstance(last_success_raw, str) else None
    )
    guard_ok = False
    if last_run is not None and previous.get("governance_fingerprint") == fingerprint:
        guard_ok = now - last_run < timedelta(hours=session_guard_hours)
    if guard_ok:
        typer.echo(
            "bootstrap up-to-date "
            f"(version={version}, mandates={mandates_count}, "
            f"fingerprint={fingerprint}, guard={session_guard_hours}h)"
        )
        return

    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1",
        "workspace_root": str(root),
        "governance_fingerprint": fingerprint,
        "last_success_at": now.isoformat().replace("+00:00", "Z"),
        "session_guard_hours": session_guard_hours,
        "source": "sdd bootstrap run",
    }
    state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    typer.echo(
        "bootstrap updated "
        f"(version={version}, mandates={mandates_count}, "
        f"fingerprint={fingerprint}, file={state_path.relative_to(root)})"
    )
