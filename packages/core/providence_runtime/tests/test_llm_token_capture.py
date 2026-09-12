"""Tests for LLM token capture protocol and implementations."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from providence_runtime.llm import (
    ClaudeTokenCapture,
    LLMTokenCapture,
    SimulatedTokenCapture,
    TokenCounts,
)


class TestTokenCounts:
    """Test TokenCounts dataclass."""

    def test_tokens_total_computed_correctly(self) -> None:
        """tokens_total should be sum of input and output."""
        counts = TokenCounts(tokens_input=100, tokens_output=50)
        assert counts.tokens_total == 150

    def test_tokens_total_zero(self) -> None:
        """tokens_total should be 0 when both inputs are 0."""
        counts = TokenCounts(tokens_input=0, tokens_output=0)
        assert counts.tokens_total == 0

    def test_tokens_total_large_numbers(self) -> None:
        """tokens_total should handle large numbers."""
        counts = TokenCounts(tokens_input=1_000_000, tokens_output=500_000)
        assert counts.tokens_total == 1_500_000


class TestSimulatedTokenCapture:
    """Test SimulatedTokenCapture implementation."""

    def test_capture_from_response_returns_none(self) -> None:
        """capture_from_response should always return None."""
        capture = SimulatedTokenCapture()
        assert capture.capture_from_response("any response") is None
        assert capture.capture_from_response(None) is None
        assert capture.capture_from_response({"tokens": 100}) is None

    def test_capture_from_env_returns_none_when_env_not_set(self) -> None:
        """capture_from_env should return None when env vars not set."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SDD_TOKENS_INPUT", None)
            os.environ.pop("SDD_TOKENS_OUTPUT", None)
            capture = SimulatedTokenCapture()
            assert capture.capture_from_env() is None

    def test_capture_from_env_returns_none_when_only_input_set(self) -> None:
        """capture_from_env should return None when only one env var set."""
        with patch.dict(os.environ, {"SDD_TOKENS_INPUT": "100"}, clear=False):
            os.environ.pop("SDD_TOKENS_OUTPUT", None)
            capture = SimulatedTokenCapture()
            assert capture.capture_from_env() is None

    def test_capture_from_env_returns_none_when_only_output_set(self) -> None:
        """capture_from_env should return None when only one env var set."""
        with patch.dict(os.environ, {"SDD_TOKENS_OUTPUT": "50"}, clear=False):
            os.environ.pop("SDD_TOKENS_INPUT", None)
            capture = SimulatedTokenCapture()
            assert capture.capture_from_env() is None

    def test_capture_from_env_returns_token_counts_when_set(self) -> None:
        """capture_from_env should return TokenCounts when both env vars set."""
        with patch.dict(
            os.environ,
            {"SDD_TOKENS_INPUT": "150", "SDD_TOKENS_OUTPUT": "75"},
            clear=False,
        ):
            capture = SimulatedTokenCapture()
            result = capture.capture_from_env()
            assert result is not None
            assert result.tokens_input == 150
            assert result.tokens_output == 75
            assert result.tokens_total == 225

    def test_capture_from_env_raises_on_invalid_input(self) -> None:
        """capture_from_env should raise ValueError if env vars are not integers."""
        with patch.dict(
            os.environ,
            {"SDD_TOKENS_INPUT": "invalid", "SDD_TOKENS_OUTPUT": "50"},
            clear=False,
        ):
            capture = SimulatedTokenCapture()
            with pytest.raises(ValueError, match="must be integers"):
                capture.capture_from_env()

    def test_capture_from_env_raises_on_invalid_output(self) -> None:
        """capture_from_env should raise ValueError if output is not an integer."""
        with patch.dict(
            os.environ,
            {"SDD_TOKENS_INPUT": "100", "SDD_TOKENS_OUTPUT": "not_int"},
            clear=False,
        ):
            capture = SimulatedTokenCapture()
            with pytest.raises(ValueError, match="must be integers"):
                capture.capture_from_env()

    def test_capture_from_env_handles_zero_values(self) -> None:
        """capture_from_env should accept 0 as a valid value."""
        with patch.dict(
            os.environ, {"SDD_TOKENS_INPUT": "0", "SDD_TOKENS_OUTPUT": "0"}, clear=False
        ):
            capture = SimulatedTokenCapture()
            result = capture.capture_from_env()
            assert result is not None
            assert result.tokens_input == 0
            assert result.tokens_output == 0

    def test_capture_from_env_handles_negative_values(self) -> None:
        """capture_from_env should accept negative values (no validation)."""
        with patch.dict(
            os.environ,
            {"SDD_TOKENS_INPUT": "-100", "SDD_TOKENS_OUTPUT": "-50"},
            clear=False,
        ):
            capture = SimulatedTokenCapture()
            result = capture.capture_from_env()
            assert result is not None
            assert result.tokens_input == -100
            assert result.tokens_output == -50


