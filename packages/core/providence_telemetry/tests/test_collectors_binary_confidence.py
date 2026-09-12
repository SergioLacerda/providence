"""Tests for telemetry collectors: binary and confidence."""

from __future__ import annotations

import pytest

from providence_telemetry.collectors.binary import BinaryCollector, BinaryMetrics
from providence_telemetry.collectors.confidence import ConfidenceCollector

pytestmark = pytest.mark.unit


class TestBinaryMetrics:
    def test_compression_ratio_zero_when_json_size_zero(self) -> None:
        metrics = BinaryMetrics(json_size=0, msgpack_size=10, string_pool_size=3)
        assert metrics.compression_ratio == 0.0

    def test_compression_ratio_and_to_dict(self) -> None:
        metrics = BinaryMetrics(json_size=100, msgpack_size=40, string_pool_size=12)
        payload = metrics.to_dict()
        assert payload["json_size"] == 100
        assert payload["msgpack_size"] == 40
        assert payload["compression_ratio"] == 0.6
        assert payload["speedup_factor"] == 3.5


class TestBinaryCollector:
    def test_update_and_collect(self) -> None:
        collector = BinaryCollector()
        collector.update(json_size=200, msgpack_size=80, string_pool_size=20)
        result = collector.collect()
        assert collector.name == "binary_metrics"
        assert result["json_size"] == 200
        assert result["compression_ratio"] == 0.6


class TestConfidenceCollector:
    def test_evaluate_model_none(self) -> None:
        score, message = ConfidenceCollector().evaluate_model(None)
        assert score == 60
        assert "Unknown model" in message

    def test_evaluate_model_gpt4_variants(self) -> None:
        collector = ConfidenceCollector()
        assert collector.evaluate_model("gpt-4")[0] == 95
        assert collector.evaluate_model("gpt-4-turbo")[0] == 90
        assert collector.evaluate_model("gpt4-32k")[0] == 90

    def test_evaluate_model_claude_and_lower_tiers(self) -> None:
        collector = ConfidenceCollector()
        assert collector.evaluate_model("claude-3-opus")[0] == 95
        assert collector.evaluate_model("claude-sonnet")[0] == 90
        assert collector.evaluate_model("gpt-3.5-turbo")[0] == 80
        assert collector.evaluate_model("claude-haiku")[0] == 80
        assert collector.evaluate_model("gemini-1.5")[0] == 70
        assert collector.evaluate_model("my-custom-model")[0] == 60

    def test_evaluate_temperature_ranges(self) -> None:
        collector = ConfidenceCollector()
        assert collector.evaluate_temperature(None)[0] == 75
        assert collector.evaluate_temperature(0.0)[0] == 100
        assert collector.evaluate_temperature(0.4)[0] == 90
        assert collector.evaluate_temperature(0.9)[0] == 75
        assert collector.evaluate_temperature(1.2)[0] == 50

    def test_collect_high_safety_via_constructor(self) -> None:
        collector = ConfidenceCollector(model="gpt-4", temperature=0.0)
        result = collector.collect()
        assert result["overall_confidence"] == 97.5
        assert result["safety_level"] == "HIGH"

    def test_collect_moderate_safety_via_constructor(self) -> None:
        collector = ConfidenceCollector(model="unknown", temperature=1.2)
        result = collector.collect()
        assert result["overall_confidence"] == 55.0
        assert result["safety_level"] == "MODERATE"
