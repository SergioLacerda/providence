"""Public wizard contracts and canonical invocation boundary."""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast


@dataclass(frozen=True)
class WizardInvocation:
    """Canonical invocation payload for the wizard."""

    project_root: Path
    non_interactive: bool = False
    output_path: Path | None = None
    language: str = "python"
    custom_governance_path: Path | None = None
    """Scenario B trigger: a user-supplied mandates/guidelines JSON file.

    When set, the wizard validates and loads this file instead of generating
    a fresh governance set from markdown templates (Phase 1-3 is bypassed).
    """
    debug: bool = False
    """Show full verbose wizard output instead of the quiet macro summary."""


@dataclass(frozen=True)
class GeneratedManifest:
    """Minimal generated artifact summary."""

    files: list[Path]
    mandates_count: int
    guidelines_count: int
    categories: list[str]


@dataclass(frozen=True)
class WizardResult:
    """Canonical wizard execution result."""

    success: bool
    manifest: GeneratedManifest | None = None
    errors: list[str] = field(default_factory=list)


def run_wizard(invocation: WizardInvocation) -> WizardResult:
    """Run the wizard through the canonical application boundary."""
    module = importlib.import_module("providence_wizard.application.session_bootstrap")
    session_bootstrap_cls = module.SessionBootstrap
    return cast(WizardResult, session_bootstrap_cls(invocation).run())


def generate_agent_instructions_from_config(
    output_base: Path,
    config: dict[str, Any],
) -> bool:
    """Regenerate .providence/agent-instructions.md from a governance config dict."""
    from providence_wizard.orchestration.seedlings.governance_seeds import (
        generate_agent_instructions_from_config as _impl,
    )

    return _impl(output_base, config)


def generate_root_bootstrap_from_config(
    output_base: Path,
    config: dict[str, Any],
) -> bool:
    """Regenerate root bootstrap files from a governance config dict."""
    from providence_wizard.orchestration.seedlings.governance_seeds import (
        generate_root_bootstrap_from_config as _impl,
    )

    return _impl(output_base, config)
