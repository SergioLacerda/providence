#!/usr/bin/env python3
"""
SDD Security Demo — Artifact Missing / Corrupt

Shows three pre-flight failure modes that SDD catches before any agent
execution begins:
  1. Artifact file not found (missing .providence/metadata.json)
  2. Artifact with unsupported / future schema version (corrupt/upgraded artifact)
  3. Artifact with empty fingerprint (incomplete compilation)

All three are caught by PolicyEngine.validate_preflight() or SchemaValidator
before any tool call or crew kickoff.

Run from repo root:
    uv run python examples/security/demo_artifact_missing.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from providence_runtime import (
    CompiledArtifact,
    PolicyEngine,
    SchemaValidator,
    SessionState,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
METADATA_PATH = REPO_ROOT / ".providence" / "metadata.json"
SECTION = "\n" + "=" * 60


def load_real_artifact() -> CompiledArtifact:
    raw = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    return CompiledArtifact(
        artifact_version=raw["version"],
        schema_version=raw["version"],
        fingerprint=raw["fingerprints"]["combined"],
        generated_at=raw.get("generated_at", ""),
        profile=raw.get("adoption_level", "FULL"),
    )


def preflight(label: str, artifact: CompiledArtifact, session: SessionState) -> None:
    print(f"\n[SDD] --- Scenario: {label} ---")
    engine = PolicyEngine()
    result = engine.validate_preflight(
        artifact=artifact,
        session=session,
        current_profile="FULL",
    )
    if not result.allowed:
        print(f"[SDD] BLOCKED  severity={result.severity}  reason={result.reason}")
        print(f"[SDD] Remediation : {result.remediation}")
        print("[SDD] Agent execution prevented.")
    else:
        print("[SDD] ALLOWED  — preflight passed.")


def schema_check(label: str, artifact: CompiledArtifact) -> None:
    print(f"\n[SDD] --- Scenario: {label} ---")
    validator = SchemaValidator()
    result = validator.validate_artifact(artifact)
    if not result.compatible:
        print(f"[SDD] SCHEMA INCOMPATIBLE  reason={result.reason}")
        print(f"[SDD] Remediation : {result.remediation}")
        print("[SDD] Agent execution prevented.")
    else:
        print(f"[SDD] Schema OK  version={result.artifact_version}")


def main() -> None:
    print(SECTION)
    print("SDD Security — Artifact Missing / Corrupt Demo")
    print(SECTION)

    if not METADATA_PATH.exists():
        print("[SDD] ERROR: .providence/metadata.json not found. Run from repo root.")
        sys.exit(1)

    real_artifact = load_real_artifact()
    clean_session = SessionState(
        workspace_id="demo",
        agent_id="demo-agent",
        work_item_id="demo-task",
        artifact_fingerprint=real_artifact.fingerprint,
        schema_version=real_artifact.schema_version,
        policy_set_version=real_artifact.schema_version,
    )

    # ── Scenario 1: artifact file missing (simulate by empty fingerprint + no-artifact policy) ──
    missing_artifact = CompiledArtifact(
        artifact_version="",
        schema_version="",
        fingerprint="",
        generated_at="",
        profile="client",
    )
    preflight(
        "Artifact with empty fingerprint (missing compile)",
        missing_artifact,
        clean_session,
    )

    # ── Scenario 2: schema version unrecognised (future/corrupt artifact) ──
    future_artifact = CompiledArtifact(
        artifact_version="99.0",
        schema_version="99.0",
        fingerprint=real_artifact.fingerprint,
        generated_at="",
        profile="client",
    )
    schema_check(
        "Unknown schema version '99.0' (corrupt/future artifact)", future_artifact
    )

    # ── Scenario 3: artifact present but session carries tampered fingerprint ──
    tampered_session = SessionState(
        workspace_id="demo",
        agent_id="demo-agent",
        work_item_id="demo-task",
        artifact_fingerprint="c0ffee0000000000",
        schema_version=real_artifact.schema_version,
        policy_set_version=real_artifact.schema_version,
    )
    preflight(
        "Valid artifact, tampered session fingerprint", real_artifact, tampered_session
    )

    # ── Scenario 4: everything clean — execution permitted ──
    preflight(
        "Clean state (valid artifact + matching fingerprint)",
        real_artifact,
        clean_session,
    )

    print(SECTION)


if __name__ == "__main__":
    main()
