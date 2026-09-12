"""Tests for providence_cli.services.governance_security_handlers  keygen and compiled-dir resolution."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from rich.console import Console

from providence_cli.services.governance_security_handlers import (
    resolve_compiled_dir,
    run_keygen,
)

pytestmark = pytest.mark.unit

_CONSOLE = Console(highlight=False)


# ---------------------------------------------------------------------------
# run_keygen
# ---------------------------------------------------------------------------


class TestRunKeygen:
    def test_key_already_exists_exits_0(self, tmp_path: Path) -> None:
        out = tmp_path / "keys"
        out.mkdir()
        (out / "mykey.key").write_text("existing", encoding="utf-8")
        with pytest.raises(typer.Exit) as exc_info:
            run_keygen(key_id="mykey", output_dir=str(out), console=_CONSOLE)
        assert exc_info.value.exit_code == 0

    def test_generates_key_pair_via_native_backend(self, tmp_path: Path) -> None:
        out = tmp_path / "keys"
        mock_runner = MagicMock()
        with patch(
            "providence_core.utils.compiler_runner.CompilerRunner",
            return_value=mock_runner,
        ):
            run_keygen(key_id="newkey", output_dir=str(out), console=_CONSOLE)
        mock_runner.keygen.assert_called_once_with(
            private_key_path=out / "newkey.key",
            public_key_path=out / "newkey.pub.pem",
        )

    def test_creates_output_dir(self, tmp_path: Path) -> None:
        out = tmp_path / "deep" / "keys"
        mock_runner = MagicMock()
        with patch(
            "providence_core.utils.compiler_runner.CompilerRunner",
            return_value=mock_runner,
        ):
            run_keygen(key_id="mykey", output_dir=str(out), console=_CONSOLE)
        assert out.exists()

    def test_backend_unavailable_exits_1(self, tmp_path: Path) -> None:
        out = tmp_path / "keys"
        with (
            patch(
                "providence_core.utils.compiler_runner.CompilerRunner",
                side_effect=Exception("binary not found"),
            ),
            pytest.raises(typer.Exit) as exc_info,
        ):
            run_keygen(key_id="newkey", output_dir=str(out), console=_CONSOLE)
        assert exc_info.value.exit_code == 1

    def test_keygen_failure_exits_1(self, tmp_path: Path) -> None:
        out = tmp_path / "keys"
        mock_runner = MagicMock()
        mock_runner.keygen.side_effect = Exception("keygen failed")
        with (
            patch(
                "providence_core.utils.compiler_runner.CompilerRunner",
                return_value=mock_runner,
            ),
            pytest.raises(typer.Exit) as exc_info,
        ):
            run_keygen(key_id="newkey", output_dir=str(out), console=_CONSOLE)
        assert exc_info.value.exit_code == 1


# ---------------------------------------------------------------------------
# resolve_compiled_dir
# ---------------------------------------------------------------------------


class TestResolveCompiledDir:
    def test_explicit_path_returned(self, tmp_path: Path) -> None:
        compiled = tmp_path / "compiled"
        compiled.mkdir()
        result = resolve_compiled_dir(
            ws_root=tmp_path, compiled_dir=str(compiled), console=_CONSOLE
        )
        assert result == compiled

    def test_default_path_used_when_exists(self, tmp_path: Path) -> None:
        compiled = tmp_path / ".providence" / "compiled"
        compiled.mkdir(parents=True)
        result = resolve_compiled_dir(
            ws_root=tmp_path, compiled_dir=None, console=_CONSOLE
        )
        assert result == compiled

    def test_fallback_to_sdd_paths_when_default_missing(self, tmp_path: Path) -> None:
        master_compiled = tmp_path / "master_compiled"
        master_compiled.mkdir()
        mock_profile = MagicMock(type="master")
        mock_paths = {
            "master_compiled": master_compiled,
            "client_compiled": tmp_path / "nope",
        }
        with (
            patch(
                "providence_core.utils.environment.resolve_profile",
                return_value=mock_profile,
            ),
            patch(
                "providence_core.utils.environment.get_sdd_paths",
                return_value=mock_paths,
            ),
        ):
            result = resolve_compiled_dir(
                ws_root=tmp_path, compiled_dir=None, console=_CONSOLE
            )
        assert result == master_compiled

    def test_fallback_profile_exception_defaults_to_master(
        self, tmp_path: Path
    ) -> None:
        master_compiled = tmp_path / "master_compiled"
        master_compiled.mkdir()
        mock_paths = {
            "master_compiled": master_compiled,
            "client_compiled": tmp_path / "nope",
        }
        with (
            patch(
                "providence_core.utils.environment.resolve_profile",
                side_effect=Exception("fail"),
            ),
            patch(
                "providence_core.utils.environment.get_sdd_paths",
                return_value=mock_paths,
            ),
        ):
            result = resolve_compiled_dir(
                ws_root=tmp_path, compiled_dir=None, console=_CONSOLE
            )
        assert result == master_compiled

    def test_not_found_exits_1(self, tmp_path: Path) -> None:
        mock_paths = {
            "master_compiled": tmp_path / "nope1",
            "client_compiled": tmp_path / "nope2",
        }
        with (
            patch(
                "providence_core.utils.environment.resolve_profile",
                side_effect=Exception,
            ),
            patch(
                "providence_core.utils.environment.get_sdd_paths",
                return_value=mock_paths,
            ),
            pytest.raises(typer.Exit) as exc_info,
        ):
            resolve_compiled_dir(ws_root=tmp_path, compiled_dir=None, console=_CONSOLE)
        assert exc_info.value.exit_code == 1
