"""Independent workspace settings with legacy profile defaults."""

from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkspaceSettings:
    """Operation capabilities, artifact identity and audit persistence policy."""

    capabilities: frozenset[str]
    artifact_target: str
    audit_mode: str


def resolve_workspace_settings(root: Path, profile: str) -> WorkspaceSettings:
    """Resolve explicit settings without changing legacy artifact wire values."""
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(root / ".providence" / "profile", encoding="utf-8")
    section = parser["workspace"] if parser.has_section("workspace") else {}
    unknown = set(section) - {"capabilities", "artifact_target", "audit_mode"}
    if unknown:
        raise ValueError(f"Unknown workspace settings: {sorted(unknown)}")
    target = section.get("artifact_target", profile).strip()
    audit = section.get(
        "audit_mode", "active" if profile == "master" else "passive"
    ).strip()
    defaults = "consume,author,publish" if profile == "master" else "consume"
    capabilities = frozenset(
        part.strip()
        for part in section.get("capabilities", defaults).split(",")
        if part.strip()
    )
    if target not in {"master", "client"}:
        raise ValueError("workspace.artifact_target must be master or client")
    if audit not in {"passive", "active", "strict"}:
        raise ValueError("workspace.audit_mode must be passive, active or strict")
    if not capabilities or capabilities - {"consume", "author", "publish"}:
        raise ValueError(
            "workspace.capabilities must contain consume, author or publish"
        )
    if "publish" in capabilities and "author" not in capabilities:
        raise ValueError("workspace publish capability requires author")
    return WorkspaceSettings(capabilities, target, audit)
