"""Governance gate and directive validation for SDD CLI profile enforcement."""

from __future__ import annotations

import click

from providence_cli.utils.profile_gate_directives import _collect_gate_directives

__all__ = [
    "_collect_gate_directives",
    "_GATE_EXEMPT_COMMANDS",
    "_extract_invocation",
    "_is_sensitive_command",
    "governance_gate",
]

# Commands that are exempt from governance gate (run before workspace init or to fix governance).
_GATE_EXEMPT_COMMANDS = frozenset(
    {"init", "bootstrap", "version", "help", "governance", "runtime"}
)


def _extract_invocation(ctx: click.Context) -> tuple[str, str]:
    """Best-effort extraction of command and subcommand names."""
    tokens = _raw_invocation_tokens(ctx)
    non_flag_tokens = [t for t in tokens if t and not t.startswith("-")]
    cmd = non_flag_tokens[0] if non_flag_tokens else ""
    subcmd = non_flag_tokens[1] if len(non_flag_tokens) > 1 else ""
    return cmd, subcmd


def _raw_invocation_tokens(ctx: click.Context) -> list[str]:
    """Best-effort extraction of all raw tokens (including flags) for this invocation."""
    import warnings

    raw_tokens: list[str] = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        protected_args = getattr(ctx, "protected_args", []) or []
    raw_tokens.extend(str(t) for t in protected_args)
    if isinstance(ctx.args, list):
        raw_tokens.extend(str(t) for t in ctx.args)
    return raw_tokens


def _is_informational_invocation(ctx: click.Context, invoked: str) -> bool:
    """True when the invocation is a pure listing/no-op that bypasses the gate.

    Covers `<cmd> --list` (informational, never touches governance) and a bare
    `<cmd>` with no arguments at all for sensitive commands like `ask`, which
    will fail its own required-argument validation (usage error) regardless of
    governance state  the gate must not preempt that with an unrelated
    governance message.
    """
    tokens = _raw_invocation_tokens(ctx)
    args_after_cmd = tokens[1:] if tokens and tokens[0] == invoked else tokens
    if "--list" in args_after_cmd:
        return True
    return invoked == "ask" and not args_after_cmd


def _is_sensitive_command(cmd: str, subcmd: str) -> bool:
    """Commands that require stronger SOFT governance directives."""
    if cmd in {"release", "wizard", "ask"}:
        return True
    return bool(cmd == "governance" and subcmd in {"compile", "generate"})


def governance_gate(ctx: click.Context) -> None:
    """Validate workspace governance state before command execution.

    Runs the AHP check (cached  fast on re-runs) and:
    - HEALTHY / PARTIAL   proceed silently
    - NOT_INITIALIZED     warn once, then proceed (setup may still be in progress)
    - MISCONFIGURED       warn with actionable message, then proceed
    - NOT_CONNECTED       skip silently (not an SDD workspace)

    Exempt commands (init, version) bypass this gate entirely.
    """
    invoked, subcommand = _extract_invocation(ctx)
    if invoked in _GATE_EXEMPT_COMMANDS:
        return
    if _is_informational_invocation(ctx, invoked):
        return

    try:
        import os
        import uuid

        from providence_runtime.telemetry import RuntimeEvent, TelemetrySink

        from providence_cli.services.ask_telemetry import enqueue_flush

        root = ctx.obj.get("root") if isinstance(ctx.obj, dict) else None
        profile = ctx.obj.get("profile", "") if isinstance(ctx.obj, dict) else ""
        cached_ahp = ctx.obj.get("_ahp") if isinstance(ctx.obj, dict) else None
        if isinstance(cached_ahp, dict):
            state = str(cached_ahp.get("state", "UNKNOWN"))
        else:
            from pathlib import Path

            from providence_core.governance.handshake import AgentHandshakeProtocol

            ahp = AgentHandshakeProtocol(project_root=Path(root) if root else None)
            state, _report = ahp.validate(output_mode="silent")

        # Determine logging mode based on profile (active for master, passive for client)
        logging_mode = "active" if profile == "master" else "passive"
        sink = TelemetrySink(logging_mode=logging_mode)

        sink.emit(
            RuntimeEvent(
                event="governance.checked",
                command=invoked,
                status="ok",
                trace_id=str(uuid.uuid4()),
                agent_id=os.environ.get("SDD_AGENT_ID", "unknown"),
                details={"state": state, "profile": profile},
            )
        )

        directives = _collect_gate_directives(
            invoked,
            subcommand,
            profile,
            state,
            _is_sensitive_command(invoked, subcommand),
        )

        from providence_cli.utils.output import is_json_mode

        json_mode = is_json_mode(ctx)
        for msg, next_step, reason in directives:
            is_hard = "HARD [governance]" in msg
            # Suppress SOFT warnings in JSON mode  they would corrupt machine-parseable output.
            if is_hard or not json_mode:
                click.echo(f"{msg} Next: {next_step}", err=True)
            sink.emit(
                RuntimeEvent(
                    event="governance.violation",
                    command=invoked,
                    status="fail" if is_hard else "warn",
                    trace_id=str(uuid.uuid4()),
                    agent_id=os.environ.get("SDD_AGENT_ID", "unknown"),
                    details={
                        "state": state,
                        "profile": profile,
                        "action": "block" if is_hard else "warn",
                        "required_next_step": next_step,
                        "reason": reason,
                        "subcommand": subcommand,
                    },
                )
            )
            enqueue_flush(sink)
            if is_hard:
                raise click.exceptions.Exit(1)

        enqueue_flush(sink)
        # HEALTHY / NOT_CONNECTED with no profile directive  silent
    except click.exceptions.Exit:
        raise
    except Exception as _exc:  # nosec B110
        # typer.Exit (and typer._click.exceptions.Exit) must propagate  hard-block exits
        # must not be silenced even when the broader exception handler is active.
        if type(_exc).__name__ == "Exit" and hasattr(_exc, "exit_code"):
            raise
        # Gate must never block legitimate commands due to import errors.
