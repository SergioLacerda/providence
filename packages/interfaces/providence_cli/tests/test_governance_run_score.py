"""Tests for providence_cli.services.governance_scoring_output  run_governance_score basics."""

from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import patch

from rich.console import Console

from providence_cli.services.governance_scoring_output import run_governance_score
from providence_core.utils.environment import (
    ProfileContext,
    WorkspaceNotInitializedError,
)


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


class TestRunGovernanceScore:
    def test_all_checks_pass_with_artifact_fingerprint(self, tmp_path: Path) -> None:
        global _AHP_CONFIDENCE
        _AHP_CONFIDENCE = 80.0

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
                ws_root=tmp_path, verbose=False, threshold=80, console=_console()
            )

        assert captured["final_score"] == 100
        assert all(passed for _, passed, _ in captured["checks"])

    def test_profile_not_initialized(self, tmp_path: Path) -> None:
        global _AHP_CONFIDENCE
        _AHP_CONFIDENCE = 80.0

        compiled_dir = tmp_path / "compiled"
        compiled_dir.mkdir()
        artifact = compiled_dir / "governance-core.json"
        artifact.write_text(json.dumps({"fingerprint": "abc"}), encoding="utf-8")

        captured: dict = {}

        def _capture_render(**kwargs):
            captured.update(kwargs)

        with (
            patch(
                "providence_core.utils.environment.resolve_profile",
                side_effect=WorkspaceNotInitializedError("not initialized"),
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
        assert checks_by_label[".providence/profile valid"] is False
        assert checks_by_label["core_hash matches artifact"] is False
        # profile (30) fails, artifacts (30) + AHP (20) pass => 50/100
        assert captured["final_score"] == 50

    def test_artifacts_missing(self, tmp_path: Path) -> None:
        global _AHP_CONFIDENCE
        _AHP_CONFIDENCE = 80.0

        compiled_dir = tmp_path / "compiled"
        compiled_dir.mkdir()  # no governance-core.json written

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
        assert checks_by_label["governance artifacts compiled"] is False
        assert checks_by_label["core_hash matches artifact"] is False
        # profile (30) + AHP (20) pass, artifacts (30) fails => 50/100
        assert captured["final_score"] == 50
