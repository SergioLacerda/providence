#!/usr/bin/env python3
"""
SDD Security Demo — Bidirectional Handshake Failure (M015)

Shows SDD blocking agent bootstrap when the awakening profile is invalid.
M015 (Bidirectional Agent Handshake) requires every agent session to
present a well-formed profile before it is permitted to invoke any skill.

Three failure modes demonstrated:
  1. Missing required fields — profile dict is incomplete
  2. Invalid skill_set type — not a list
  3. Empty fallback_order — list present but empty (no fallback strategy)

A valid profile is shown at the end to confirm the happy path.

Run from repo root:
    uv run python examples/security/demo_handshake_failure.py
"""

from __future__ import annotations

from typing import Any

from providence_runtime import SkillContractError, validate_awakening_profile

SECTION = "\n" + "=" * 60

VALID_PROFILE: dict[str, Any] = {
    "activation_profile": "standard",
    "skill_set": ["sdd-ask", "sdd-validate-governance"],
    "fallback_order": ["sdd-ask"],
    "budget_policy": {"max_tokens": 50000, "max_cost_usd": 0.50},
    "escalation_policy": {"on_breach": "halt"},
    "validation_policy": {"require_fingerprint": True},
    "telemetry_policy": {"sink": "jsonl", "otel_enabled": False},
}


def attempt_handshake(label: str, profile: dict[str, Any]) -> None:
    print(f"\n[SDD] --- Scenario: {label} ---")
    try:
        result = validate_awakening_profile(profile)
        print(f"[SDD] HANDSHAKE OK — profile='{result.activation_profile}'")
        print(f"[SDD] Authorized skills  : {result.skill_set}")
        print(f"[SDD] Fallback order     : {result.fallback_order}")
        print("[SDD] Agent bootstrap permitted.")
    except SkillContractError as exc:
        print(f"[SDD] HANDSHAKE REJECTED — {exc}")
        print("[SDD] Agent bootstrap blocked. Governance enforced (M015).")


def main() -> None:
    print(SECTION)
    print("SDD Security — Bidirectional Handshake Failure Demo")
    print(SECTION)
    print(
        "\n[SDD] M015 requires a valid awakening profile before any skill execution.\n"
    )

    # Scenario 1: missing required fields
    attempt_handshake(
        "Missing fields (no budget_policy, escalation_policy, ...)",
        {
            "activation_profile": "partial",
            "skill_set": ["sdd-ask"],
        },
    )

    # Scenario 2: skill_set is not a list
    attempt_handshake(
        "Invalid type — skill_set is a string, not a list",
        {**VALID_PROFILE, "skill_set": "sdd-ask"},
    )

    # Scenario 3: empty fallback_order
    attempt_handshake(
        "Empty fallback_order (no recovery strategy)",
        {**VALID_PROFILE, "fallback_order": []},
    )

    # Scenario 4: valid profile — handshake succeeds
    attempt_handshake("Valid profile (happy path)", VALID_PROFILE)

    print(SECTION)


if __name__ == "__main__":
    main()
