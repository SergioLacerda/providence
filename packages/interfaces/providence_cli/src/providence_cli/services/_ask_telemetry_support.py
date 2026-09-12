"""Support helpers for ask telemetry/session flows."""

from __future__ import annotations

import configparser
from pathlib import Path
from typing import Any


def resolve_workspace_id(*, workspace_root: Path, logger: Any | None = None) -> str:
    profile_path = workspace_root / ".providence" / "profile"
    if not profile_path.exists():
        return "unknown"
    try:
        parser = configparser.ConfigParser()
        parser.read(profile_path)
        return parser.get("sdd", "workspace_id", fallback="unknown")
    except Exception as exc:
        if logger is not None:
            logger.debug("Failed to read config: %s", exc)
        return "unknown"


def build_telemetry_details(
    *,
    context_source: str,
    mandates_count: int,
    drift_detected: bool,
    profile: str,
    state: str,
    query_hash: str = "",
    extra_details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    details: dict[str, Any] = {
        "context_source": context_source,
        "mandates_loaded": mandates_count,
        "drift_detected": drift_detected,
        "ahp_state": state,
        "profile": profile,
    }
    if query_hash:
        details["query_hash"] = query_hash
    if extra_details:
        details.update(extra_details)
    return details


def resolve_status(state: str) -> str:
    return "ok" if state in ("HEALTHY", "PARTIAL") else "warn"


def build_sink(
    *,
    otel_endpoint: str,
    events_path: Path,
    telemetry_sink_cls: Any,
    otel_bridge_cls: Any,
    otlp_exporter_cls: Any,
) -> Any:
    if otel_endpoint:
        exporter = otlp_exporter_cls(endpoint=otel_endpoint)
        return otel_bridge_cls(exporter=exporter, jsonl_path=events_path)
    return telemetry_sink_cls(jsonl_path=events_path, logging_mode="passive")
