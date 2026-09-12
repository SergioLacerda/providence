"""Unit tests for `providence runtime status` command.

Tests call the status() callback directly to bypass Typer's CliRunner,
patching AgentHandshakeProtocol.validate() and find_workspace_root.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from providence_cli.commands.runtime import status

pytestmark = pytest.mark.unit


def _make_ahp_patch(state: str) -> MagicMock:
    report = MagicMock()
    instance = MagicMock()
    instance.validate.return_value = (state, report)
    instance.format_combined_output.return_value = f"[state={state}]"
    return instance


class TestRuntimeStatusCommand:
    """providence runtime status exits with correct codes per AHP state."""

    def test_healthy_exits_0(self, tmp_path: Path) -> None:
        ahp_instance = _make_ahp_patch("HEALTHY")
        with (
            patch(
                "providence_core.utils.environment.find_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_core.governance.handshake.AgentHandshakeProtocol",
                return_value=ahp_instance,
            ),
            patch(
                "providence_cli.commands.runtime._emit_runtime_status", return_value={}
            ),
            patch(
                "providence_cli.commands.runtime._show_ask_confidence", return_value=""
            ),
            patch("providence_runtime.format_governance_footer", return_value=""),
        ):
            # HEALTHY → should not raise typer.Exit (exits 0 implicitly)
            status(ctx=MagicMock(), verbose=False, force=False, update_cache=False)

    def test_partial_exits_0(self, tmp_path: Path) -> None:
        ahp_instance = _make_ahp_patch("PARTIAL")
        with (
            patch(
                "providence_core.utils.environment.find_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_core.governance.handshake.AgentHandshakeProtocol",
                return_value=ahp_instance,
            ),
            patch(
                "providence_cli.commands.runtime._emit_runtime_status", return_value={}
            ),
            patch(
                "providence_cli.commands.runtime._show_ask_confidence", return_value=""
            ),
            patch("providence_runtime.format_governance_footer", return_value=""),
        ):
            status(ctx=MagicMock(), verbose=False, force=False, update_cache=False)

    def test_not_initialized_exits_1(self, tmp_path: Path) -> None:
        ahp_instance = _make_ahp_patch("NOT_INITIALIZED")
        with (
            pytest.raises(typer.Exit) as exc_info,
            patch(
                "providence_core.utils.environment.find_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_core.governance.handshake.AgentHandshakeProtocol",
                return_value=ahp_instance,
            ),
            patch(
                "providence_cli.commands.runtime._emit_runtime_status", return_value={}
            ),
            patch(
                "providence_cli.commands.runtime._show_ask_confidence", return_value=""
            ),
            patch("providence_runtime.format_governance_footer", return_value=""),
        ):
            status(ctx=MagicMock(), verbose=False, force=False, update_cache=False)
        assert exc_info.value.exit_code == 1

    def test_misconfigured_exits_2(self, tmp_path: Path) -> None:
        ahp_instance = _make_ahp_patch("MISCONFIGURED")
        with (
            pytest.raises(typer.Exit) as exc_info,
            patch(
                "providence_core.utils.environment.find_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_core.governance.handshake.AgentHandshakeProtocol",
                return_value=ahp_instance,
            ),
            patch(
                "providence_cli.commands.runtime._emit_runtime_status", return_value={}
            ),
            patch(
                "providence_cli.commands.runtime._show_ask_confidence", return_value=""
            ),
            patch("providence_runtime.format_governance_footer", return_value=""),
        ):
            status(ctx=MagicMock(), verbose=False, force=False, update_cache=False)
        assert exc_info.value.exit_code == 2

    def test_no_workspace_exits_3(self) -> None:
        ahp_instance = _make_ahp_patch("NOT_CONNECTED")
        with (
            pytest.raises(typer.Exit) as exc_info,
            patch(
                "providence_cli.commands.runtime.resolve_workspace_root",
                return_value=Path("/tmp/nonexistent"),
            ),
            patch(
                "providence_core.governance.handshake.AgentHandshakeProtocol",
                return_value=ahp_instance,
            ),
            patch(
                "providence_cli.commands.runtime._emit_runtime_status", return_value={}
            ),
            patch(
                "providence_cli.commands.runtime._show_ask_confidence", return_value=""
            ),
            patch("providence_runtime.format_governance_footer", return_value=""),
        ):
            status(ctx=MagicMock(), verbose=False, force=False, update_cache=False)
        assert exc_info.value.exit_code == 3


class TestShowAskConfidence:
    """Tests for the internal _show_ask_confidence helper."""

    def test_no_state_file_returns_silently(self, tmp_path: Path) -> None:
        from providence_cli.commands.runtime import _show_ask_confidence

        # No .providence/runtime/governance-state.json → should not raise
        _show_ask_confidence(tmp_path)

    def test_state_file_without_last_ask_returns_silently(self, tmp_path: Path) -> None:
        import json

        from providence_cli.commands.runtime import _show_ask_confidence

        runtime_dir = tmp_path / ".providence" / "runtime"
        runtime_dir.mkdir(parents=True)
        (runtime_dir / "governance-state.json").write_text(
            json.dumps({"state": "HEALTHY"}), encoding="utf-8"
        )
        _show_ask_confidence(tmp_path)

    def test_state_file_with_last_ask_echoes_fields(self, tmp_path: Path) -> None:
        import json

        from providence_cli.commands.runtime import _show_ask_confidence

        runtime_dir = tmp_path / ".providence" / "runtime"
        runtime_dir.mkdir(parents=True)
        last_ask = {
            "ts": "2025-01-01T00:00:00",
            "context_source": "compiled",
            "compiled_fingerprint_used": "abc123def",
            "mandates_loaded": 3,
            "agent_id": "test-agent",
        }
        (runtime_dir / "governance-state.json").write_text(
            json.dumps({"state": "HEALTHY", "last_ask": last_ask}), encoding="utf-8"
        )

        echoed: list[str] = []
        with patch("typer.echo", side_effect=lambda s, **kw: echoed.append(str(s))):
            _show_ask_confidence(tmp_path)

        combined = "\n".join(echoed)
        assert "ask_confidence" in combined
        assert "compiled" in combined

    def test_state_file_with_trace_id_shows_truncated(self, tmp_path: Path) -> None:
        import json

        from providence_cli.commands.runtime import _show_ask_confidence

        runtime_dir = tmp_path / ".providence" / "runtime"
        runtime_dir.mkdir(parents=True)
        last_ask = {
            "ts": "2025-01-01T00:00:00",
            "context_source": "none",
            "compiled_fingerprint_used": "",
            "mandates_loaded": 0,
            "agent_id": "agent-1",
            "trace_id": "abc123def456789",
        }
        (runtime_dir / "governance-state.json").write_text(
            json.dumps({"state": "HEALTHY", "last_ask": last_ask}), encoding="utf-8"
        )

        echoed: list[str] = []
        with patch("typer.echo", side_effect=lambda s, **kw: echoed.append(str(s))):
            _show_ask_confidence(tmp_path)

        combined = "\n".join(echoed)
        assert "trace_id" in combined
        assert "abc123de" in combined  # first 8 chars

    def test_malformed_json_does_not_raise(self, tmp_path: Path) -> None:
        from providence_cli.commands.runtime import _show_ask_confidence

        runtime_dir = tmp_path / ".providence" / "runtime"
        runtime_dir.mkdir(parents=True)
        (runtime_dir / "governance-state.json").write_text(
            "not-valid-json", encoding="utf-8"
        )

        # Should not raise
        _show_ask_confidence(tmp_path)


class TestDoUpdateCache:
    """Tests for _do_update_cache() helper."""

    def _write_gov_json(
        self, tmp_path: Path, enforcement_steps: list[str] | None
    ) -> Path:
        import json

        gov_dir = tmp_path / ".providence" / "compiled"
        gov_dir.mkdir(parents=True)
        item: dict = {
            "id": "M003",
            "type": "MANDATE",
            "title": "Context Awareness",
            "status": "active",
            "criticality": "high",
            "summary_minimal": "Context Awareness",
            "summary_runtime": None,
        }
        if enforcement_steps is not None:
            item["enforcement_steps"] = enforcement_steps
        payload = {
            "schema_version": "3.0",
            "fingerprint": "abc123",
            "generated_at": "2026-01-01T00:00:00",
            "items": [item],
        }
        gov_path = gov_dir / "governance-core.json"
        gov_path.write_text(json.dumps(payload), encoding="utf-8")
        return gov_path

    def test_happy_path_prints_quiz_and_touches_cache(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        from providence_cli.commands.runtime import _do_update_cache

        self._write_gov_json(
            tmp_path, ["Read .providence-cache.md", "Confirm mandate list"]
        )
        cache_file = tmp_path / ".providence" / "runtime" / ".providence-cache.md"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text("old", encoding="utf-8")
        old_mtime = cache_file.stat().st_mtime

        import time

        time.sleep(0.01)

        _do_update_cache(tmp_path)

        out = capsys.readouterr().out
        assert "M003" in out
        assert "Read .providence-cache.md" in out
        assert "Confirm mandate list" in out
        assert cache_file.stat().st_mtime > old_mtime

    def test_creates_cache_file_when_absent(self, tmp_path: Path) -> None:
        from providence_cli.commands.runtime import _do_update_cache

        self._write_gov_json(tmp_path, ["step one"])
        cache_file = tmp_path / ".providence" / "runtime" / ".providence-cache.md"
        assert not cache_file.exists()

        _do_update_cache(tmp_path)

        assert cache_file.exists()

    def test_missing_compiled_file_exits_1(self, tmp_path: Path) -> None:
        from providence_cli.commands.runtime import _do_update_cache

        with pytest.raises(typer.Exit) as exc_info:
            _do_update_cache(tmp_path)
        assert exc_info.value.exit_code == 1

    def test_missing_enforcement_steps_exits_1(self, tmp_path: Path) -> None:
        from providence_cli.commands.runtime import _do_update_cache

        self._write_gov_json(tmp_path, None)
        with pytest.raises(typer.Exit) as exc_info:
            _do_update_cache(tmp_path)
        assert exc_info.value.exit_code == 1


class TestMainExitHandling:
    """typer.Exit must not leak as a raw traceback regardless of typer version."""

    def test_typer_exit_is_caught_by_main(self) -> None:
        from unittest.mock import patch

        import typer

        from providence_cli.main import main

        with patch("providence_cli.main.app") as mock_app:
            mock_app.side_effect = typer.Exit(3)
            result = main()
        assert result == 3


class TestRuntimeStatusVerboseDiagnostics:
    """--verbose must print workspace root and diagnostic header."""

    def test_verbose_prints_workspace_root(self, tmp_path: Path, capsys) -> None:
        ahp_instance = _make_ahp_patch("HEALTHY")
        ahp_instance.skill_profile = "client"

        with (
            patch(
                "providence_core.utils.environment.find_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_cli.commands.runtime.enforce_path_policy",
                return_value=tmp_path,
            ),
            patch(
                "providence_core.governance.handshake.AgentHandshakeProtocol",
                return_value=ahp_instance,
            ),
            patch(
                "providence_cli.commands.runtime._emit_runtime_status", return_value={}
            ),
            patch(
                "providence_cli.commands.runtime._show_ask_confidence", return_value=""
            ),
            patch(
                "providence_cli.commands.runtime._check_cache_staleness",
                return_value={"stale": False},
            ),
            patch("providence_runtime.format_governance_footer", return_value=""),
        ):
            ctx = MagicMock()
            ctx.obj = {}
            ctx.params = {}
            ctx.info_name = "status"
            status(ctx=ctx, verbose=True, force=False, update_cache=False)

        captured = capsys.readouterr()
        assert "workspace root" in captured.out
        assert str(tmp_path) in captured.out

    def test_compact_mode_does_not_print_diagnostic_block(
        self, tmp_path: Path, capsys
    ) -> None:
        ahp_instance = _make_ahp_patch("HEALTHY")
        ahp_instance.skill_profile = "client"

        with (
            patch(
                "providence_core.utils.environment.find_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_cli.commands.runtime.enforce_path_policy",
                return_value=tmp_path,
            ),
            patch(
                "providence_core.governance.handshake.AgentHandshakeProtocol",
                return_value=ahp_instance,
            ),
            patch(
                "providence_cli.commands.runtime._emit_runtime_status", return_value={}
            ),
            patch(
                "providence_cli.commands.runtime._show_ask_confidence", return_value=""
            ),
            patch(
                "providence_cli.commands.runtime._check_cache_staleness",
                return_value={"stale": False},
            ),
            patch("providence_runtime.format_governance_footer", return_value=""),
        ):
            ctx = MagicMock()
            ctx.obj = {}
            ctx.params = {}
            ctx.info_name = "status"
            status(ctx=ctx, verbose=False, force=False, update_cache=False)

        captured = capsys.readouterr()
        assert "workspace root" not in captured.out
        assert "═══" not in captured.out


class TestHandshakeCacheNotConnected:
    """NOT_CONNECTED must never be read from or written to cache."""

    def test_load_cache_rejects_not_connected(self, tmp_path: Path) -> None:
        import json
        from datetime import datetime, timedelta

        from providence_core.governance.handshake_cache import HandshakeCache

        cache_dir = tmp_path / ".providence" / "runtime"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "governance-state.json"
        cache_file.write_text(
            json.dumps(
                {
                    "state": "NOT_CONNECTED",
                    "last_check": datetime.now().isoformat(),
                    "confidence": 0.0,
                    "gap_version": "1.0",
                    "status": "NOT_ACTIVE",
                    "checks": [],
                    "mandates_loaded": [],
                    "skill_profile": "default",
                    "spec_fingerprint": "",
                    "agent_id": "test",
                }
            ),
            encoding="utf-8",
        )
        cache = HandshakeCache(
            cache_file, cache_dir, timedelta(minutes=30), tmp_path, "test-agent"
        )
        assert cache.load_cache() is None

    def test_save_cache_skips_not_connected(self, tmp_path: Path) -> None:
        from datetime import timedelta

        from providence_core.governance.handshake_cache import HandshakeCache

        cache_dir = tmp_path / ".providence" / "runtime"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "governance-state.json"
        cache = HandshakeCache(
            cache_file, cache_dir, timedelta(minutes=30), tmp_path, "test-agent"
        )
        cache.save_cache("NOT_CONNECTED", [], 0.0, "default")
        assert not cache_file.exists()


class TestHandshakeAutoHeal:
    """Stale NOT_CONNECTED cache is discarded when .providence/ now exists."""

    def test_auto_heal_triggers_revalidation_when_sdd_exists(
        self, tmp_path: Path
    ) -> None:
        import json
        from datetime import datetime
        from unittest.mock import patch

        from providence_core.governance.handshake import AgentHandshakeProtocol

        # Create .providence/ so Layer 1 would pass
        (tmp_path / ".providence").mkdir()

        ahp = AgentHandshakeProtocol(project_root=tmp_path)

        # Manually write a stale NOT_CONNECTED cache file (pre-fix format)
        ahp.cache_dir.mkdir(parents=True, exist_ok=True)
        ahp.cache_file.write_text(
            json.dumps(
                {
                    "state": "NOT_CONNECTED",
                    "last_check": datetime.now().isoformat(),
                    "confidence": 0.0,
                    "gap_version": "1.0",
                    "status": "NOT_ACTIVE",
                    "checks": [],
                    "mandates_loaded": [],
                    "skill_profile": "default",
                    "spec_fingerprint": "",
                    "agent_id": "test",
                }
            ),
            encoding="utf-8",
        )

        # Patch all 4 layers to return non-NOT_CONNECTED states
        with (
            patch.object(
                ahp._validator, "layer_1_discovery", return_value=("CONNECTED", [])
            ),
            patch.object(
                ahp._validator,
                "layer_2_link_validation",
                return_value=("CONNECTED", []),
            ),
            patch.object(
                ahp._validator,
                "layer_3_runtime_validation",
                return_value=("INITIALIZED", []),
            ),
            patch.object(
                ahp._validator,
                "layer_4_governance_health",
                return_value=("UNKNOWN", []),
            ),
            patch.object(ahp._cache, "extract_mandates", return_value=[]),
            patch.object(ahp._cache, "compute_spec_fingerprint", return_value=""),
            patch.object(ahp._cache, "map_ahp_to_gap", return_value="NOT_ACTIVE"),
            patch.object(ahp._cache, "extract_skill_profile", return_value="default"),
        ):
            state, _ = ahp.validate()

        # Should NOT return the cached NOT_CONNECTED
        assert state != "NOT_CONNECTED"


class TestRuntimeStatusPathPolicy:
    """PathPolicyViolation must produce a clean error message, not a raw traceback."""

    def test_path_policy_violation_exits_2(self, tmp_path: Path) -> None:
        from providence_cli.utils.providence_authority import PathPolicyViolation

        with (
            patch(
                "providence_core.utils.environment.find_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_cli.commands.runtime.enforce_path_policy",
                side_effect=PathPolicyViolation(
                    requested_path=tmp_path,
                    reason="outside permitted paths",
                    hint="use SDD_WORKSPACE_ROOT",
                ),
            ),
            pytest.raises(typer.Exit) as exc_info,
        ):
            status(ctx=MagicMock(), verbose=False, force=False, update_cache=False)
        assert exc_info.value.exit_code == 2
