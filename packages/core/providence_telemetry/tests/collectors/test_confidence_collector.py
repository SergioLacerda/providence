from providence_telemetry.collectors import MetricsRegistry
from providence_telemetry.collectors.confidence import ConfidenceCollector


def test_collect_no_args_uses_constructor_config() -> None:
    collector = ConfidenceCollector(model="gpt-4", temperature=0.0)
    result = collector.collect()
    assert result["model"]["score"] == 95
    assert result["temperature"]["score"] == 100
    assert result["overall_confidence"] == 97.5
    assert result["safety_level"] == "HIGH"


def test_collect_default_constructor() -> None:
    collector = ConfidenceCollector()
    result = collector.collect()
    assert "model" in result
    assert "temperature" in result
    assert "overall_confidence" in result
    assert "safety_level" in result


def test_evaluate_model_unknown() -> None:
    c = ConfidenceCollector()
    score, msg = c.evaluate_model(None)
    assert score == 60
    assert "neutral" in msg


def test_evaluate_model_gpt4() -> None:
    c = ConfidenceCollector()
    score, _ = c.evaluate_model("gpt-4")
    assert score == 95


def test_evaluate_model_gpt4_turbo() -> None:
    c = ConfidenceCollector()
    score, _ = c.evaluate_model("gpt-4-turbo")
    assert score == 90


def test_evaluate_model_claude_opus() -> None:
    c = ConfidenceCollector()
    score, _ = c.evaluate_model("claude-3-opus-20240229")
    assert score == 95


def test_evaluate_model_claude_sonnet() -> None:
    c = ConfidenceCollector()
    score, _ = c.evaluate_model("claude-3-sonnet")
    assert score == 90


def test_evaluate_model_gpt35() -> None:
    c = ConfidenceCollector()
    score, _ = c.evaluate_model("gpt-3.5-turbo")
    assert score == 80


def test_evaluate_model_haiku() -> None:
    c = ConfidenceCollector()
    score, _ = c.evaluate_model("claude-haiku")
    assert score == 80


def test_evaluate_model_gemini() -> None:
    c = ConfidenceCollector()
    score, _ = c.evaluate_model("gemini-pro")
    assert score == 70


def test_evaluate_model_unknown_named() -> None:
    c = ConfidenceCollector()
    score, msg = c.evaluate_model("llama-3")
    assert score == 60
    assert "llama-3" in msg


def test_evaluate_temperature_none() -> None:
    c = ConfidenceCollector()
    score, _ = c.evaluate_temperature(None)
    assert score == 75


def test_evaluate_temperature_zero() -> None:
    c = ConfidenceCollector()
    score, msg = c.evaluate_temperature(0.0)
    assert score == 100
    assert "Deterministic" in msg


def test_evaluate_temperature_low() -> None:
    c = ConfidenceCollector()
    score, _ = c.evaluate_temperature(0.3)
    assert score == 90


def test_evaluate_temperature_moderate() -> None:
    c = ConfidenceCollector()
    score, _ = c.evaluate_temperature(0.7)
    assert score == 75


def test_evaluate_temperature_high() -> None:
    c = ConfidenceCollector()
    score, _ = c.evaluate_temperature(1.5)
    assert score == 50


def test_safety_level_moderate() -> None:
    collector = ConfidenceCollector(model=None, temperature=1.5)
    result = collector.collect()
    assert result["safety_level"] == "MODERATE"


def test_collect_compatible_with_metrics_registry() -> None:
    registry = MetricsRegistry()
    collector = ConfidenceCollector(model="gpt-4", temperature=0.0)
    registry.register(collector)
    results = registry.collect_all()
    assert "agent_confidence" in results["metrics"]
