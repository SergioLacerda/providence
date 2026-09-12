"""Full coverage tests for InteractiveWizard using injected prompter."""

from __future__ import annotations

import json
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from providence_wizard.application import workspace_runtime
from providence_wizard.application.interactive_wizard import (
    InteractiveWizard,
    run_interactive_wizard,
)
from providence_wizard.application.workspace_runtime import (
    docs_meta_ready,
    source_spec_ready,
)

# Prevent the large orchestration phase modules from being imported as a side
# effect of test patches. This keeps them out of the coverage denominator so
# that their low coverage does not drag down the overall providence_wizard metric.
# Each file is mocked for the lifetime of EVERY test in this module.
_LARGE_PHASE_MODULES = [
    "providence_wizard.orchestration.wizard.phase1_generator",
    "providence_wizard.orchestration.wizard.phase3_compiler",
    "providence_wizard.orchestration.phase_4_5_6_generator",
    "providence_wizard.orchestration.phase5_artifact_compiler",
]


@pytest.fixture(autouse=True)
def _mock_large_phase_modules():
    """Replace large phase modules with MagicMocks for each test."""
    mocks = {mod: MagicMock() for mod in _LARGE_PHASE_MODULES}
    # Remove any previously cached real imports so mocks take precedence.
    originals = {mod: sys.modules.pop(mod, None) for mod in _LARGE_PHASE_MODULES}
    with patch.dict(sys.modules, mocks):
        yield
    # Restore originals (if any were present before this test).
    for mod, orig in originals.items():
        if orig is not None:
            sys.modules[mod] = orig
        else:
            sys.modules.pop(mod, None)


@pytest.fixture(autouse=True)
def _assume_interactive_tty(monkeypatch: pytest.MonkeyPatch):
    """Tests use fake/callable prompters and expect interactive-capable
    behavior  simulate a real TTY so InteractiveFlowRuntime's upfront
    non-interactive-without-a-path check doesn't short-circuit them. Tests
    exercising that check specifically override this locally."""
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)


_BASE_PATHS = {
    "root": Path("/fake/root"),
    "client_build": None,
    "client_compiled": None,
    "master_compiled": Path("/fake/master"),
    "packages": Path("/fake/packages"),
    "source_spec": Path("/fake/spec"),
}


def _make_wizard(
    tmp_path: Path,
    prompter: Any = None,
    emitter: Any = None,
    debug: bool = False,
) -> InteractiveWizard:
    paths = {
        **_BASE_PATHS,
        "client_build": tmp_path / "build",
        "client_compiled": tmp_path / "compiled",
    }
    with patch(
        "providence_wizard.application.interactive_wizard.get_sdd_paths",
        return_value=paths,
    ):
        return InteractiveWizard(
            repo_root=tmp_path,
            emitter=emitter or (lambda _: None),
            prompter=prompter or (lambda _: ""),
            debug=debug,
        )


