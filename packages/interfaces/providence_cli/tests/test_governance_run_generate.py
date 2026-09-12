"""Tests for providence_cli.services.governance_generate_handlers  run_generate orchestration."""

from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

from rich.console import Console

from providence_cli.services.governance_generate_handlers import run_generate


def _console() -> Console:
    return Console(file=io.StringIO(), width=120)


class TestRunGenerate:
    def test_non_bootstrap_delegates_to_generate_artifacts(self) -> None:
        with patch(
            "providence_cli.services.governance_generate_handlers.generate_artifacts"
        ) as mock_gen:
            run_generate(
                output_dir="/out",
                path="",
                full_bootstrap=False,
                key_id="dev-01",
                profile="client",
                output_json=False,
                console=_console(),
            )
        mock_gen.assert_called_once()

    def test_invalid_kwargs_are_coerced_to_defaults(self) -> None:
        """Non-bool/non-str kwargs fall back to safe defaults (non-bootstrap path)."""
        with patch(
            "providence_cli.services.governance_generate_handlers.generate_artifacts"
        ) as mock_gen:
            run_generate(
                output_dir="/out",
                path="",
                full_bootstrap="not-a-bool",
                key_id=123,
                profile=None,
                output_json=False,
                console=_console(),
            )
        mock_gen.assert_called_once()

    def test_full_bootstrap_runs_full_sequence(self) -> None:
        compile_fn = MagicMock()
        keygen_fn = MagicMock()
        sign_fn = MagicMock()
        with (
            patch(
                "providence_cli.services.governance_generate_handlers.generate_artifacts"
            ) as mock_gen,
            patch(
                "providence_cli.services.governance_generate_handlers.run_bootstrap_signing"
            ) as mock_sign,
            patch(
                "providence_cli.services.governance_generate_handlers.complete_bootstrap_handshake"
            ) as mock_handshake,
        ):
            run_generate(
                output_dir="/out",
                path="",
                full_bootstrap=True,
                key_id="dev-01",
                profile="client",
                output_json=False,
                console=_console(),
                compile_fn=compile_fn,
                keygen_fn=keygen_fn,
                sign_fn=sign_fn,
            )
        compile_fn.assert_called_once_with(profile="client")
        mock_gen.assert_called_once()
        mock_sign.assert_called_once_with(
            "dev-01", keygen_fn=keygen_fn, sign_fn=sign_fn
        )
        mock_handshake.assert_called_once()

    def test_full_bootstrap_announces_handshake_refresh(self) -> None:
        """Full bootstrap must say out loud that it rewrote the active M015
        handshake, since that silently invalidates a prior session's response."""
        console = _console()
        with (
            patch(
                "providence_cli.services.governance_generate_handlers.generate_artifacts"
            ),
            patch(
                "providence_cli.services.governance_generate_handlers.run_bootstrap_signing"
            ),
            patch(
                "providence_cli.services.governance_generate_handlers.complete_bootstrap_handshake"
            ),
        ):
            run_generate(
                output_dir="/out",
                path="",
                full_bootstrap=True,
                key_id="dev-01",
                profile="client",
                output_json=False,
                console=console,
            )
        assert "M015" in console.file.getvalue()

    def test_full_bootstrap_without_compile_fn(self) -> None:
        with (
            patch(
                "providence_cli.services.governance_generate_handlers.generate_artifacts"
            ),
            patch(
                "providence_cli.services.governance_generate_handlers.run_bootstrap_signing"
            ),
            patch(
                "providence_cli.services.governance_generate_handlers.complete_bootstrap_handshake"
            ),
        ):
            run_generate(
                output_dir="/out",
                path="",
                full_bootstrap=True,
                key_id="dev-01",
                profile="client",
                output_json=True,
                console=_console(),
            )
