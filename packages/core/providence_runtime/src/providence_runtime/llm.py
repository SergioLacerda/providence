"""LLM Token Capture — Extract and propagate token counts from API responses.

This module provides protocols and implementations for capturing token counts
from LLM API responses (e.g., Claude API) and propagating them through the
telemetry system for accurate economy tracking.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol

_ENV_TOKENS_INPUT = "SDD_TOKENS_INPUT"
_ENV_TOKENS_OUTPUT = "SDD_TOKENS_OUTPUT"


def _read_token_env_vars() -> tuple[str | None, str | None]:
    """Return the raw (unparsed) SDD_TOKENS_INPUT/SDD_TOKENS_OUTPUT env values."""
    return os.environ.get(_ENV_TOKENS_INPUT), os.environ.get(_ENV_TOKENS_OUTPUT)


@dataclass
class TokenCounts:
    """Container for LLM API token counts."""

    tokens_input: int
    tokens_output: int

    @property
    def tokens_total(self) -> int:
        """Computed total tokens."""
        return self.tokens_input + self.tokens_output


class LLMTokenCapture(Protocol):
    """Protocol for capturing token counts from LLM responses."""

    def capture_from_response(self, _response: Any) -> TokenCounts | None:
        """Extract token counts from an LLM API response object.

        Args:
            _response: An LLM API response object (e.g., Claude Message).

        Returns:
            TokenCounts if tokens are present, None if extraction fails or unsupported.
        """
        pass

    def capture_from_env(self) -> TokenCounts | None:
        """Extract token counts from environment variables.

        Returns:
            TokenCounts if SDD_TOKENS_INPUT and SDD_TOKENS_OUTPUT are set, None otherwise.
        """
        pass


class ClaudeTokenCapture:
    """Captures token counts from Claude API responses.

    Extracts usage information from Claude API Message objects.
    Falls back to environment variables if API integration not available.
    """

    def capture_from_response(self, response: Any) -> TokenCounts | None:
        """Extract token counts from Claude API response.

        Expects a Message object with a usage attribute containing:
        - input_tokens: Number of input tokens
        - output_tokens: Number of output tokens

        Args:
            response: Claude API Message object.

        Returns:
            TokenCounts if tokens are present, None otherwise.
        """
        try:
            # Claude API response structure:
            # response.usage.input_tokens
            # response.usage.output_tokens
            if hasattr(response, "usage") and response.usage is not None:
                usage = response.usage
                if hasattr(usage, "input_tokens") and hasattr(usage, "output_tokens"):
                    return TokenCounts(
                        tokens_input=int(usage.input_tokens),
                        tokens_output=int(usage.output_tokens),
                    )
        except (AttributeError, TypeError, ValueError):
            # Fallback to None if response structure doesn't match expected format
            pass

        return None

    def capture_from_env(self) -> TokenCounts | None:
        """Fallback: Extract token counts from environment variables.

        Returns:
            TokenCounts if SDD_TOKENS_INPUT and SDD_TOKENS_OUTPUT are set, None otherwise.
        """
        tokens_input_str, tokens_output_str = _read_token_env_vars()

        if tokens_input_str is None or tokens_output_str is None:
            return None

        try:
            tokens_input = int(tokens_input_str)
            tokens_output = int(tokens_output_str)
            return TokenCounts(tokens_input=tokens_input, tokens_output=tokens_output)
        except ValueError:
            return None


class SimulatedTokenCapture:
    """Captures token counts from environment variables.

    Allows CLI and test harnesses to simulate token counts without requiring
    a live Claude API integration. Reads from SDD_TOKENS_INPUT and SDD_TOKENS_OUTPUT
    environment variables.
    """

    def capture_from_response(self, response: Any) -> TokenCounts | None:
        """Not implemented for simulated capture.

        Returns:
            Always None (use capture_from_env instead).
        """
        return None

    def capture_from_env(self) -> TokenCounts | None:
        """Extract token counts from environment variables.

        Looks for SDD_TOKENS_INPUT and SDD_TOKENS_OUTPUT. Both must be set and
        must be valid integers.

        Returns:
            TokenCounts if both env vars are present, None otherwise.

        Raises:
            ValueError: If env vars are set but not valid integers.
        """
        tokens_input_str, tokens_output_str = _read_token_env_vars()

        if tokens_input_str is None or tokens_output_str is None:
            return None

        try:
            tokens_input = int(tokens_input_str)
            tokens_output = int(tokens_output_str)
            return TokenCounts(tokens_input=tokens_input, tokens_output=tokens_output)
        except ValueError as e:
            raise ValueError(
                f"SDD_TOKENS_INPUT and SDD_TOKENS_OUTPUT must be integers, "
                f"got '{tokens_input_str}' and '{tokens_output_str}': {e}"
            ) from e
