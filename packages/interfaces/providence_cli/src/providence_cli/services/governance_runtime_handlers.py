"""Runtime-oriented governance command handlers (audit/handshake)."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from providence_cli.services.governance_payloads import (
    build_governance_audit_data,
    build_governance_handshake_completed_data,
    governance_error,
    governance_ok,
)
from providence_cli.utils.output import emit_json


def run_governance_audit(*, verbose: bool, output_json: bool, console: Console) -> None:
    """Execute governance audit flow with JSON/text output modes."""
    from providence_core.governance.audit import GovernanceAuditor

    auditor = GovernanceAuditor()
    report = auditor.perform_audit()

    if output_json:
        data = build_governance_audit_data(report)
        if report.ok:
            payload = governance_ok("governance audit", data)
        else:
            payload = governance_error(
                "governance audit",
                code="governance_audit_failed",
                message=f"Governance security audit failed with score {report.score}.",
                data=data,
            )
        emit_json(payload, err=not report.ok)
        return

    console.print(
        Panel(
            f"[bold cyan]Security Audit Report[/bold cyan]\nScore: [bold]{report.score}/100[/bold]",
            border_style="cyan" if report.ok else "red",
        )
    )

    if not report.issues:
        console.print("[green]No security issues found. System is hardened.[/green]")
    else:
        table = Table(title="Security Issues", show_header=True, header_style="bold")
        table.add_column("Severity", style="bold")
        table.add_column("Category")
        table.add_column("Issue")
        if verbose:
            table.add_column("Remediation")

        for issue in report.issues:
            sev_color = {
                "CRITICAL": "red",
                "HIGH": "bright_red",
                "MEDIUM": "yellow",
                "LOW": "blue",
            }.get(issue.severity, "white")

            row = [
                f"[{sev_color}]{issue.severity}[/{sev_color}]",
                issue.category,
                issue.message,
            ]
            if verbose:
                row.append(issue.remediation)
            table.add_row(*row)

        console.print(table)

    if not report.ok:
        console.print(f"\n[red]Veredito: BLOQUEADO (Score {report.score} < 70)[/red]")
        console.print("Corrija as vulnerabilidades crticas/altas antes de prosseguir.")
        raise typer.Exit(1)
    console.print(f"\n[green]Veredito: APROVADO (Score {report.score})[/green]")


def run_governance_handshake(
    *,
    response: str | None,
    init: bool,
    task_desc: str,
    output_mode: str,
    output_json: bool,
    console: Console,
) -> None:
    """Execute governance handshake flow with JSON/text output modes."""
    import json as _json

    from providence_core.governance.handshake import AgentHandshakeProtocol

    ahp = AgentHandshakeProtocol()

    if init:
        challenge = ahp.generate_challenge(task_description=task_desc)
        if output_json or output_mode == "silent":
            challenge_data = challenge.to_dict()
            payload = governance_ok("governance handshake", challenge_data)
            emit_json(payload)
        else:
            console.print(
                Panel(
                    f"[bold blue]SDD Handshake Challenge (M015)[/bold blue]\n\n"
                    f"Session ID: {challenge.session_id}\n"
                    f"Mandates: {', '.join(challenge.active_mandates)}\n"
                    f"Skills Available: {len(challenge.available_skills)}\n"
                    f"Signature Status: {challenge.signature_status}\n\n"
                    f"[yellow]Copy the following JSON and provide it to the agent:[/yellow]"
                )
            )
            console.print(_json.dumps(challenge.to_dict(), indent=2))
        return

    if response is None:
        console.print("[red]ERROR: --response or --init is required.[/red]")
        raise typer.Exit(1)

    try:
        response_data = _json.loads(response)
    except _json.JSONDecodeError as exc:
        console.print(f"[red]ERROR: invalid JSON response: {exc}[/red]")
        raise typer.Exit(1) from exc

    ahp = AgentHandshakeProtocol()
    ahp.validate(output_mode="silent")
    result = ahp.complete_handshake(response_data)

    if output_json or output_mode == "silent":
        data = build_governance_handshake_completed_data(result)
        payload = governance_ok("governance handshake", data)
        emit_json(payload)
        return

    console.print(
        Panel(
            f"[green]Handshake Response Registered[/green]\n\n"
            f"Agent ID: {result.agent_id}\n"
            f"Skills declared: {', '.join(result.skills_to_use) or 'none'}\n"
            f"Signature Acknowledged: {'[green]Yes[/green]' if result.acknowledged_signature else '[red]No[/red]'}\n"
            f"Compliance Declaration: {'[green]Yes[/green]' if result.compliance_declaration else '[red]No[/red]'}",
            title="SDD Governance Handshake",
        )
    )
