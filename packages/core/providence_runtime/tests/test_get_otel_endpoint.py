"""Tests for the centralized OTLP endpoint resolution helper.

Regression coverage for A3: SDD_OTEL_EXPORTER_ENDPOINT (canonical) and
SDD_OTEL_ENDPOINT (legacy, previously read independently by the CLI's
ask_telemetry path) must resolve through a single function so both layers
agree on precedence.
"""

from __future__ import annotations

import os
from unittest.mock import patch

from providence_runtime.telemetry import get_otel_endpoint


def test_returns_empty_when_unset() -> None:
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("SDD_OTEL_EXPORTER_ENDPOINT", None)
        os.environ.pop("SDD_OTEL_ENDPOINT", None)
        assert get_otel_endpoint() == ""


def test_reads_canonical_env_var() -> None:
    with patch.dict(
        os.environ, {"SDD_OTEL_EXPORTER_ENDPOINT": "https://canonical.example/v1"}
    ):
        os.environ.pop("SDD_OTEL_ENDPOINT", None)
        assert get_otel_endpoint() == "https://canonical.example/v1"


def test_falls_back_to_legacy_env_var() -> None:
    with patch.dict(os.environ, {"SDD_OTEL_ENDPOINT": "https://legacy.example/v1"}):
        os.environ.pop("SDD_OTEL_EXPORTER_ENDPOINT", None)
        assert get_otel_endpoint() == "https://legacy.example/v1"


def test_canonical_env_var_takes_precedence_over_legacy() -> None:
    with patch.dict(
        os.environ,
        {
            "SDD_OTEL_EXPORTER_ENDPOINT": "https://canonical.example/v1",
            "SDD_OTEL_ENDPOINT": "https://legacy.example/v1",
        },
    ):
        assert get_otel_endpoint() == "https://canonical.example/v1"
