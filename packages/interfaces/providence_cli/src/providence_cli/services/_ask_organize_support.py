"""Support helpers for organize-intake artifact generation."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from providence_cli.services.ask_hash import _hash_query


def _now() -> str:
    return (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )


def split_into_chunks(text: str, *, max_lines: int = 40) -> list[dict[str, Any]]:
    lines = text.splitlines() or [text]
    chunks: list[dict[str, Any]] = []
    cursor = 0
    chunk_id = 0
    while cursor < len(lines):
        window = lines[cursor : cursor + max_lines]
        chunk_text = "\n".join(window)
        offset_start = len("\n".join(lines[:cursor])) + (1 if cursor > 0 else 0)
        chunks.append(
            {
                "chunk_id": f"c{chunk_id:04d}",
                "line_start": cursor + 1,
                "line_end": cursor + len(window),
                "offset_start": offset_start,
                "offset_end": offset_start + len(chunk_text),
                "text_hash": hashlib.sha256(chunk_text.encode()).hexdigest()[:12],
                "preview": chunk_text[:220],
            }
        )
        cursor += max_lines
        chunk_id += 1
    return chunks


def _extract_error_signature(block: str) -> str:
    match = re.search(
        r"([A-Za-z_][A-Za-z0-9_]*(Error|Exception))", block, flags=re.IGNORECASE
    )
    if match:
        return match.group(1)
    if "failed" in block.lower():
        return "AssertionFailed"
    return "UnknownError"


def _extract_test_case(block: str) -> str:
    match = re.search(r"\b(test[_A-Za-z0-9]+)\b", block)
    return match.group(1) if match else "unknown_test"


def _extract_file_path(block: str) -> str:
    match = re.search(r"([A-Za-z0-9_\-./]+\.py)", block)
    return match.group(1) if match else "unknown_file"


def _extract_time_key(block: str) -> str:
    match = re.search(r"(\d{2}:\d{2}:\d{2})", block)
    return match.group(1) if match else "unknown_time"


def _new_index_entry(
    *, chunk_id: str, severity: str, confidence: float
) -> dict[str, Any]:
    return {
        "chunks": [chunk_id],
        "severity": severity,
        "first_seen": _now(),
        "repeat_count": 1,
        "confidence": confidence,
        "noise_score": 0.0,
    }


def _append_or_merge_index(
    index: dict[str, dict[str, Any]],
    key: str,
    chunk_id: str,
    *,
    severity: str = "medium",
    confidence: float = 0.7,
) -> None:
    if key not in index:
        index[key] = _new_index_entry(
            chunk_id=chunk_id, severity=severity, confidence=confidence
        )
        return
    existing = index[key]
    if chunk_id not in existing["chunks"]:
        existing["chunks"].append(chunk_id)
    existing["repeat_count"] = int(existing.get("repeat_count", 1)) + 1


def build_multi_index(
    *, source_text: str, chunks: list[dict[str, Any]]
) -> dict[str, Any]:
    lines = source_text.splitlines()
    by_error: dict[str, dict[str, Any]] = {}
    by_root_cause: dict[str, dict[str, Any]] = {}
    by_test_case: dict[str, dict[str, Any]] = {}
    by_file_path: dict[str, dict[str, Any]] = {}
    by_time_window: dict[str, dict[str, Any]] = {}
    for chunk in chunks:
        start = int(chunk["line_start"]) - 1
        block = "\n".join(lines[start : int(chunk["line_end"])]).strip()
        chunk_id = str(chunk["chunk_id"])
        signature = _extract_error_signature(block)
        _append_or_merge_index(
            by_error,
            signature,
            chunk_id,
            severity="high"
            if "Error" in signature or "Exception" in signature
            else "medium",
            confidence=0.85,
        )
        _append_or_merge_index(by_root_cause, signature, chunk_id, confidence=0.75)
        _append_or_merge_index(
            by_test_case, _extract_test_case(block), chunk_id, confidence=0.65
        )
        _append_or_merge_index(
            by_file_path, _extract_file_path(block), chunk_id, confidence=0.6
        )
        _append_or_merge_index(
            by_time_window, _extract_time_key(block), chunk_id, confidence=0.5
        )
    return {
        "index_by_error_signature": by_error,
        "index_by_root_cause": by_root_cause,
        "index_by_test_case": by_test_case,
        "index_by_file_path": by_file_path,
        "index_by_time_window": by_time_window,
    }


def build_organize_artifact(
    *, query: str, source_text: str, route_reason: str, degraded: bool = False
) -> dict[str, Any]:
    chunks = split_into_chunks(source_text)
    indexed_lines = sum(
        max(0, int(chunk["line_end"]) - int(chunk["line_start"]) + 1)
        for chunk in chunks
    )
    total_lines = max(1, len(source_text.splitlines()))
    discarded_pct = max(0.0, 100.0 - ((indexed_lines / total_lines) * 100.0))
    return {
        "schema_version": "1.0.0",
        "query_hash": _hash_query(query),
        "query_original": query,
        "intake_index_mode": "multi",
        "route": "heavy",
        "route_reason": route_reason,
        "retrieval_policy": "degraded" if degraded else "indexed_only",
        "index_degraded": degraded,
        "chunks": chunks,
        "indexes": build_multi_index(source_text=source_text, chunks=chunks),
        "coverage_stats": {
            "total_lines": total_lines,
            "indexed_lines": indexed_lines,
            "indexed_pct": round((indexed_lines / total_lines) * 100.0, 2),
            "discarded_noise_pct": round(discarded_pct, 2),
        },
    }


def write_organize_artifact(*, workspace_root: Path, artifact: dict[str, Any]) -> Path:
    out_dir = workspace_root / ".providence" / "runtime" / "ask-intake"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"{ts}-{artifact.get('query_hash', 'unknown')}.json"
    out_path.write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return out_path
