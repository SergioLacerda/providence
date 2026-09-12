#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, TypedDict


@dataclass(frozen=True)
class LadderMetrics:
    sample_size: int
    avg_false_block_rate: float
    avg_rework_delta: float
    rollback_rate: float


class ImpactRow(TypedDict, total=False):
    timestamp: str
    false_block_rate: float
    rework_delta: float
    rollback_flag: bool


class PromotionThreshold(TypedDict):
    min_samples: int
    max_false_block_rate: float
    max_rollback_rate: float
    max_rework_delta: float


class RollbackThreshold(TypedDict):
    min_samples: int
    false_block_rate: float
    rollback_rate: float
    rework_delta: float


class LadderThresholds(TypedDict):
    window_days: int
    promotion_candidate: PromotionThreshold
    rollback_trigger: RollbackThreshold


def _parse_iso(ts: str) -> datetime | None:
    raw = ts.strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _as_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return default
    return default


def _as_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def _parse_thresholds(path: Path) -> LadderThresholds:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("thresholds payload must be a JSON object")

    promote_raw = raw.get("promotion_candidate", {})
    rollback_raw = raw.get("rollback_trigger", {})
    if not isinstance(promote_raw, dict) or not isinstance(rollback_raw, dict):
        raise ValueError("thresholds sections must be JSON objects")

    return LadderThresholds(
        window_days=int(raw.get("window_days", 7)),
        promotion_candidate=PromotionThreshold(
            min_samples=int(promote_raw.get("min_samples", 0)),
            max_false_block_rate=_as_float(
                promote_raw.get("max_false_block_rate", 1.0), 1.0
            ),
            max_rollback_rate=_as_float(promote_raw.get("max_rollback_rate", 1.0), 1.0),
            max_rework_delta=_as_float(promote_raw.get("max_rework_delta", 1.0), 1.0),
        ),
        rollback_trigger=RollbackThreshold(
            min_samples=int(rollback_raw.get("min_samples", 0)),
            false_block_rate=_as_float(rollback_raw.get("false_block_rate", 1.0), 1.0),
            rollback_rate=_as_float(rollback_raw.get("rollback_rate", 1.0), 1.0),
            rework_delta=_as_float(rollback_raw.get("rework_delta", 1.0), 1.0),
        ),
    )


def _load_recent_impacts(path: Path, window_days: int) -> list[ImpactRow]:
    if not path.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    rows: list[ImpactRow] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        decoded: Any = json.loads(line)
        if not isinstance(decoded, dict):
            continue
        ts = _parse_iso(str(decoded.get("timestamp", "")))
        if ts is None:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if ts >= cutoff:
            rows.append(
                ImpactRow(
                    timestamp=str(decoded.get("timestamp", "")),
                    false_block_rate=_as_float(decoded.get("false_block_rate", 0.0)),
                    rework_delta=_as_float(decoded.get("rework_delta", 0.0)),
                    rollback_flag=_as_bool(decoded.get("rollback_flag", False)),
                )
            )
    return rows


def _compute_metrics(rows: list[ImpactRow]) -> LadderMetrics:
    if not rows:
        return LadderMetrics(0, 0.0, 0.0, 0.0)
    n = len(rows)
    avg_false = sum(r.get("false_block_rate", 0.0) for r in rows) / n
    avg_rework = sum(r.get("rework_delta", 0.0) for r in rows) / n
    rollback_rate = sum(1 for r in rows if bool(r.get("rollback_flag"))) / n
    return LadderMetrics(
        sample_size=n,
        avg_false_block_rate=round(avg_false, 6),
        avg_rework_delta=round(avg_rework, 6),
        rollback_rate=round(rollback_rate, 6),
    )


def _evaluate(metrics: LadderMetrics, thresholds: LadderThresholds) -> dict[str, bool]:
    promote = thresholds["promotion_candidate"]
    rollback = thresholds["rollback_trigger"]

    p_min_samples = promote["min_samples"]
    r_min_samples = rollback["min_samples"]

    promote_ready = (
        metrics.sample_size >= p_min_samples
        and metrics.avg_false_block_rate <= promote["max_false_block_rate"]
        and metrics.rollback_rate <= promote["max_rollback_rate"]
        and metrics.avg_rework_delta <= promote["max_rework_delta"]
    )

    rollback_recommended = metrics.sample_size >= r_min_samples and (
        metrics.avg_false_block_rate >= rollback["false_block_rate"]
        or metrics.rollback_rate >= rollback["rollback_rate"]
        or metrics.avg_rework_delta >= rollback["rework_delta"]
    )

    return {
        "promote_ready": promote_ready,
        "rollback_recommended": rollback_recommended,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build progressive-enforcement ladder digest."
    )
    parser.add_argument(
        "--impacts",
        default=".providence/runtime/rule-impact.jsonl",
        help="Path to rule-impact jsonl telemetry.",
    )
    parser.add_argument(
        "--thresholds",
        default="tools/ci/config/enforcement_ladder_thresholds.json",
        help="Path to threshold policy JSON.",
    )
    parser.add_argument("--json-out", required=True, help="Digest JSON output path.")
    parser.add_argument("--md-out", required=True, help="Digest markdown output path.")
    parser.add_argument(
        "--mode",
        choices=["report", "enforce"],
        default="report",
        help="In enforce mode, rollback recommendation returns non-zero.",
    )
    args = parser.parse_args()

    thresholds_path = Path(args.thresholds)
    thresholds = _parse_thresholds(thresholds_path)
    window_days = thresholds["window_days"]

    rows = _load_recent_impacts(Path(args.impacts), window_days=window_days)
    metrics = _compute_metrics(rows)
    eval_state = _evaluate(metrics, thresholds)

    status = "ok"
    if eval_state["rollback_recommended"]:
        status = "rollback_recommended"
    elif metrics.sample_size < thresholds["promotion_candidate"]["min_samples"]:
        status = "insufficient_data"
    elif eval_state["promote_ready"]:
        status = "promotion_candidate"

    payload = {
        "status": status,
        "window_days": window_days,
        "metrics": {
            "sample_size": metrics.sample_size,
            "avg_false_block_rate": metrics.avg_false_block_rate,
            "avg_rework_delta": metrics.avg_rework_delta,
            "rollback_rate": metrics.rollback_rate,
        },
        "thresholds": thresholds,
        "evaluation": eval_state,
        "source": str(args.impacts),
    }

    json_out = Path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    md_out = Path(args.md_out)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.write_text(
        "\n".join(
            [
                "# enforcement ladder digest",
                "",
                f"- status: `{status}`",
                f"- window_days: `{window_days}`",
                f"- sample_size: `{metrics.sample_size}`",
                f"- avg_false_block_rate: `{metrics.avg_false_block_rate}`",
                f"- avg_rework_delta: `{metrics.avg_rework_delta}`",
                f"- rollback_rate: `{metrics.rollback_rate}`",
                f"- promote_ready: `{eval_state['promote_ready']}`",
                f"- rollback_recommended: `{eval_state['rollback_recommended']}`",
                f"- source: `{args.impacts}`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    if args.mode == "enforce" and eval_state["rollback_recommended"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
