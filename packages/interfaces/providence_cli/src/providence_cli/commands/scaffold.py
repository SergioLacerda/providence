"""Scaffold command  generate new skills and commands from canonical templates."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Annotated

import typer
from jinja2 import (
    Environment,
    FileSystemLoader,
    select_autoescape,
)

from providence_cli.commands.scaffold_registry import _append_to_registry
from providence_cli.services.command_group_output import show_command_group
from providence_core.utils.environment import find_workspace_root

app = typer.Typer(
    help="Scaffold new Providence skills and commands from canonical templates.",
    invoke_without_command=True,
)


@app.callback(invoke_without_command=True)
def scaffold_default(
    ctx: typer.Context,
    list_commands: bool = typer.Option(False, "--list", help="List scaffold commands."),
) -> None:
    """Scaffold new Providence skills and commands."""
    if list_commands or ctx.invoked_subcommand is None:
        show_command_group("Scaffold", ["skill", "command"])
        raise typer.Exit(0)


_RISK_SCORES = ["low", "medium", "high", "critical", "controlled"]
_TOKEN_BUDGETS = {
    "low": "low",
    "medium": "medium",
    "high": "medium",
    "critical": "high",
    "controlled": "medium",
}
_CATEGORIES = [
    "analysis",
    "architecture",
    "convergence",
    "correction",
    "economy",
    "governance",
    "operations",
    "orchestrator",
]


def _get_templates_dir(ws_root: Path) -> Path:
    return ws_root / ".providence" / "templates"


def _render(template_path: Path, context: Mapping[str, object]) -> str:
    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        autoescape=select_autoescape(enabled_extensions=["html", "xml"]),
        keep_trailing_newline=True,
    )
    return str(env.get_template(template_path.name).render(**context))


@app.command()
def skill(
    name: Annotated[str, typer.Argument(help="Skill name (kebab-case)")],
    category: Annotated[
        str, typer.Option(help=f"Skill category: {', '.join(_CATEGORIES)}")
    ] = "operations",
    risk: Annotated[
        str, typer.Option(help="Risk score: low | medium | high | critical")
    ] = "low",
    description: Annotated[str, typer.Option(help="One-line skill description")] = "",
    when_to_use: Annotated[
        str, typer.Option(help="Primary trigger phrase")
    ] = "when needed",
) -> None:
    """Scaffold a new SDD skill from the canonical template."""
    if risk not in _RISK_SCORES:
        typer.echo(f"ERROR: --risk must be one of {_RISK_SCORES}", err=True)
        raise typer.Exit(1)

    ws_root = find_workspace_root()
    if ws_root is None:
        typer.echo(
            "ERROR: Not inside an SDD workspace (.providence/ not found)", err=True
        )
        raise typer.Exit(1)

    templates_dir = _get_templates_dir(ws_root)
    if not (templates_dir / "skill").exists():
        typer.echo(f"ERROR: Templates not found at {templates_dir}/skill/", err=True)
        raise typer.Exit(1)

    skill_dir = ws_root / ".providence" / "skills" / name
    if skill_dir.exists():
        typer.echo(f"ERROR: Skill '{name}' already exists at {skill_dir}", err=True)
        raise typer.Exit(1)

    skill_dir.mkdir(parents=True)

    context = {
        "name": name,
        "category": category,
        "risk_score": risk,
        "token_budget": _TOKEN_BUDGETS.get(risk, "medium"),
        "description": description or f"{name.replace('-', ' ').title()} skill.",
        "when_to_use_0": when_to_use,
    }

    (skill_dir / "skill.yaml").write_text(
        _render(templates_dir / "skill" / "skill.yaml.tpl", context), encoding="utf-8"
    )
    (skill_dir / "SKILL.md").write_text(
        _render(templates_dir / "skill" / "SKILL.md.tpl", context), encoding="utf-8"
    )

    registry_path = ws_root / ".providence" / "skills" / "registry.json"
    _append_to_registry(
        registry_path, {"name": name, "description": context["description"]}
    )

    typer.echo(f" Skill '{name}' created at {skill_dir}")
    typer.echo(f"   {skill_dir}/skill.yaml")
    typer.echo(f"   {skill_dir}/SKILL.md")
    typer.echo("   registry.json updated")
    typer.echo(
        f"\nNext: run 'sdd scaffold command {name} --routes-to {name}' to create a slash command"
    )


@app.command()
def command(
    name: Annotated[
        str, typer.Argument(help="Command name (kebab-case, becomes /name)")
    ],
    routes_to: Annotated[
        str, typer.Option(help="Skill ID this command routes to")
    ] = "",
) -> None:
    """Scaffold a new SDD slash command from the canonical template."""
    skill_id = routes_to or name

    ws_root = find_workspace_root()
    if ws_root is None:
        typer.echo(
            "ERROR: Not inside an SDD workspace (.providence/ not found)", err=True
        )
        raise typer.Exit(1)

    templates_dir = _get_templates_dir(ws_root)
    if not (templates_dir / "command").exists():
        typer.echo(f"ERROR: Templates not found at {templates_dir}/command/", err=True)
        raise typer.Exit(1)

    cmd_dir = ws_root / ".providence" / "commands" / name
    if cmd_dir.exists():
        typer.echo(f"ERROR: Command '{name}' already exists at {cmd_dir}", err=True)
        raise typer.Exit(1)

    cmd_dir.mkdir(parents=True)

    context = {"name": name, "skill_id": skill_id}
    (cmd_dir / "command.yaml").write_text(
        _render(templates_dir / "command" / "command.yaml.tpl", context),
        encoding="utf-8",
    )

    registry_path = ws_root / ".providence" / "commands" / "registry.json"
    _append_to_registry(
        registry_path,
        {
            "id": name,
            "slash": f"/{name}",
            "routes_to": {"type": "skill", "id": skill_id},
            "targets": ["claude", "codex", "copilot", "antigravity"],
        },
    )

    typer.echo(f" Command '/{name}' created at {cmd_dir}")
    typer.echo(f"   {cmd_dir}/command.yaml")
    typer.echo("   registry.json updated")
