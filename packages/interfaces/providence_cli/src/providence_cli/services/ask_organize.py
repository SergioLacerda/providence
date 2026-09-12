"""Helpers for organize-intake heuristics and artifact generation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from providence_cli.services._ask_organize_support import (
    build_organize_artifact,
    write_organize_artifact,
)


def _estimate_input_complexity(text: str) -> dict[str, int]:
    lines = text.splitlines()
    line_count = max(1, len(lines))
    char_count = len(text)
    traceback_count = len(re.findall(r"\btraceback\b", text, flags=re.IGNORECASE))
    test_marker_count = len(re.findall(r"\btest[_\w]*\b", text, flags=re.IGNORECASE))
    error_marker_count = len(
        re.findall(r"\b(error|exception|failed|failure)\b", text, flags=re.IGNORECASE)
    )
    return {
        "line_count": line_count,
        "char_count": char_count,
        "traceback_count": traceback_count,
        "test_marker_count": test_marker_count,
        "error_marker_count": error_marker_count,
    }


def should_use_organize(text: str) -> tuple[bool, str]:
    """Return whether organize intake should be used and the trigger reason."""
    metrics = _estimate_input_complexity(text)
    if metrics["char_count"] >= 6000:
        return True, "char_count>=6000"
    if metrics["line_count"] >= 120:
        return True, "line_count>=120"
    if metrics["traceback_count"] >= 2:
        return True, "traceback_count>=2"
    if metrics["error_marker_count"] >= 8 and metrics["test_marker_count"] >= 4:
        return True, "dense_error_test_markers"
    return False, "light_input"


def run_sdd_organize(
    *,
    workspace_root: Path,
    query: str,
    source_text: str,
    route_reason: str,
) -> tuple[dict[str, Any], Path]:
    """Run sdd-organize intake and persist artifact."""
    artifact = build_organize_artifact(
        query=query,
        source_text=source_text,
        route_reason=route_reason,
    )
    path = write_organize_artifact(workspace_root=workspace_root, artifact=artifact)
    return artifact, path
