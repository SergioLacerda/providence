"""Context summarization and compression helpers."""

from __future__ import annotations

import json
from typing import Any


def _summarize_context_value(value: Any) -> Any:
    if isinstance(value, str):
        if len(value) <= 120:
            return value
        return {
            "type": "string",
            "length": len(value),
            "preview": value[:120],
        }
    if isinstance(value, list):
        sample = value[:3]
        return {
            "type": "list",
            "count": len(value),
            "sample": sample,
        }
    if isinstance(value, dict):
        keys = sorted(str(key) for key in value)
        return {
            "type": "dict",
            "count": len(value),
            "keys": keys[:10],
        }
    return value


def _estimate_payload_size(payload: Any) -> int:
    try:
        return len(json.dumps(payload, sort_keys=True, ensure_ascii=True))
    except TypeError:
        return len(str(payload))


def _compress_context(context: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    critical_keys = {
        "governance_fingerprint",
        "active_mandates",
        "execution_contract",
        "diagnosis_report",
        "diagnosis_attestation",
        "gate_decision",
        "freeze_mode_state",
        "pipeline_state",
        "pipeline_gate_decision",
        "pipeline_escalation",
    }
    compressed: dict[str, Any] = {}
    summarized_keys: list[str] = []
    archival_candidates: list[str] = []

    for key, value in context.items():
        if key in critical_keys:
            compressed[key] = value
            continue
        summarized = _summarize_context_value(value)
        compressed[key] = summarized
        summarized_keys.append(key)
        if (
            isinstance(value, str)
            and len(value) > 120
            or isinstance(value, list | dict)
            and len(value) > 3
        ):
            archival_candidates.append(key)

    original_size = _estimate_payload_size(context)
    compressed_size = _estimate_payload_size(compressed)
    report: dict[str, Any] = {
        "original_key_count": len(context),
        "compressed_key_count": len(compressed),
        "original_estimated_bytes": original_size,
        "compressed_estimated_bytes": compressed_size,
        "preserved_keys": sorted(key for key in context if key in critical_keys),
        "summarized_keys": sorted(summarized_keys),
        "archival_candidates": sorted(archival_candidates),
        "compression_ratio": (
            float(compressed_size) / float(original_size) if original_size > 0 else 1.0
        ),
    }
    return compressed, report
