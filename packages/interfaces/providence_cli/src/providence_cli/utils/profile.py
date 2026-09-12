"""Profile-aware policy adapters for SDD CLI commands (re-export module).

Provides MasterAdapter and ClientAdapter that encode which operations are
permitted in each workspace context, along with helpers to retrieve the
active profile from Click context.
"""

from providence_cli.utils.profile_loader import (  # noqa: F401
    _ADAPTERS,
    ClientAdapter,
    MasterAdapter,
    ProfilePolicy,
    enforce_profile_policy,
    get_active_profile,
    get_adapter,
    profile_context_display,
)
from providence_cli.utils.profile_validator import (  # noqa: F401
    _GATE_EXEMPT_COMMANDS,
    _collect_gate_directives,
    _extract_invocation,
    _is_sensitive_command,
    governance_gate,
)

__all__ = [
    "_ADAPTERS",
    "ClientAdapter",
    "MasterAdapter",
    "ProfilePolicy",
    "enforce_profile_policy",
    "get_active_profile",
    "get_adapter",
    "profile_context_display",
    "_GATE_EXEMPT_COMMANDS",
    "_collect_gate_directives",
    "_extract_invocation",
    "_is_sensitive_command",
    "governance_gate",
]
