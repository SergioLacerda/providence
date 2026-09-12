"""Governed intake — entrypoint resolution.

Relocated from `providence_cli.services.ask_response_intake`
(`.analysis/pending/20260907-backend-governance-reorg-refinement`, Fase 1).
"""

from __future__ import annotations

import os

# Env var set by the prompt-submit hook when it invokes `providence ask` on the
# agent's behalf. Any other invocation path (direct CLI use, or the slash
# command adapter's own `providence ask` call) is a deliberate/explicit invocation.
ASK_ENTRYPOINT_ENV = "SDD_ASK_ENTRYPOINT"


def resolve_ask_entrypoint() -> tuple[str, str | None]:
    """Resolve (entrypoint, explicit_command) from how `providence ask` was invoked.

    Returns ``("hook", None)`` only when the prompt-submit hook set
    ``SDD_ASK_ENTRYPOINT=hook`` before calling `providence ask`. Every other call —
    a human typing `providence ask` directly, or the slash-command adapter running
    its own explicit invocation — is treated as ``("explicit_command",
    "sdd-ask")``.
    """
    if os.environ.get(ASK_ENTRYPOINT_ENV, "").strip().casefold() == "hook":
        return "hook", None
    return "explicit_command", "sdd-ask"
