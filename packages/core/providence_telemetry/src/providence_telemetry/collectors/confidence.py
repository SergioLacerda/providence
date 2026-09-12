"""Collector that scores AI agent confidence from model and temperature metadata."""

from typing import Any

from ..collectors import BaseCollector

_SAFETY_HIGH_THRESHOLD: int = 80

_MODEL_SCORES: list[tuple[str, int, str]] = [
    ("gpt-4-turbo", 90, "GPT-4 Turbo (high confidence)"),
    ("gpt4-32k", 90, "GPT-4 32K (high confidence)"),
    ("gpt-4", 95, "GPT-4 (very high confidence)"),
    ("claude-3-opus", 95, "Claude Opus (very high confidence)"),
    ("claude-opus", 95, "Claude Opus (very high confidence)"),
    ("claude-3-sonnet", 90, "Claude Sonnet (high confidence)"),
    ("claude-sonnet", 90, "Claude Sonnet (high confidence)"),
    ("gpt-3.5", 80, "GPT-3.5-Turbo (moderate confidence)"),
    ("gpt35", 80, "GPT-3.5-Turbo (moderate confidence)"),
    ("claude-haiku", 80, "Claude Haiku (moderate confidence)"),
    ("gemini", 70, "Gemini (baseline confidence)"),
]


class ConfidenceCollector(BaseCollector):
    """Evaluates AI agent confidence and operational safety."""

    def __init__(
        self,
        name: str = "agent_confidence",
        model: str | None = None,
        temperature: float | None = None,
    ) -> None:
        super().__init__(name)
        self._model = model
        self._temperature = temperature

    def collect(self) -> dict[str, Any]:
        """Return model + temperature confidence scores and an overall safety level."""
        model_score, model_msg = self.evaluate_model(self._model)
        temp_score, temp_msg = self.evaluate_temperature(self._temperature)
        avg_score = (model_score + temp_score) / 2
        return {
            "model": {"score": model_score, "message": model_msg},
            "temperature": {"score": temp_score, "message": temp_msg},
            "overall_confidence": avg_score,
            "safety_level": "HIGH"
            if avg_score >= _SAFETY_HIGH_THRESHOLD
            else "MODERATE",
        }

    def evaluate_model(self, model_name: str | None) -> tuple[int, str]:
        """Return a (score, message) pair for the given model identifier."""
        if not model_name:
            return 60, "Unknown model (neutral confidence)"
        model_lower = model_name.lower()
        for substring, score, message in _MODEL_SCORES:
            if substring in model_lower:
                return score, message
        return 60, f"Unknown model: {model_name}"

    def evaluate_temperature(self, temperature: float | None) -> tuple[int, str]:
        """Return a (score, message) pair based on the sampling temperature."""
        if temperature is None:
            return 75, "Default temperature (0.7 assumed)"
        if temperature == 0.0:
            return 100, "Deterministic mode (temperature=0.0)"
        if temperature < 0.5:
            return 90, f"Low randomness (temp={temperature:.1f})"
        if temperature < 1.0:
            return 75, f"Moderate randomness (temp={temperature:.1f})"
        return 50, f"High randomness (temp={temperature:.1f})"
