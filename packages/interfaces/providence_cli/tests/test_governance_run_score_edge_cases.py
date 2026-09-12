"""Tests for providence_cli.services.governance_scoring_output  run_governance_score edge cases."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from unittest.mock import patch

from rich.console import Console

from providence_cli.services.governance_scoring_output import run_governance_score
from providence_core.utils.environment import ProfileContext


def _console() -> Console:
    return Console(file=io.StringIO(), width=120)


class _FakeAHPReport:
    def __init__(self, confidence: float) -> None:
        self.confidence = confidence


class _FakeAHP:
    def __init__(
        self, project_root: Path | None = None, cache_ttl_minutes: int | None = None
    ) -> None:
        self.project_root = project_root
        self._confidence = _AHP_CONFIDENCE

    def validate(self, output_mode: str = "silent", force_recheck: bool = False):
        return ("HEALTHY", _FakeAHPReport(confidence=self._confidence))


_AHP_CONFIDENCE = 80.0


class TestRunGovernanceScoreEdgeCases:
    def test_low_ahp_confidence(self, tmp_path: Path) -> None:
        global _AHP_CONFIDENCE
        _AHP_CONFIDENCE = 30.0

        compiled_dir = tmp_path / "compiled"
        compiled_dir.mkdir()
        artifact = compiled_dir / "governance-core.json"
        fingerprint = "0123456789abcdef" + "extra"
        artifact.write_text(json.dumps({"fingerprint": fingerprint}), encoding="utf-8")

        profile_ctx = ProfileContext(
            type="client",
            name="test-ws",
            workspace_id="ws1",
            core_hash=fingerprint[:16],
            root=tmp_path,
        )

        captured: dict = {}

        def _capture_render(**kwargs):
            captured.update(kwargs)

        with (
            patch(
                "providence_core.utils.environment.resolve_profile",
                return_value=profile_ctx,
            ),
            patch(
                "providence_cli.utils.providence_authority.compiled_active_dir",
                return_value=compiled_dir,
            ),
            patch(
                "providence_core.governance.handshake.AgentHandshakeProtocol", _FakeAHP
            ),
            patch(
                "providence_cli.services.governance_scoring_output.render_governance_score_output",
                side_effect=_capture_render,
            ),
        ):
            run_governance_score(
                ws_root=tmp_path, verbose=False, threshold=50, console=_console()
            )

        finally_label = next(
            label for label, _, _ in captured["checks"] if label.startswith("AHP")
        )
        assert "30.0%" in finally_label
        checks_by_label = {label: passed for label, passed, _ in captured["checks"]}
        assert (
            checks_by_label[
                next(lbl for lbl in checks_by_label if lbl.startswith("AHP"))
            ]
            is False
        )
        # profile (30) + artifacts (30) + hash (20) pass, AHP (20) fails => 80/100
        assert captured["final_score"] == 80

    def test_hash_backward_compatibility(self, tmp_path: Path) -> None:
        global _AHP_CONFIDENCE
        _AHP_CONFIDENCE = 80.0

        compiled_dir = tmp_path / "compiled"
        compiled_dir.mkdir()
        artifact = compiled_dir / "governance-core.json"
        # No "fingerprint" key -> backward-compatibility branch computes sha256
        artifact_data = {"items": ["a", "b"]}
        artifact.write_text(json.dumps(artifact_data), encoding="utf-8")

        computed = hashlib.sha256(
            json.dumps(artifact_data, sort_keys=True).encode()
        ).hexdigest()[:16]

        profile_ctx = ProfileContext(
            type="client",
            name="test-ws",
            workspace_id="ws1",
            core_hash=computed,
            root=tmp_path,
        )

        captured: dict = {}

        def _capture_render(**kwargs):
            captured.update(kwargs)

        with (
            patch(
                "providence_core.utils.environment.resolve_profile",
                return_value=profile_ctx,
            ),
            patch(
                "providence_cli.utils.providence_authority.compiled_active_dir",
                return_value=compiled_dir,
            ),
            patch(
                "providence_core.governance.handshake.AgentHandshakeProtocol", _FakeAHP
            ),
            patch(
                "providence_cli.services.governance_scoring_output.render_governance_score_output",
                side_effect=_capture_render,
            ),
        ):
            run_governance_score(
                ws_root=tmp_path, verbose=False, threshold=50, console=_console()
            )

        checks_by_label = {label: passed for label, passed, _ in captured["checks"]}
        assert checks_by_label["core_hash matches artifact"] is True
        assert captured["final_score"] == 100

    def test_hash_check_exception_is_caught(self, tmp_path: Path) -> None:
        global _AHP_CONFIDENCE
        _AHP_CONFIDENCE = 80.0

        compiled_dir = tmp_path / "compiled"
        compiled_dir.mkdir()
        artifact = compiled_dir / "governance-core.json"
        artifact.write_text("not valid json", encoding="utf-8")

        profile_ctx = ProfileContext(
            type="client",
            name="test-ws",
            workspace_id="ws1",
            core_hash="0123456789abcdef",
            root=tmp_path,
        )

        captured: dict = {}

        def _capture_render(**kwargs):
            captured.update(kwargs)

        with (
            patch(
                "providence_core.utils.environment.resolve_profile",
                return_value=profile_ctx,
            ),
            patch(
                "providence_cli.utils.providence_authority.compiled_active_dir",
                return_value=compiled_dir,
            ),
            patch(
                "providence_core.governance.handshake.AgentHandshakeProtocol", _FakeAHP
            ),
            patch(
                "providence_cli.services.governance_scoring_output.render_governance_score_output",
                side_effect=_capture_render,
            ),
        ):
            run_governance_score(
                ws_root=tmp_path, verbose=False, threshold=50, console=_console()
            )

        checks_by_label = {label: passed for label, passed, _ in captured["checks"]}
        assert checks_by_label["core_hash matches artifact"] is False