class TestLLMTokenCaptureProtocol:
    """Test that SimulatedTokenCapture satisfies LLMTokenCapture protocol."""

    def test_simulated_token_capture_satisfies_protocol(self) -> None:
        """SimulatedTokenCapture should satisfy LLMTokenCapture protocol."""
        capture = SimulatedTokenCapture()
        # Protocol check: both methods should be callable
        assert callable(capture.capture_from_response)
        assert callable(capture.capture_from_env)

        # Protocol check: both methods should return TokenCounts | None
        assert capture.capture_from_response("test") is None or isinstance(
            capture.capture_from_response("test"), TokenCounts
        )
        assert capture.capture_from_env() is None or isinstance(
            capture.capture_from_env(), TokenCounts
        )

    def test_protocol_default_methods_are_callable(self) -> None:
        assert LLMTokenCapture.capture_from_response(object(), {}) is None
        assert LLMTokenCapture.capture_from_env(object()) is None


class _Usage:
    def __init__(self, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _Response:
    def __init__(self, usage: object) -> None:
        self.usage = usage


class TestClaudeTokenCapture:
    def test_capture_from_response_success(self) -> None:
        capture = ClaudeTokenCapture()
        response = _Response(_Usage(120, 30))
        result = capture.capture_from_response(response)
        assert result is not None
        assert result.tokens_input == 120
        assert result.tokens_output == 30

    def test_capture_from_response_missing_usage_returns_none(self) -> None:
        capture = ClaudeTokenCapture()
        assert capture.capture_from_response(object()) is None

    def test_capture_from_response_invalid_values_returns_none(self) -> None:
        capture = ClaudeTokenCapture()
        response = _Response(_Usage("bad", 10))  # type: ignore[arg-type]
        assert capture.capture_from_response(response) is None

    def test_capture_from_env_success_and_invalid(self) -> None:
        capture = ClaudeTokenCapture()
        with patch.dict(
            os.environ,
            {"SDD_TOKENS_INPUT": "42", "SDD_TOKENS_OUTPUT": "8"},
            clear=False,
        ):
            ok = capture.capture_from_env()
            assert ok is not None
            assert ok.tokens_total == 50
        with patch.dict(
            os.environ,
            {"SDD_TOKENS_INPUT": "x", "SDD_TOKENS_OUTPUT": "8"},
            clear=False,
        ):
            assert capture.capture_from_env() is None


class TestTokenCountsIntegration:
    """Integration tests combining token capture with telemetry."""

    def test_simulated_capture_with_environment_flow(self) -> None:
        """Test full flow: capture tokens from env and verify they propagate."""
        with patch.dict(
            os.environ,
            {"SDD_TOKENS_INPUT": "200", "SDD_TOKENS_OUTPUT": "100"},
            clear=False,
        ):
            capture = SimulatedTokenCapture()
            tokens = capture.capture_from_env()

            assert tokens is not None
            assert tokens.tokens_input == 200
            assert tokens.tokens_output == 100
            assert tokens.tokens_total == 300

    def test_multiple_captures_independent(self) -> None:
        """Multiple capture instances should be independent."""
        with patch.dict(
            os.environ,
            {"SDD_TOKENS_INPUT": "100", "SDD_TOKENS_OUTPUT": "50"},
            clear=False,
        ):
            capture1 = SimulatedTokenCapture()
            capture2 = SimulatedTokenCapture()

            tokens1 = capture1.capture_from_env()
            tokens2 = capture2.capture_from_env()

            assert tokens1 is not None
            assert tokens2 is not None
            assert tokens1.tokens_total == tokens2.tokens_total
