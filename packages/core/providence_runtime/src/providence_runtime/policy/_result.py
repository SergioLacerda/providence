"""PolicyResult dataclass and severity/decision constants."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# Severity levels for policy violations.
SEVERITY_HARD = "hard"  # fail closed — blocks execution
SEVERITY_SOFT = "soft"  # warn — allows execution with guidance
SEVERITY_NONE = "none"  # no action required

# Policy decision types for skill enforcement
SkillPolicyDecision = Literal["allow", "block", "warn"]


@dataclass
class PolicyResult:
    """Result of a policy evaluation."""

    allowed: bool
    severity: str  # hard | soft | none
    reason: str
    remediation: str = ""
