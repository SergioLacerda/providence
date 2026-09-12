#!/usr/bin/env python3
"""
SDD — Drift Accuracy Battery

A deterministic regression harness for governance drift detection.
Run before and after implementing a feature to measure impact on drift accuracy.

How it works:
  1. Loads the REAL current artifact fingerprint (.providence/metadata.json)
  2. Runs a fixed, deterministic battery of 100 sessions:
       - 70 CLEAN  : carry the current artifact fingerprint (must not drift)
       - 15 STALE  : carry the fingerprint saved from the LAST run (drift if artifact changed)
       - 10 MISSING: carry empty fingerprint (must always drift)
       - 5  CORRUPT: carry a known-bad fingerprint (must always drift)
  3. Computes accuracy metrics (TP, FP, detection rate, false positive rate)
  4. Saves a snapshot to drift_battery_snapshot.json
  5. If a previous snapshot exists, prints a delta report

Usage:
    # First run — establishes baseline
    uv run python examples/security/drift_battery.py

    # After implementing a new feature / recompiling artifact:
    uv run python examples/security/drift_battery.py

    # With a label to identify the run:
    uv run python examples/security/drift_battery.py --label "after-auth-refactor"

    # Save snapshot to a custom path:
    uv run python examples/security/drift_battery.py --snapshot path/to/snap.json

Run from repo root.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from providence_runtime import CompiledArtifact, DriftDetector, SessionState

REPO_ROOT = Path(__file__).resolve().parents[2]
METADATA_PATH = REPO_ROOT / ".providence" / "metadata.json"
DEFAULT_SNAP = REPO_ROOT / "examples" / "security" / "drift_battery_snapshot.json"

SECTION = "\n" + "=" * 60

# ── Fixed battery composition (deterministic, no randomness) ─────────────
BATTERY = {
    "clean": 70,  # sessions carrying the CURRENT fingerprint → must be CLEAN
    "stale": 15,  # sessions carrying the PREVIOUS fingerprint → drift if artifact changed
    "missing": 10,  # empty fingerprint → always MISSING drift
    "corrupt": 5,  # known-bad fingerprint → always MISMATCH drift
}
TOTAL = sum(BATTERY.values())  # 100

# Intentional drift scenarios (stale becomes clean if artifact unchanged)
ALWAYS_DRIFT = BATTERY["missing"] + BATTERY["corrupt"]  # 15 — unconditional
STALE_COUNT = BATTERY["stale"]  # 15 — conditional on artifact change


# ── Data types ────────────────────────────────────────────────────────────


@dataclass
class BatteryResult:
    label: str
    timestamp: str
    artifact_fp: str
    schema_version: str

    # Raw counts
    total: int
    true_positives: int  # intentional drift correctly detected
    false_positives: int  # clean sessions incorrectly flagged as drift
    stale_drifted: int  # stale sessions that drifted (0 = artifact unchanged)

    # Derived metrics
    detection_rate: float  # TP / expected_drift  — should be 1.0 always
    false_pos_rate: float  # FP / clean_sessions  — should be 0.0 always
    drift_rate: float  # total_drifted / total — changes when artifact changes

    # Artifact changed since last snapshot?
    artifact_changed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Helpers ───────────────────────────────────────────────────────────────


def load_artifact() -> CompiledArtifact:
    raw = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    return CompiledArtifact(
        artifact_version=raw["version"],
        schema_version=raw["version"],
        fingerprint=raw["fingerprints"]["combined"],
        generated_at=raw.get("generated_at", ""),
        profile=raw.get("adoption_level", "FULL"),
    )


def make_session(fp: str, artifact: CompiledArtifact) -> SessionState:
    return SessionState(
        workspace_id="battery",
        agent_id="battery-agent",
        work_item_id="battery-task",
        artifact_fingerprint=fp,
        schema_version=artifact.schema_version,
        policy_set_version=artifact.schema_version,
    )


def load_snapshot(path: Path) -> dict[str, Any] | None:
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else None
    return None


def save_snapshot(result: BatteryResult, path: Path) -> None:
    path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")


# ── Core battery runner ───────────────────────────────────────────────────


def run_battery(
    artifact: CompiledArtifact,
    previous_fp: str | None,
    label: str,
) -> BatteryResult:
    detector = DriftDetector()

    # Use previous fingerprint for stale sessions; fall back to a synthetic one
    # if this is the first run (no previous snapshot).
    stale_fp = previous_fp if previous_fp else "00000000stale000"
    corrupt_fp = "deadbeefcafebabe"

    sessions: list[tuple[str, str]] = (
        [(artifact.fingerprint, "clean")] * BATTERY["clean"]
        + [(stale_fp, "stale")] * BATTERY["stale"]
        + [("", "missing")] * BATTERY["missing"]
        + [(corrupt_fp, "corrupt")] * BATTERY["corrupt"]
    )

    true_positives = 0
    false_positives = 0
    stale_drifted = 0

    for fp, category in sessions:
        session = make_session(fp, artifact)
        report = detector.detect(
            session_fingerprint=session.artifact_fingerprint,
            artifact_fingerprint=artifact.fingerprint,
        )
        drifted = report.drift_detected

        if category == "clean":
            if drifted:
                false_positives += 1
        elif category == "stale":
            if drifted:
                stale_drifted += 1
                true_positives += 1
        else:  # missing / corrupt — always expected to drift
            if drifted:
                true_positives += 1

    total_drifted = true_positives + false_positives
    expected_always = ALWAYS_DRIFT
    expected_drift = expected_always + stale_drifted  # stale only if changed
    detection_rate = true_positives / max(expected_drift, 1)
    false_pos_rate = false_positives / BATTERY["clean"]
    drift_rate = total_drifted / TOTAL

    artifact_changed = previous_fp is not None and previous_fp != artifact.fingerprint

    return BatteryResult(
        label=label,
        timestamp=datetime.now(timezone.utc).isoformat(),
        artifact_fp=artifact.fingerprint,
        schema_version=artifact.schema_version,
        total=TOTAL,
        true_positives=true_positives,
        false_positives=false_positives,
        stale_drifted=stale_drifted,
        detection_rate=detection_rate,
        false_pos_rate=false_pos_rate,
        drift_rate=drift_rate,
        artifact_changed=artifact_changed,
    )


# ── Delta report ──────────────────────────────────────────────────────────


def print_delta(current: BatteryResult, previous: dict[str, Any]) -> None:
    prev_drift = previous["drift_rate"]
    prev_fp = previous["artifact_fp"]
    prev_label = previous.get("label", "previous")
    prev_ts = previous.get("timestamp", "?")

    delta_drift = current.drift_rate - prev_drift
    delta_symbol = "▲" if delta_drift > 0 else ("▼" if delta_drift < 0 else "=")
    delta_sign = (
        f"+{delta_drift * 100:.2f}pp"
        if delta_drift >= 0
        else f"{delta_drift * 100:.2f}pp"
    )

    print("\n[Battery] --- Delta vs previous run ---")
    print(f"[Battery] Previous label     : {prev_label}")
    print(f"[Battery] Previous timestamp : {prev_ts}")
    print(f"[Battery] Previous artifact  : {prev_fp}")
    print(f"[Battery] Current  artifact  : {current.artifact_fp}")

    fp_status = "CHANGED ⚠" if current.artifact_changed else "unchanged ✓"
    print(f"[Battery] Artifact state     : {fp_status}")

    print(
        f"\n[Battery] Drift rate         : {prev_drift * 100:.2f}%  →  {current.drift_rate * 100:.2f}%  "
        f"({delta_symbol} {delta_sign})"
    )
    print(
        f"[Battery] Detection rate     : {previous['detection_rate'] * 100:.1f}%  →  "
        f"{current.detection_rate * 100:.1f}%"
    )
    print(
        f"[Battery] False positive rate: {previous['false_pos_rate'] * 100:.1f}%  →  "
        f"{current.false_pos_rate * 100:.1f}%"
    )

    # Verdict
    print("\n[Battery] --- Impact assessment ---")
    if abs(delta_drift) < 0.02 and not current.artifact_changed:
        print(
            f"[Battery] NEUTRAL — drift rate stable ({delta_sign}). No governance impact detected."
        )
    elif current.artifact_changed and current.stale_drifted > 0:
        print(
            f"[Battery] ARTIFACT CHANGED — {current.stale_drifted} stale sessions now drift."
        )
        print("[Battery]   This is expected after providence governance compile.")
        print(
            f"[Battery]   Drift rate increase: {delta_sign} — sessions need fingerprint refresh."
        )
    elif delta_drift > 0.02:
        print(f"[Battery] REGRESSION ⚠ — drift rate increased by {delta_sign}.")
        print(
            "[Battery]   Investigate: new feature may have introduced governance drift."
        )
    elif delta_drift < -0.02:
        print(
            f"[Battery] IMPROVEMENT ✓ — drift rate decreased by {abs(delta_drift) * 100:.2f}pp."
        )


# ── Main ──────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="SDD drift accuracy battery")
    parser.add_argument(
        "--label",
        type=str,
        default="manual-run",
        help="Label for this run (e.g. 'before-auth-refactor')",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=DEFAULT_SNAP,
        help="Path to snapshot file (default: drift_battery_snapshot.json)",
    )
    args = parser.parse_args()

    print(SECTION)
    print("SDD — Drift Accuracy Battery")
    print(SECTION)

    if not METADATA_PATH.exists():
        print(
            "[Battery] ERROR: .providence/metadata.json not found. Run from repo root."
        )
        sys.exit(1)

    artifact = load_artifact()
    previous = load_snapshot(args.snapshot)
    previous_fp = previous["artifact_fp"] if previous else None

    print(f"\n[Battery] Artifact fingerprint : {artifact.fingerprint}")
    print(f"[Battery] Schema version       : {artifact.schema_version}")
    print(f"[Battery] Profile              : {artifact.profile}")
    print(f"[Battery] Label                : {args.label}")
    print(
        f"[Battery] Previous snapshot    : {'found' if previous else 'none (first run)'}"
    )

    print(f"\n[Battery] Battery composition ({TOTAL} sessions, deterministic):")
    for scenario, count in BATTERY.items():
        pct = count / TOTAL * 100
        print(f"[Battery]   {scenario:<10} {count:>3} sessions ({pct:.0f}%)")

    print("\n[Battery] Running battery...")
    result = run_battery(artifact, previous_fp, args.label)

    print("\n[Battery] --- Results ---")
    print(
        f"[Battery]   True positives   : {result.true_positives:>3} / {ALWAYS_DRIFT + result.stale_drifted}"
    )
    print(
        f"[Battery]   False positives  : {result.false_positives:>3} / {BATTERY['clean']}"
    )
    print(
        f"[Battery]   Stale drifted    : {result.stale_drifted:>3} / {STALE_COUNT}  "
        f"({'artifact changed' if result.artifact_changed else 'artifact unchanged'})"
    )
    print(
        f"[Battery]   Detection rate   : {result.detection_rate * 100:.1f}%  (target: 100%)"
    )
    print(
        f"[Battery]   False pos rate   : {result.false_pos_rate * 100:.1f}%   (target:   0%)"
    )
    print(f"[Battery]   Drift rate       : {result.drift_rate * 100:.2f}%")

    # Accuracy verdict
    print("\n[Battery] --- Accuracy ---")
    if result.false_positives == 0 and result.detection_rate >= 1.0:
        print("[Battery] PERFECT — 100% detection, 0% false positives.")
    elif result.false_positives > 0:
        print(
            f"[Battery] FALSE POSITIVES DETECTED — {result.false_positives} clean sessions flagged as drift. Investigate."
        )
    elif result.detection_rate < 1.0:
        missed = int(
            (1.0 - result.detection_rate) * (ALWAYS_DRIFT + result.stale_drifted)
        )
        print(
            f"[Battery] MISSED DETECTIONS — {missed} drift scenarios not caught. Investigate."
        )

    if previous:
        print_delta(result, previous)

    save_snapshot(result, args.snapshot)
    print(f"\n[Battery] Snapshot saved → {args.snapshot}")
    print(SECTION)


if __name__ == "__main__":
    main()
