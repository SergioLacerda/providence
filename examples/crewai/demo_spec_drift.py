#!/usr/bin/env python3
"""
CrewAI Demo — SDD Spec Drift Detection

Shows SDD detecting a tampered governance fingerprint before a CrewAI crew
executes. The crew is initialized but never kicked off when drift is found.

Run from repo root:
    uv run --extra examplescrewai python examples/crewai/demo_spec_drift.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from providence_runtime import DriftDetector

try:
    from crewai import Agent, Crew, Task

    _CREWAI_AVAILABLE = True
except Exception:
    _CREWAI_AVAILABLE = False

REPO_ROOT = Path(__file__).resolve().parents[2]
METADATA_PATH = REPO_ROOT / ".providence" / "metadata.json"

SECTION = "\n" + "=" * 60


def load_fingerprint() -> tuple[str, str]:
    """Return (fingerprint, schema_version) from the compiled artifact."""
    raw = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    return raw["fingerprints"]["combined"], raw["version"]


# ─── Main ─────────────────────────────────────────────────────────────────


def main() -> None:
    print(SECTION)
    print("SDD + CrewAI — Spec Drift Detection Demo")
    print(SECTION)

    if not _CREWAI_AVAILABLE:
        print("\n[CrewAI] WARNING: crewai could not be imported (dependency issue).")
        print("[CrewAI] The SDD drift detection below runs regardless.\n")

    # 1. Load the real governance fingerprint
    print("\n[SDD] Loading governance artifact fingerprint...")
    if not METADATA_PATH.exists():
        print("[SDD] ERROR: .providence/metadata.json not found. Run from repo root.")
        sys.exit(1)

    artifact_fingerprint, schema_version = load_fingerprint()
    print(f"[SDD] Artifact fingerprint (expected) : {artifact_fingerprint}")

    # 2. Initialize CrewAI crew (does NOT execute yet)
    if _CREWAI_AVAILABLE:
        print("\n[CrewAI] Initializing crew...")
        analyst = Agent(
            role="Governance Analyst",
            goal="Analyze spec compliance",
            backstory="Expert in SDD governance contracts.",
            verbose=False,
        )
        task = Task(
            description="Verify that the current governance spec is clean.",
            expected_output="A compliance verdict.",
            agent=analyst,
        )
        crew = Crew(agents=[analyst], tasks=[task], verbose=False)
        print(
            f"[CrewAI] Crew initialized — agents={len(crew.agents)}, tasks={len(crew.tasks)}"
        )
    else:
        crew = None
        print(
            "\n[CrewAI] Crew skipped (not available) — SDD gate is framework-agnostic."
        )

    # 3. Simulate drift: session was bound to a stale fingerprint
    stale_fingerprint = "deadbeef00000000"
    print(f"\n[SDD] Session fingerprint (stale/tampered) : {stale_fingerprint}")
    print(f"[SDD] Artifact fingerprint (expected)      : {artifact_fingerprint}")

    # 4. SDD drift check — runs BEFORE crew.kickoff()
    print("\n[SDD] Running drift detection check...")
    detector = DriftDetector()
    report = detector.detect(
        session_fingerprint=stale_fingerprint,
        artifact_fingerprint=artifact_fingerprint,
    )

    if report.drift_detected:
        print(f"\n[SDD] DRIFT_DETECTED — type={report.drift_type}")
        print(f"[SDD] Details      : {report.details}")
        print(f"[SDD] Remediation  : {report.remediation_command}")
        print("\n[SDD] Crew kickoff prevented. Governance enforced.")
        print("[SDD] Run the remediation command above to recompile the artifact.")
        print(SECTION)
        sys.exit(0)

    # 5. Only reached when fingerprints match (clean state)
    print("\n[SDD] No drift detected — crew execution permitted.")
    if crew is not None:
        result = crew.kickoff()
        print(f"[CrewAI] Result: {result}")
    print(SECTION)


if __name__ == "__main__":
    main()
