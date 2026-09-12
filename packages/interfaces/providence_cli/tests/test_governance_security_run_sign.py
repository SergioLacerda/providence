"""Tests for providence_cli.services.governance_security_handlers  run_sign orchestration."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from rich.console import Console

from providence_cli.services.governance_security_handlers import run_sign

pytestmark = pytest.mark.unit

_CONSOLE = Console(highlight=False)


# ---------------------------------------------------------------------------
# run_sign
# ---------------------------------------------------------------------------


class TestRunSign:
    def test_key_not_found_exits_1(self, tmp_path: Path) -> None:
        with pytest.raises(typer.Exit) as exc_info:
            run_sign(
                key_id="missing",
                key_path=None,
                ws_root=tmp_path,
                target_dir=tmp_path,
                targets=["artifact.json"],
                console=_CONSOLE,
            )
        assert exc_info.value.exit_code == 1

    def test_missing_custom_key_id_reports_expected_path(self, tmp_path: Path) -> None:
        output = StringIO()
        console = Console(file=output, highlight=False, force_terminal=False, width=240)

        with pytest.raises(typer.Exit) as exc_info:
            run_sign(
                key_id="my-org-01",
                key_path=None,
                ws_root=tmp_path,
                target_dir=tmp_path,
                targets=["artifact.json"],
                console=console,
            )

        assert exc_info.value.exit_code == 1
        text = output.getvalue()
        assert str(tmp_path / ".providence" / "trust" / "my-org-01.key") in text
        assert "providence governance keygen --key-id my-org-01" in text

    def test_custom_key_id_does_not_fall_back_to_dev_01(self, tmp_path: Path) -> None:
        custom_key = tmp_path / ".providence" / "trust" / "my-org-01.key"
        custom_key.parent.mkdir(parents=True)
        custom_key.write_text("priv", encoding="utf-8")

        with (
            patch(
                "providence_cli.services.governance_security_handlers._perform_artifact_signing",
                return_value=0,
            ) as signing,
            patch(
                "providence_cli.services.governance_security_handlers._update_trusted_keyring"
            ),
        ):
            run_sign(
                key_id="my-org-01",
                key_path=None,
                ws_root=tmp_path,
                target_dir=tmp_path,
                targets=["artifact.json"],
                console=_CONSOLE,
            )

        assert signing.call_args.kwargs["k_path"] == custom_key
        assert signing.call_args.kwargs["key_id"] == "my-org-01"

    def test_explicit_key_path_used(self, tmp_path: Path) -> None:
        k_path = tmp_path / "custom.key"
        k_path.write_text("priv", encoding="utf-8")

        with (
            patch(
                "providence_cli.services.governance_security_handlers._perform_artifact_signing",
                return_value=0,
            ),
            patch(
                "providence_cli.services.governance_security_handlers._update_trusted_keyring"
            ),
        ):
            run_sign(
                key_id="custom",
                key_path=str(k_path),
                ws_root=tmp_path,
                target_dir=tmp_path,
                targets=[],
                console=_CONSOLE,
            )

    def test_no_artifacts_prints_warning(self, tmp_path: Path) -> None:
        k_path = tmp_path / ".providence" / "trust" / "nokey.key"
        k_path.parent.mkdir(parents=True)
        k_path.write_text("priv", encoding="utf-8")

        with (
            patch(
                "providence_cli.services.governance_security_handlers._perform_artifact_signing",
                return_value=0,
            ),
            patch(
                "providence_cli.services.governance_security_handlers._update_trusted_keyring"
            ),
        ):
            run_sign(
                key_id="nokey",
                key_path=None,
                ws_root=tmp_path,
                target_dir=tmp_path,
                targets=[],
                console=_CONSOLE,
            )

    def test_success_prints_summary(self, tmp_path: Path) -> None:
        k_path = tmp_path / ".providence" / "trust" / "testkey.key"
        k_path.parent.mkdir(parents=True)
        k_path.write_text("priv", encoding="utf-8")

        with (
            patch(
                "providence_cli.services.governance_security_handlers._perform_artifact_signing",
                return_value=2,
            ),
            patch(
                "providence_cli.services.governance_security_handlers._update_trusted_keyring"
            ),
        ):
            run_sign(
                key_id="testkey",
                key_path=None,
                ws_root=tmp_path,
                target_dir=tmp_path,
                targets=["a.json", "b.json"],
                console=_CONSOLE,
            )