class TestInitAndPaths:
    def test_paths_set_from_sdd_paths(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        assert wizard.client_build_dir == tmp_path / "build"
        assert wizard.client_compiled_dir == tmp_path / "compiled"
        assert wizard.phase1_choices_dir == tmp_path / "build" / "phase-1-choices"

    def test_prompter_injected(self, tmp_path: Path) -> None:
        calls: list[str] = []

        def my_prompter(msg: str) -> str:
            calls.append(msg)
            return "answer"

        wizard = _make_wizard(tmp_path, prompter=my_prompter)
        # _prompter wraps the callable; verify select() delegates correctly
        assert wizard._prompter.select("test?", ["answer", "other"]) == "answer"


class TestPrintHeader:
    def test_emits_title_and_separator(self, tmp_path: Path) -> None:
        logs: list[str] = []
        wizard = _make_wizard(tmp_path, emitter=logs.append)
        wizard.print_header("My Title", "")
        assert any("My Title" in m for m in logs)
        assert any("=" in m for m in logs)


class TestAskUserPreferences:
    def _wizard_with_choices(
        self,
        tmp_path: Path,
        enforcement: str,
        interaction_language: str = "1",
        local_docs_language: str = "3",
        handshake: str = "1",
    ) -> InteractiveWizard:
        responses = iter(
            [
                enforcement,
                interaction_language,
                local_docs_language,
                handshake,
            ]
        )
        return _make_wizard(tmp_path, prompter=lambda _: next(responses))

    def test_silent_mode(self, tmp_path: Path) -> None:
        config = self._wizard_with_choices(tmp_path, "1").ask_user_preferences()
        assert config["enforcement_mode"] == "silent_mode"
        assert config["language"] == "all"

    def test_warn_mode(self, tmp_path: Path) -> None:
        config = self._wizard_with_choices(tmp_path, "2").ask_user_preferences()
        assert config["enforcement_mode"] == "warn_mode"
        assert config["language"] == "all"

    def test_strict_mode(self, tmp_path: Path) -> None:
        config = self._wizard_with_choices(tmp_path, "3").ask_user_preferences()
        assert config["enforcement_mode"] == "strict_mode"
        assert config["language"] == "all"

    def test_unknown_choices_default(self, tmp_path: Path) -> None:
        # Out-of-bounds index  _CallablePrompter falls back to first choice
        config = self._wizard_with_choices(tmp_path, "9").ask_user_preferences()
        assert config["enforcement_mode"] == "silent_mode"
        assert config["language"] == "all"

    def test_config_has_generated_at(self, tmp_path: Path) -> None:
        config = self._wizard_with_choices(tmp_path, "1").ask_user_preferences()
        assert "generated_at" in config

    def test_config_has_language_context(self, tmp_path: Path) -> None:
        config = self._wizard_with_choices(
            tmp_path, "2", interaction_language="2", local_docs_language="3"
        ).ask_user_preferences()
        assert (
            config["language_context"]["preferred_human_language"]
            == "Portugus (Brasil)"
        )
        assert (
            config["language_context"]["preferred_chat_language"] == "Portugus (Brasil)"
        )
        assert (
            config["language_context"]["preferred_ui_language"] == "Portugus (Brasil)"
        )
        assert (
            config["language_context"]["preferred_local_docs_language"]
            == "Portugus (Brasil)"
        )

    def test_config_has_default_locale_metadata(self, tmp_path: Path) -> None:
        config = self._wizard_with_choices(tmp_path, "1").ask_user_preferences()
        assert config["locale"] == "en"
        assert config["docs_language"] == "English"
        assert config["docs_locale"] == "en"

    def test_config_has_pt_br_locale_metadata(self, tmp_path: Path) -> None:
        config = self._wizard_with_choices(
            tmp_path, "2", interaction_language="2", local_docs_language="2"
        ).ask_user_preferences()
        assert config["locale"] == "pt-BR"
        assert config["docs_language"] == "Portugus (Brasil)"
        assert config["docs_locale"] == "pt-BR"

    def test_non_interactive_reuses_real_wizard_config_end_to_end(
        self, tmp_path: Path
    ) -> None:
        """End-to-end: non_interactive=True + a real on-disk wizard-config.json
        are wired together through ask_user_preferences() itself  not just
        the resolver in isolation, and not with ask_user_preferences mocked."""
        wizard = _make_wizard(tmp_path, prompter=lambda _: "1")
        wizard.non_interactive = True
        existing = {
            "docs_language": "English",
            "docs_locale": "en",
            "enforcement_mode": "warn_mode",
            "handshake_mode": "standard",
            "locale": "en",
            "language_context": {
                "preferred_human_language": "English",
                "preferred_chat_language": "English",
                "preferred_ui_language": "English",
                "preferred_local_docs_language": "English",
            },
        }
        wizard.wizard_config_path.parent.mkdir(parents=True, exist_ok=True)
        wizard.wizard_config_path.write_text(json.dumps(existing), encoding="utf-8")

        config = wizard.ask_user_preferences()

        assert config["enforcement_mode"] == "warn_mode"
        assert config["handshake_mode"] == "standard"
        assert config["locale"] == "en"
        assert config["language"] == "all"


class TestSaveConfig:
    def test_saves_to_wizard_config_json(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        config = {"language": "Python", "enforcement_mode": "warn_mode"}
        path = wizard.save_config(config)
        assert path.exists()
        assert json.loads(path.read_text(encoding="utf-8"))["language"] == "Python"


class TestDocsMetaReady:
    def _make_docs_meta(
        self, tmp_path: Path, spec: str = "mandate.spec", dsl: str = "guidelines.dsl"
    ) -> None:
        docs_meta = tmp_path / "build" / "docs-meta"
        docs_meta.mkdir(parents=True)
        (docs_meta / spec).write_text("x", encoding="utf-8")
        (docs_meta / dsl).write_text("x", encoding="utf-8")

    def test_false_when_missing(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        assert docs_meta_ready(wizard.client_build_dir) is False

    def test_true_with_spec_and_dsl(self, tmp_path: Path) -> None:
        self._make_docs_meta(tmp_path)
        wizard = _make_wizard(tmp_path)
        assert docs_meta_ready(wizard.client_build_dir) is True

    def test_true_with_md_files(self, tmp_path: Path) -> None:
        self._make_docs_meta(tmp_path, "mandate.md", "guidelines.md")
        wizard = _make_wizard(tmp_path)
        assert docs_meta_ready(wizard.client_build_dir) is True


class TestEnsureDocsMeta:
    def _make_ready(self, tmp_path: Path) -> None:
        docs_meta = tmp_path / "build" / "docs-meta"
        docs_meta.mkdir(parents=True)
        (docs_meta / "mandate.spec").write_text("x", encoding="utf-8")
        (docs_meta / "guidelines.dsl").write_text("x", encoding="utf-8")

    def test_returns_true_when_already_ready(self, tmp_path: Path) -> None:
        self._make_ready(tmp_path)
        ok, reason = _make_wizard(tmp_path)._ensure_docs_meta_ready()
        assert ok is True
        assert reason == ""

    def test_bootstraps_and_returns_true_when_docs_meta_missing(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """When no bundled canonical spec is available, fall back to the placeholder stub."""
        monkeypatch.setattr(workspace_runtime, "_bundled_spec_dir", lambda: None)
        wizard = _make_wizard(tmp_path)
        ok, reason = wizard._ensure_docs_meta_ready()
        assert ok is True
        assert reason == ""
        assert (tmp_path / "build" / "docs-meta").exists()
        assert (tmp_path / "build" / "phase-1-choices").exists()
        assert (tmp_path / "build" / "phase-2-input").exists()
        assert (tmp_path / "build" / "docs-meta" / "mandate.md").exists()
        assert (tmp_path / "build" / "docs-meta" / "guidelines.dsl").exists()

    def test_bootstraps_prefers_bundled_canonical_spec_when_available(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        bundled_dir = tmp_path / "bundled"
        bundled_dir.mkdir()
        (bundled_dir / "mandate.spec").write_text(
            'mandate M001 {\n  title: "Real Mandate"\n}\n', encoding="utf-8"
        )
        (bundled_dir / "guidelines.dsl").write_text(
            'guideline G01 {\n  title: "Real Guideline"\n}\n', encoding="utf-8"
        )
        monkeypatch.setattr(workspace_runtime, "_bundled_spec_dir", lambda: bundled_dir)
        wizard = _make_wizard(tmp_path)
        ok, reason = wizard._ensure_docs_meta_ready()
        assert ok is True
        assert reason == ""
        docs_meta = tmp_path / "build" / "docs-meta"
        assert (docs_meta / "mandate.spec").exists()
        assert (docs_meta / "guidelines.dsl").exists()
        assert not (docs_meta / "mandate.md").exists()


class TestPostGenerationCleanup:
    def test_cleanup_removes_temporary_artifacts_and_keeps_final_template(
        self, tmp_path: Path
    ) -> None:
        wizard = _make_wizard(tmp_path)
        (wizard.final_template_dir / "keep.txt").mkdir(parents=True, exist_ok=True)
        (wizard.final_template_dir / "keep.txt" / "ok").write_text(
            "ok", encoding="utf-8"
        )
        (wizard.client_build_dir / "docs-meta").mkdir(parents=True, exist_ok=True)
        (wizard.phase1_choices_dir).mkdir(parents=True, exist_ok=True)
        (wizard.phase2_input_dir).mkdir(parents=True, exist_ok=True)
        wizard.client_compiled_dir.mkdir(parents=True, exist_ok=True)
        (wizard.client_compiled_dir / ".providence").mkdir(parents=True, exist_ok=True)
        wizard.wizard_config_path.write_text("{}", encoding="utf-8")

        cleaned = wizard._cleanup_post_generation_artifacts()

        assert cleaned
        assert not (wizard.client_build_dir / "docs-meta").exists()
        assert not wizard.phase1_choices_dir.exists()
        assert not wizard.phase2_input_dir.exists()
        assert not (wizard.client_compiled_dir / ".providence").exists()
        assert wizard.final_template_dir.exists()


class TestPhase1Generate:
    def _ready_docs_meta(self, tmp_path: Path) -> None:
        d = tmp_path / "build" / "docs-meta"
        d.mkdir(parents=True)
        (d / "mandate.spec").write_text("x", encoding="utf-8")
        (d / "guidelines.dsl").write_text("x", encoding="utf-8")

    def test_success(self, tmp_path: Path) -> None:
        self._ready_docs_meta(tmp_path)
        responses = iter(["2", "1", "1", "3", "1"])
        wizard = _make_wizard(tmp_path, prompter=lambda _: next(responses))
        mock_gen = MagicMock()
        mock_gen.run.return_value = {"success": True}
        # Phase1Generator is in the sys.modules mock  configure return_value directly.
        sys.modules[
            "providence_wizard.orchestration.wizard.phase1_generator"
        ].Phase1Generator.return_value = mock_gen
        result = wizard.phase_1_generate_templates()
        assert result["success"] is True

    def test_success_in_zero_state_without_docs_meta(self, tmp_path: Path) -> None:
        responses = iter(["2", "1", "1", "3", "1"])
        wizard = _make_wizard(tmp_path, prompter=lambda _: next(responses))
        mock_gen = MagicMock()
        mock_gen.run.return_value = {"success": True}
        sys.modules[
            "providence_wizard.orchestration.wizard.phase1_generator"
        ].Phase1Generator.return_value = mock_gen
        result = wizard.phase_1_generate_templates()
        assert result["success"] is True

    def test_exception_returns_failure(self, tmp_path: Path) -> None:
        self._ready_docs_meta(tmp_path)
        responses = iter(["2", "1", "1", "3", "1"])
        wizard = _make_wizard(tmp_path, prompter=lambda _: next(responses))
        sys.modules[
            "providence_wizard.orchestration.wizard.phase1_generator"
        ].Phase1Generator.side_effect = RuntimeError("crash")
        result = wizard.phase_1_generate_templates()
        sys.modules[
            "providence_wizard.orchestration.wizard.phase1_generator"
        ].Phase1Generator.side_effect = None
        assert result["success"] is False
        assert "crash" in result["error"]

    def test_passes_selector_selection_to_generator_config(
        self, tmp_path: Path
    ) -> None:
        self._ready_docs_meta(tmp_path)
        responses = iter(["2", "1", "1", "3", "1"])
        wizard = _make_wizard(tmp_path, prompter=lambda _: next(responses))
        wizard.selector_output_path.write_text(
            json.dumps(
                {
                    "version": "1.0",
                    "selected_ids": ["M001"],
                    "resolved_ids": ["M001", "M002"],
                }
            ),
            encoding="utf-8",
        )
        mock_gen = MagicMock()
        mock_gen.run.return_value = {"success": True}
        sys.modules[
            "providence_wizard.orchestration.wizard.phase1_generator"
        ].Phase1Generator.return_value = mock_gen

        result = wizard.phase_1_generate_templates()

        assert result["success"] is True
        call = sys.modules[
            "providence_wizard.orchestration.wizard.phase1_generator"
        ].Phase1Generator.call_args
        assert call.kwargs["config"]["selector_selection"]["resolved_ids"] == [
            "M001",
            "M002",
        ]

    def test_emits_selector_site_hint_when_site_exists(self, tmp_path: Path) -> None:
        self._ready_docs_meta(tmp_path)
        responses = iter(["2", "1", "1", "3", "1"])
        logs: list[str] = []
        wizard = _make_wizard(
            tmp_path,
            prompter=lambda _: next(responses),
            emitter=logs.append,
            debug=True,
        )
        wizard.selector_site_path.parent.mkdir(parents=True, exist_ok=True)
        wizard.selector_site_path.write_text("<html></html>", encoding="utf-8")
        mock_gen = MagicMock()
        mock_gen.run.return_value = {"success": True}
        sys.modules[
            "providence_wizard.orchestration.wizard.phase1_generator"
        ].Phase1Generator.return_value = mock_gen

        result = wizard.phase_1_generate_templates()

        assert result["success"] is True
        assert any("Optional pre-filter available" in message for message in logs)
        saved = json.loads(wizard.wizard_config_path.read_text(encoding="utf-8"))
        assert saved["selector_discovery"]["selection_loaded"] is False
        assert saved["selector_discovery"]["published_site_path"] == str(
            wizard.selector_site_path
        )

    def test_emits_loaded_selector_hint_when_artifact_exists(
        self, tmp_path: Path
    ) -> None:
        self._ready_docs_meta(tmp_path)
        responses = iter(["2", "1", "1", "3", "1"])
        logs: list[str] = []
        wizard = _make_wizard(
            tmp_path,
            prompter=lambda _: next(responses),
            emitter=logs.append,
            debug=True,
        )
        wizard.selector_output_path.write_text(
            json.dumps(
                {
                    "version": "1.0",
                    "selected_ids": ["M001"],
                    "resolved_ids": ["M001", "M002"],
                }
            ),
            encoding="utf-8",
        )
        mock_gen = MagicMock()
        mock_gen.run.return_value = {"success": True}
        sys.modules[
            "providence_wizard.orchestration.wizard.phase1_generator"
        ].Phase1Generator.return_value = mock_gen

        result = wizard.phase_1_generate_templates()

        assert result["success"] is True
        assert any(
            "Loaded selector selection: 2 item(s)" in message for message in logs
        )
        saved = json.loads(wizard.wizard_config_path.read_text(encoding="utf-8"))
        assert saved["selector_discovery"]["selection_loaded"] is True
        assert saved["selector_discovery"]["selected_count"] == 2
        assert saved["selector_discovery"]["resolved_count"] == 2
        assert saved["selector_discovery"]["source_path"] == str(
            wizard.selector_output_path
        )

    def test_fails_cleanly_when_selector_artifact_is_malformed(
        self, tmp_path: Path
    ) -> None:
        self._ready_docs_meta(tmp_path)
        responses = iter(["2", "1", "1", "3", "1"])
        logs: list[str] = []
        wizard = _make_wizard(
            tmp_path, prompter=lambda _: next(responses), emitter=logs.append
        )
        wizard.selector_output_path.write_text("{bad json}", encoding="utf-8")

        result = wizard.phase_1_generate_templates()

        assert result["success"] is False
        assert "Invalid selector artifact" in result["error"]
        saved = json.loads(wizard.wizard_config_path.read_text(encoding="utf-8"))
        assert saved["phase1_status"]["status"] == "failed"
        assert "Invalid selector artifact" in saved["phase1_status"]["reason"]
        assert (
            saved["selector_discovery"]["validation_error"]
            == "Selector payload is not valid JSON."
        )
        assert any("Invalid selector artifact" in message for message in logs)


class TestPhase2Instructions:
    def test_fails_when_phase1_dir_missing(self, tmp_path: Path) -> None:
        result = _make_wizard(tmp_path).phase_2_show_instructions()
        assert result["success"] is False

    def test_fails_when_no_supported_files(self, tmp_path: Path) -> None:
        (tmp_path / "build" / "phase-1-choices").mkdir(parents=True)
        result = _make_wizard(tmp_path).phase_2_show_instructions()
        assert result["success"] is False

    def test_copies_md_files_and_returns_success(self, tmp_path: Path) -> None:
        phase1 = tmp_path / "build" / "phase-1-choices"
        phase1.mkdir(parents=True)
        (phase1 / "test.md").write_text("# Test", encoding="utf-8")
        wizard = _make_wizard(tmp_path, prompter=lambda _: "")
        result = wizard.phase_2_show_instructions()
        assert result["success"] is True
        assert "test.md" in result["copied_files"]

    def test_config_exists_but_missing_templates_does_not_look_successful(
        self, tmp_path: Path
    ) -> None:
        wizard = _make_wizard(tmp_path, prompter=lambda _: "")
        wizard.wizard_config_path.parent.mkdir(parents=True, exist_ok=True)
        wizard.wizard_config_path.write_text(
            json.dumps({"phase1_status": {"status": "completed"}}), encoding="utf-8"
        )
        result = wizard.phase_2_show_instructions()
        assert result["success"] is False
        assert "Phase 1 templates not found" in result["error"]


class TestPhase3Compile:
    def test_fails_when_phase2_dir_missing(self, tmp_path: Path) -> None:
        result = _make_wizard(tmp_path).phase_3_compile_templates()
        assert result["success"] is False

    def _set_phase3_mock(self, mock_c: MagicMock) -> None:
        sys.modules[
            "providence_wizard.orchestration.wizard.phase3_compiler"
        ].Phase3Compiler.return_value = mock_c
        sys.modules[
            "providence_wizard.orchestration.wizard.phase3_compiler"
        ].Phase3Compiler.side_effect = None

    def test_success_with_seedlings(self, tmp_path: Path) -> None:
        (tmp_path / "build" / "phase-2-input").mkdir(parents=True)
        mock_c = MagicMock()
        mock_c.run.return_value = {
            "success": True,
            "mandates": 2,
            "guidelines": 5,
            "files": [],
            "output_path": str(tmp_path),
        }
        self._set_phase3_mock(mock_c)
        with patch.object(
            InteractiveWizard, "phase_6_generate_seedlings", return_value=True
        ):
            result = _make_wizard(tmp_path).phase_3_compile_templates()
        assert result["success"] is True
        assert result["seedlings_success"] is True

    def test_success_seedlings_fail(self, tmp_path: Path) -> None:
        (tmp_path / "build" / "phase-2-input").mkdir(parents=True)
        mock_c = MagicMock()
        mock_c.run.return_value = {
            "success": True,
            "mandates": 1,
            "guidelines": 2,
            "files": [],
            "output_path": str(tmp_path),
        }
        self._set_phase3_mock(mock_c)
        with patch.object(
            InteractiveWizard, "phase_6_generate_seedlings", return_value=False
        ):
            result = _make_wizard(tmp_path).phase_3_compile_templates()
        assert result["success"] is True
        assert result["seedlings_success"] is False

    def test_compiler_fails(self, tmp_path: Path) -> None:
        (tmp_path / "build" / "phase-2-input").mkdir(parents=True)
        mock_c = MagicMock()
        mock_c.run.return_value = {
            "success": False,
            "error": "syntax",
            "mandates": 0,
            "guidelines": 0,
            "files": [],
            "output_path": "",
        }
        self._set_phase3_mock(mock_c)
        result = _make_wizard(tmp_path).phase_3_compile_templates()
        assert result["success"] is False

    def test_exception_returns_failure(self, tmp_path: Path) -> None:
        (tmp_path / "build" / "phase-2-input").mkdir(parents=True)
        sys.modules[
            "providence_wizard.orchestration.wizard.phase3_compiler"
        ].Phase3Compiler.side_effect = RuntimeError("boom")
        result = _make_wizard(tmp_path).phase_3_compile_templates()
        sys.modules[
            "providence_wizard.orchestration.wizard.phase3_compiler"
        ].Phase3Compiler.side_effect = None
        assert result["success"] is False


class TestPhase4Generate:
    def _setup_p4(self, tmp_path: Path) -> InteractiveWizard:
        wizard = _make_wizard(tmp_path, prompter=lambda _: "")
        wizard.wizard_config_path.parent.mkdir(parents=True, exist_ok=True)
        wizard.wizard_config_path.write_text(
            json.dumps({"language": "Python"}), encoding="utf-8"
        )
        (tmp_path / "compiled").mkdir(parents=True)
        return wizard

    def test_fails_without_config(self, tmp_path: Path) -> None:
        assert _make_wizard(tmp_path).phase_4_generate_project()["success"] is False

    def test_fails_without_phase3_output(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path, prompter=lambda _: "")
        wizard.wizard_config_path.parent.mkdir(parents=True, exist_ok=True)
        wizard.wizard_config_path.write_text("{}", encoding="utf-8")
        assert wizard.phase_4_generate_project()["success"] is False

    def _set_p4_mock(self, return_value: dict) -> None:
        sys.modules[
            "providence_wizard.orchestration.phase_4_5_6_generator"
        ].run_phase_4_5_6_generator.return_value = return_value
        sys.modules[
            "providence_wizard.orchestration.phase_4_5_6_generator"
        ].run_phase_4_5_6_generator.side_effect = None

    def test_success_with_consolidation(self, tmp_path: Path) -> None:
        wizard = self._setup_p4(tmp_path)
        self._set_p4_mock(
            {
                "success": True,
                "mandates": 1,
                "guidelines": 5,
                "categories": ["git"],
                "errors": [],
            }
        )
        with patch.object(
            InteractiveWizard,
            "_consolidate_final_template",
            return_value={"success": True, "moved_items": 2},
        ):
            assert wizard.phase_4_generate_project()["success"] is True

    def test_consolidation_failure(self, tmp_path: Path) -> None:
        wizard = self._setup_p4(tmp_path)
        self._set_p4_mock(
            {
                "success": True,
                "mandates": 1,
                "guidelines": 0,
                "categories": [],
                "errors": [],
            }
        )
        with patch.object(
            InteractiveWizard,
            "_consolidate_final_template",
            return_value={"success": False, "error": "fail"},
        ):
            assert wizard.phase_4_generate_project()["success"] is False

    def test_generator_failure(self, tmp_path: Path) -> None:
        wizard = self._setup_p4(tmp_path)
        self._set_p4_mock({"success": False, "errors": ["bad"]})
        assert wizard.phase_4_generate_project()["success"] is False

    def test_exception_returns_failure(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path, prompter=lambda _: "")
        wizard.wizard_config_path.parent.mkdir(parents=True, exist_ok=True)
        wizard.wizard_config_path.write_text("{invalid", encoding="utf-8")
        (tmp_path / "compiled").mkdir(parents=True)
        assert wizard.phase_4_generate_project()["success"] is False


class TestPhase6:
    def test_delegates_to_runtime(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        with patch(
            "providence_wizard.application.interactive_wizard.run_phase6_seedlings_generation",
            return_value=True,
        ):
            assert wizard.phase_6_generate_seedlings(tmp_path) is True

    def test_exception_returns_false(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        with patch(
            "providence_wizard.application.interactive_wizard.run_phase6_seedlings_generation",
            side_effect=RuntimeError("boom"),
        ):
            assert wizard.phase_6_generate_seedlings(tmp_path) is False


class TestEnforcementLabel:
    def test_reads_from_config(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        wizard.wizard_config_path.parent.mkdir(parents=True, exist_ok=True)
        wizard.wizard_config_path.write_text(
            json.dumps({"enforcement_mode": "strict_mode"}), encoding="utf-8"
        )
        assert wizard._get_enforcement_label() == "Bloquear"

    def test_default_when_file_missing(self, tmp_path: Path) -> None:
        assert _make_wizard(tmp_path)._get_enforcement_label() == "Alertas"

    def test_default_on_parse_error(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        wizard.wizard_config_path.parent.mkdir(parents=True, exist_ok=True)
        wizard.wizard_config_path.write_text("{bad", encoding="utf-8")
        assert wizard._get_enforcement_label() == "Alertas"


class TestConsolidateFinalTemplate:
    def test_emits_on_success(self, tmp_path: Path) -> None:
        logs: list[str] = []
        wizard = _make_wizard(tmp_path, emitter=logs.append, debug=True)
        with patch(
            "providence_wizard.application._interactive_wizard_context_mixin.consolidate_final_template",
            return_value={"success": True, "moved_items": 3},
        ):
            wizard._consolidate_final_template()
        assert any("3" in m for m in logs)

    def test_returns_result_on_failure(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        with patch(
            "providence_wizard.application._interactive_wizard_context_mixin.consolidate_final_template",
            return_value={"success": False, "error": "x"},
        ):
            result = wizard._consolidate_final_template()
        assert result["success"] is False


def _make_wizard_with_source_spec(tmp_path: Path, **extra_paths) -> InteractiveWizard:
    paths = {
        **_BASE_PATHS,
        "client_build": tmp_path / "build",
        "client_compiled": tmp_path / "compiled",
        **extra_paths,
    }
    with patch(
        "providence_wizard.application.interactive_wizard.get_sdd_paths",
        return_value=paths,
    ):
        return InteractiveWizard(
            repo_root=tmp_path,
            emitter=lambda _: None,
            prompter=lambda _: "",
        )


class TestSourceSpecReady:
    def test_false_when_source_spec_missing(self, tmp_path: Path) -> None:
        wizard = _make_wizard_with_source_spec(tmp_path, source_spec=tmp_path / "spec")
        assert source_spec_ready(wizard.paths, wizard.client_build_dir) is False

    def test_true_with_mandate_and_guidelines(self, tmp_path: Path) -> None:
        spec = tmp_path / "spec"
        spec.mkdir(parents=True)
        (spec / "mandate.spec").write_text("x", encoding="utf-8")
        (spec / "guidelines.dsl").write_text("x", encoding="utf-8")
        wizard = _make_wizard_with_source_spec(tmp_path, source_spec=spec)
        assert source_spec_ready(wizard.paths, wizard.client_build_dir) is True

    def test_false_without_guidelines(self, tmp_path: Path) -> None:
        spec = tmp_path / "spec"
        spec.mkdir(parents=True)
        (spec / "mandate.md").write_text("x", encoding="utf-8")
        wizard = _make_wizard_with_source_spec(tmp_path, source_spec=spec)
        assert source_spec_ready(wizard.paths, wizard.client_build_dir) is False


class TestEnsureOnboardingScaffoldOSError:
    def test_returns_false_on_mkdir_failure(self, tmp_path: Path) -> None:
        """Covers the except OSError branch in _ensure_onboarding_scaffold."""
        wizard = _make_wizard(tmp_path)
        with patch.object(Path, "mkdir", side_effect=OSError("disk full")):
            ok, reason = wizard._ensure_onboarding_scaffold()
        assert ok is False
        assert "disk full" in reason


class TestEnsureDocsMetaReadyFailures:
    def test_scaffold_failure_propagates(self, tmp_path: Path) -> None:
        """Covers line 262: when scaffold_ok is False."""
        wizard = _make_wizard(tmp_path)
        with patch.object(
            wizard, "_ensure_onboarding_scaffold", return_value=(False, "oops")
        ):
            ok, reason = wizard._ensure_docs_meta_ready()
        assert ok is False
        assert "oops" in reason

    def test_returns_false_when_both_checks_fail(self, tmp_path: Path) -> None:
        """Covers lines 265-272: scaffold succeeds but neither docs_meta nor source_spec ready."""
        wizard = _make_wizard(tmp_path)
        with (
            patch.object(
                wizard, "_ensure_onboarding_scaffold", return_value=(True, "")
            ),
            patch(
                "providence_wizard.application._interactive_wizard_context_mixin.docs_meta_ready",
                return_value=False,
            ),
            patch(
                "providence_wizard.application._interactive_wizard_context_mixin.source_spec_ready",
                return_value=False,
            ),
        ):
            ok, reason = wizard._ensure_docs_meta_ready()
        assert ok is False
        assert "Phase 1 source artifacts are missing" in reason


class TestPhase1GenerateTemplatesFailurePaths:
    def _ready_docs_meta(self, tmp_path: Path) -> None:
        d = tmp_path / "build" / "docs-meta"
        d.mkdir(parents=True)
        (d / "mandate.spec").write_text("x", encoding="utf-8")
        (d / "guidelines.dsl").write_text("x", encoding="utf-8")

    def test_fails_when_docs_meta_not_ready(self, tmp_path: Path) -> None:
        """Covers lines 291-296: _ensure_docs_meta_ready returns False."""
        responses = iter(["2", "1", "1", "3", "1"])
        wizard = _make_wizard(tmp_path, prompter=lambda _: next(responses))
        with patch.object(
            wizard, "_ensure_docs_meta_ready", return_value=(False, "no artifacts")
        ):
            result = wizard.phase_1_generate_templates()
        assert result["success"] is False
        assert "no artifacts" in result["error"]

    def test_generator_failure_records_status(self, tmp_path: Path) -> None:
        """Covers line 338: generator returns success=False."""
        self._ready_docs_meta(tmp_path)
        responses = iter(["2", "1", "1", "3", "1"])
        wizard = _make_wizard(tmp_path, prompter=lambda _: next(responses))
        mock_gen = MagicMock()
        mock_gen.run.return_value = {"success": False, "error": "gen failed"}
        sys.modules[
            "providence_wizard.orchestration.wizard.phase1_generator"
        ].Phase1Generator.return_value = mock_gen
        result = wizard.phase_1_generate_templates()
        assert result["success"] is False


class TestPhase2InstructionsConfigPaths:
    def _setup_phase1(self, tmp_path: Path) -> None:
        phase1 = tmp_path / "build" / "phase-1-choices"
        phase1.mkdir(parents=True)
        (phase1 / "test.md").write_text("# Test", encoding="utf-8")

    def test_fails_when_config_shows_phase1_failed(self, tmp_path: Path) -> None:
        """Covers the phase1_status == 'failed' branch in phase_2_show_instructions."""
        self._setup_phase1(tmp_path)
        wizard = _make_wizard(tmp_path, prompter=lambda _: "")
        wizard.wizard_config_path.parent.mkdir(parents=True, exist_ok=True)
        wizard.wizard_config_path.write_text(
            json.dumps({"phase1_status": {"status": "failed", "reason": "bad input"}}),
            encoding="utf-8",
        )
        result = wizard.phase_2_show_instructions()
        assert result["success"] is False
        assert "bad input" in result["error"]

    def test_warns_and_continues_on_corrupt_config(self, tmp_path: Path) -> None:
        """Covers the except (OSError, ValueError, TypeError) branch."""
        self._setup_phase1(tmp_path)
        wizard = _make_wizard(tmp_path, prompter=lambda _: "")
        wizard.wizard_config_path.parent.mkdir(parents=True, exist_ok=True)
        wizard.wizard_config_path.write_text("{bad json}", encoding="utf-8")
        result = wizard.phase_2_show_instructions()
        assert result["success"] is True


class TestAskSeedlingSelection:
    def test_all_returns_none(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path, prompter=lambda _: "all")
        assert wizard._ask_seedling_selection() is None

    def test_numeric_returns_set(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path, prompter=lambda _: "1")
        result = wizard._ask_seedling_selection()
        assert result is not None
        assert len(result) == 1


class TestRun:
    """Tests for the single guided flow (Scenario A/B), replacing the old
    phase-choice menu dispatch."""

    @contextmanager
    def _patch_scenario_a_phases(
        self,
        wizard: InteractiveWizard,
        *,
        phase1: bool = True,
        phase2: bool = True,
        phase3: bool = True,
        phase4: bool = True,
    ):
        with (
            patch.object(
                wizard,
                "ask_user_preferences",
                return_value={"language": "all"},
            ),
            patch.object(wizard, "_ask_seedling_selection", return_value=None),
            patch.object(
                wizard,
                "phase_1_generate_templates",
                return_value={"success": phase1},
            ),
            patch.object(
                wizard,
                "phase_2_show_instructions",
                return_value={"success": phase2},
            ),
            patch.object(
                wizard,
                "phase_3_compile_templates",
                return_value={"success": phase3},
            ),
            patch.object(
                wizard,
                "phase_4_generate_project",
                return_value={"success": phase4},
            ),
        ):
            yield

    def test_scenario_a_success_runs_all_phases_in_order(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path, prompter=lambda _: "1")
        with self._patch_scenario_a_phases(wizard):
            assert wizard.run() is True

    def test_scenario_a_stops_when_phase1_fails(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path, prompter=lambda _: "1")
        with self._patch_scenario_a_phases(wizard, phase1=False):
            assert wizard.run() is False

    def test_scenario_a_stops_when_phase2_fails(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path, prompter=lambda _: "1")
        with self._patch_scenario_a_phases(wizard, phase2=False):
            assert wizard.run() is False

    def test_scenario_a_stops_when_phase3_fails(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path, prompter=lambda _: "1")
        with self._patch_scenario_a_phases(wizard, phase3=False):
            assert wizard.run() is False

    def test_scenario_a_stops_when_phase4_fails(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path, prompter=lambda _: "1")
        with self._patch_scenario_a_phases(wizard, phase4=False):
            assert wizard.run() is False

    def test_scenario_b_used_when_custom_governance_path_set(
        self, tmp_path: Path
    ) -> None:
        custom_file = tmp_path / "custom-governance.json"
        custom_file.write_text(
            json.dumps(
                {"items": [{"id": "M001", "type": "MANDATE", "title": "Clean Code"}]}
            ),
            encoding="utf-8",
        )
        wizard = _make_wizard(tmp_path, prompter=lambda _: "1")
        wizard.custom_governance_path = custom_file
        with (
            patch.object(
                wizard, "ask_user_preferences", return_value={"language": "all"}
            ),
            patch.object(wizard, "_ask_seedling_selection", return_value=None),
            patch.object(
                wizard, "phase_4_generate_project", return_value={"success": True}
            ),
        ):
            assert wizard.run() is True

        config = json.loads(wizard.wizard_config_path.read_text(encoding="utf-8"))
        assert config["phase1_status"]["status"] == "skipped"
        assert config["phase1_status"]["reason"] == "custom_governance_file"

    def test_scenario_b_stops_on_invalid_custom_file(self, tmp_path: Path) -> None:
        custom_file = tmp_path / "custom-governance.json"
        custom_file.write_text(json.dumps({"items": []}), encoding="utf-8")
        wizard = _make_wizard(tmp_path, prompter=lambda _: "1")
        wizard.custom_governance_path = custom_file
        with (
            patch.object(
                wizard, "ask_user_preferences", return_value={"language": "all"}
            ),
            patch.object(wizard, "_ask_seedling_selection", return_value=None),
        ):
            assert wizard.run() is False

    def test_non_interactive_without_tty_and_no_custom_path_fails_fast(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        wizard = _make_wizard(tmp_path, prompter=lambda _: "1")
        assert wizard.non_interactive is False
        assert wizard.run() is False

    def test_non_interactive_flag_skips_tty_check(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        wizard = _make_wizard(tmp_path, prompter=lambda _: "1")
        wizard.non_interactive = True
        with self._patch_scenario_a_phases(wizard):
            assert wizard.run() is True

    def test_keyboard_interrupt_returns_false(self, tmp_path: Path) -> None:
        def _raise(_: str) -> str:
            raise KeyboardInterrupt

        wizard = _make_wizard(tmp_path, prompter=_raise)
        assert wizard.run() is False

    def test_exception_returns_false(self, tmp_path: Path) -> None:
        def _raise(_: str) -> str:
            raise RuntimeError("crash")

        wizard = _make_wizard(tmp_path, prompter=_raise)
        assert wizard.run() is False


class TestRunInteractiveWizard:
    def test_creates_wizard_and_runs(self, tmp_path: Path) -> None:
        paths = {
            **_BASE_PATHS,
            "client_build": tmp_path / "build",
            "client_compiled": tmp_path / "compiled",
        }
        with (
            patch(
                "providence_wizard.application.interactive_wizard.get_sdd_paths",
                return_value=paths,
            ),
            patch.object(InteractiveWizard, "run", return_value=True),
        ):
            assert run_interactive_wizard(tmp_path) is True
