"""Governance footer formatting for skill execution results."""

from __future__ import annotations

from .profile_labels import resolve_profile_label


def format_governance_footer(
    *,
    drift: str,
    governance: str,
    profile: str,
    root_seed_drift: str | None = None,
) -> str:
    """Build the canonical compact governance footer.

    `profile` is resolved through `resolve_profile_label` so legacy `sdd-*`
    skill/route ids render as Providence-branded display labels without
    renaming the underlying registry id (see ADR-018).

    `root_seed_drift` is a separate, optional field — distinct from `drift`
    (which reflects in-session cached-state drift). It is only appended when
    explicitly provided, so existing callers are unaffected.
    """
    label = resolve_profile_label(profile)
    footer = f"PROVIDENCE GOVERNANCE: drift={drift} | governance={governance} | profile={label}"
    if root_seed_drift is not None:
        footer += f" | root_seed_drift={root_seed_drift}"
    return footer
