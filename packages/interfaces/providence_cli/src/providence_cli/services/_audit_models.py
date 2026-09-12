"""Data models for audit event parsing."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DriftRow:
    """Represents a single drift event row in the audit log."""

    ts: str
    drift_type: str
    command: str
    status: str
    fingerprint_short: str
    cause: str
