"""Tests for governance_gate B110 exception handling.

This module validates that governance_gate() correctly silences exceptions
from governance checks (B110 nosec annotation at profile.py:311).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import click
import pytest
import typer

from providence_cli.utils.profile import governance_gate


class TestGovernanceGateFallback:
    """Test governance_gate exception handling and fallback behavior."""

    @staticmethod
    def _make_minimal_ctx() -> click.Context:
        """Create a minimal Click context for testing."""
        ctx = click.Context(click.Command("test"))
        ctx.obj = {"root": None, "profile": ""}
        return ctx

    def test_governance_gate_silences_import_error(self) -> None:
        """Test that governance_gate gracefully handles import errors.

        This covers the try-except-pass fallback at profile.py:311
        when AgentHandshakeProtocol or TelemetrySink imports fail.

        The gate must never block legitimate commands due to import errors,
        so any RuntimeError from the governance check should be silently caught.
        """
        ctx = self._make_minimal_ctx()

        # Patch the module imports inside the function to raise an error
        with patch(
            "providence_core.governance.handshake.AgentHandshakeProtocol",
            side_effect=RuntimeError("Import failed"),
        ):
            # Should not raise; exception should be silently caught
            result = governance_gate(ctx)

            # Function returns None on success
            assert result is None

    def test_governance_gate_reraises_typer_exit(self) -> None:
        """Test that governance_gate properly re-raises typer.Exit.

        This validates the except typer.Exit: raise branch at profile.py:309,
        ensuring that hard-block exits are not silenced.
        """
        ctx = self._make_minimal_ctx()

        # Patch AgentHandshakeProtocol to raise typer.Exit
        with (
            patch(
                "providence_core.governance.handshake.AgentHandshakeProtocol",
                side_effect=typer.Exit(1),
            ),
            pytest.raises(typer.Exit),
        ):
            # Should re-raise typer.Exit; not catch it in the broad Exception handler
            governance_gate(ctx)

    def test_governance_gate_silences_telemetry_error(self) -> None:
        """Test that governance_gate handles TelemetrySink errors gracefully.

        Validates fallback when telemetry initialization or flush fails,
        ensuring the gate does not block commands due to observability issues.
        """
        ctx = self._make_minimal_ctx()

        # Create a mock AgentHandshakeProtocol that succeeds, but TelemetrySink fails
        mock_ahp = MagicMock()
        mock_ahp.validate.return_value = ("HEALTHY", {})

        with (
            patch(
                "providence_core.governance.handshake.AgentHandshakeProtocol",
                return_value=mock_ahp,
            ),
            patch("providence_runtime.telemetry.TelemetrySink") as mock_sink_class,
        ):
            mock_sink = MagicMock()
            mock_sink.emit.side_effect = RuntimeError("Telemetry unavailable")
            mock_sink_class.return_value = mock_sink

            # Should not raise; silently continue despite telemetry error
            result = governance_gate(ctx)
            assert result is None
