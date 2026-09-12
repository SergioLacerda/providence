"""Unit tests for providence_cli.utils.profile — ProfilePolicy adapters and governance_gate."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import click
import pytest

from providence_cli.utils.profile import (
    ClientAdapter,
    MasterAdapter,
    enforce_profile_policy,
    get_active_profile,
    get_adapter,
    governance_gate,
)

pytestmark = pytest.mark.unit


class TestGetAdapter:
    """get_adapter returns correct policy for known profiles."""

    def test_master_returns_master_adapter(self) -> None:
        assert get_adapter("master") is MasterAdapter

    def test_client_returns_client_adapter(self) -> None:
        assert get_adapter("client") is ClientAdapter

    def test_unknown_defaults_to_client(self) -> None:
        assert get_adapter("unknown-profile") is ClientAdapter

    def test_master_allows_governance(self) -> None:
        assert "governance" in MasterAdapter.allowed_commands

    def test_client_blocks_release(self) -> None:
        assert "release" in ClientAdapter.blocked_commands


class TestEnforceProfilePolicy:
    """enforce_profile_policy raises Exit for blocked commands, echoes for warned."""

    def test_blocked_command_raises_exit(self) -> None:
        ctx = MagicMock(spec=click.Context)
        ctx.obj = {"profile": "client"}
        with pytest.raises(click.exceptions.Exit):
            enforce_profile_policy("release", ctx)

    def test_allowed_command_passes_silently(self) -> None:
        ctx = MagicMock(spec=click.Context)
        ctx.obj = {"profile": "master"}
        # Should not raise
        enforce_profile_policy("governance", ctx)

    def test_warned_command_echoes_warning(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        ctx = MagicMock(spec=click.Context)
        ctx.obj = {"profile": "master"}
        enforce_profile_policy("wizard", ctx)
        # Warning goes to stdout via click.echo
        out, err = capsys.readouterr()
        assert "wizard" in out or "wizard" in err


class TestGetActiveProfile:
    """get_active_profile reads from ctx.obj or falls back to env."""

    def test_reads_from_ctx_obj(self) -> None:
        ctx = MagicMock(spec=click.Context)
        ctx.obj = {"profile": "master"}
        assert get_active_profile(ctx) == "master"

    def test_returns_client_for_none_ctx(self) -> None:
        # Without context, detect_profile falls back to "client"
        with patch(
            "providence_core.utils.environment.detect_profile", return_value="client"
        ):
            result = get_active_profile(None)
        assert result == "client"


class TestGovernanceGate:
    """governance_gate skips exempt commands and never raises on errors."""

    def _make_ctx(
        self, command: str, obj: dict[str, object] | None = None
    ) -> click.Context:
        ctx = MagicMock(spec=click.Context)
        ctx.args = [command]
        ctx.obj = obj or {}
        return ctx

    def test_exempt_init_skips_gate(self) -> None:
        ctx = self._make_ctx("init")
        # Should return immediately — no AHP import attempted
        with patch(
            "providence_core.governance.handshake.AgentHandshakeProtocol"
        ) as mock_ahp:
            governance_gate(ctx)
            mock_ahp.assert_not_called()

    def test_exempt_version_skips_gate(self) -> None:
        ctx = self._make_ctx("version")
        with patch(
            "providence_core.governance.handshake.AgentHandshakeProtocol"
        ) as mock_ahp:
            governance_gate(ctx)
            mock_ahp.assert_not_called()

    def test_never_raises_on_import_error(self) -> None:
        ctx = self._make_ctx("doctor")
        with (
            patch("providence_cli.utils.profile.governance_gate.__module__"),
            patch(
                "providence_core.governance.handshake.AgentHandshakeProtocol",
                side_effect=RuntimeError("boom"),
            ),
        ):
            # Should not propagate
            governance_gate(ctx)

    def test_healthy_state_silent(self, capsys: pytest.CaptureFixture[str]) -> None:
        ctx = self._make_ctx("doctor", obj={"profile": "client", "root": None})
        mock_report = MagicMock()
        mock_report.confidence = 100.0
        with patch(
            "providence_core.governance.handshake.AgentHandshakeProtocol"
        ) as mock_ahp_cls:
            instance = mock_ahp_cls.return_value
            instance.validate.return_value = ("HEALTHY", mock_report)
            with patch("providence_runtime.telemetry.TelemetrySink.emit"):
                governance_gate(ctx)
        out, err = capsys.readouterr()
        assert "WARN" not in out
        assert "WARN" not in err

    def test_misconfigured_state_warns(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        ctx = self._make_ctx("doctor", obj={"profile": "client", "root": None})
        mock_report = MagicMock()
        with patch(
            "providence_core.governance.handshake.AgentHandshakeProtocol"
        ) as mock_ahp_cls:
            instance = mock_ahp_cls.return_value
            instance.validate.return_value = ("MISCONFIGURED", mock_report)
            with (
                patch("providence_runtime.telemetry.TelemetrySink.emit"),
                pytest.raises(click.exceptions.Exit),
            ):
                governance_gate(ctx)
        out, err = capsys.readouterr()
        assert "MISCONFIGURED" in out or "MISCONFIGURED" in err

    def test_partial_sensitive_command_emits_soft_directive(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # 'wizard' is sensitive and NOT exempt
        ctx = self._make_ctx("wizard", obj={"profile": "client", "root": None})
        ctx.args = ["wizard"]
        mock_report = MagicMock()
        with patch(
            "providence_core.governance.handshake.AgentHandshakeProtocol"
        ) as mock_ahp_cls:
            instance = mock_ahp_cls.return_value
            instance.validate.return_value = ("PARTIAL", mock_report)
            with patch(
                "providence_runtime.telemetry.TelemetrySink.emit"
            ) as mock_append:
                governance_gate(ctx)
        out, err = capsys.readouterr()
        combined = out + err
        assert "SOFT [governance]" in combined
        assert "comando sensivel" in combined

        events = [call.args[0].event for call in mock_append.call_args_list]
        assert "governance.checked" in events
        assert "governance.violation" in events
