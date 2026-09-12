"""Tests for the new application boundary modules."""

from __future__ import annotations

import logging
from pathlib import Path

from providence_wizard.application.finalization import build_wizard_result
from providence_wizard.application.phase_runtime import (
    InteractiveFlowRuntime,
    PhaseOneRuntime,
    PhaseRuntime,
    PhaseTwoRuntime,
)
from providence_wizard.application.session_bootstrap import SessionBootstrap
from providence_wizard.contracts import WizardInvocation


def test_phase_runtime_executes_runner_with_invocation(tmp_path: Path) -> None:
    recorded: list[tuple[Path, Path | None, bool, Path | None]] = []

    def _runner(
        project_root: Path,
        output_dir: Path | None = None,
        non_interactive: bool = False,
        custom_governance_path: Path | None = None,
        debug: bool = False,
    ) -> bool:
        recorded.append(
            (project_root, output_dir, non_interactive, custom_governance_path)
        )
        return True

    runtime = PhaseRuntime(
        WizardInvocation(project_root=tmp_path, output_path=tmp_path / "out"),
        runner=_runner,
    )

    assert runtime.execute() is True
    assert recorded == [(tmp_path, tmp_path / "out", False, None)]


def test_phase_runtime_forwards_custom_governance_path(tmp_path: Path) -> None:
    """Regression: custom_governance_path must survive PhaseRuntime.execute()."""
    recorded: dict[str, object] = {}

    def _runner(
        project_root: Path,
        output_dir: Path | None = None,
        non_interactive: bool = False,
        custom_governance_path: Path | None = None,
        debug: bool = False,
    ) -> bool:
        recorded["custom_governance_path"] = custom_governance_path
        recorded["non_interactive"] = non_interactive
        return True

    custom_path = tmp_path / "custom-governance.json"
    runtime = PhaseRuntime(
        WizardInvocation(
            project_root=tmp_path,
            non_interactive=True,
            custom_governance_path=custom_path,
        ),
        runner=_runner,
    )

    assert runtime.execute() is True
    assert recorded["custom_governance_path"] == custom_path
    assert recorded["non_interactive"] is True


def test_session_bootstrap_preserves_custom_governance_path(tmp_path: Path) -> None:
    """Regression: custom_governance_path was previously dropped in __init__."""
    custom_path = tmp_path / "custom-governance.json"
    bootstrap = SessionBootstrap(
        WizardInvocation(project_root=tmp_path, custom_governance_path=custom_path)
    )

    assert bootstrap._invocation.custom_governance_path == custom_path


def test_session_bootstrap_returns_failure_result(tmp_path: Path) -> None:
    class _FalseRuntime:
        def __init__(self, _invocation) -> None:
            pass

        def execute(self) -> bool:
            return False

    from providence_wizard.application import session_bootstrap

    original = session_bootstrap.PhaseRuntime
    session_bootstrap.PhaseRuntime = _FalseRuntime
    try:
        result = SessionBootstrap(WizardInvocation(project_root=tmp_path)).run()
    finally:
        session_bootstrap.PhaseRuntime = original

    assert result.success is False
    assert result.errors


def test_session_bootstrap_elevates_logger_when_debug(tmp_path: Path) -> None:
    class _FalseRuntime:
        def __init__(self, _invocation) -> None:
            pass

        def execute(self) -> bool:
            return True

    from providence_wizard.application import session_bootstrap

    logger = logging.getLogger("providence_wizard")
    original_level = logger.level
    original_runtime = session_bootstrap.PhaseRuntime
    session_bootstrap.PhaseRuntime = _FalseRuntime
    try:
        SessionBootstrap(WizardInvocation(project_root=tmp_path, debug=True)).run()
        assert logger.level == logging.DEBUG
    finally:
        session_bootstrap.PhaseRuntime = original_runtime
        logger.setLevel(original_level)


def test_session_bootstrap_leaves_logger_level_when_not_debug(tmp_path: Path) -> None:
    class _FalseRuntime:
        def __init__(self, _invocation) -> None:
            pass

        def execute(self) -> bool:
            return True

    from providence_wizard.application import session_bootstrap

    logger = logging.getLogger("providence_wizard")
    logger.setLevel(logging.WARNING)
    original_runtime = session_bootstrap.PhaseRuntime
    session_bootstrap.PhaseRuntime = _FalseRuntime
    try:
        SessionBootstrap(WizardInvocation(project_root=tmp_path, debug=False)).run()
        assert logger.level == logging.WARNING
    finally:
        session_bootstrap.PhaseRuntime = original_runtime
        logger.setLevel(logging.NOTSET)


def test_build_wizard_result_success() -> None:
    result = build_wizard_result(True)
    assert result.success is True
    assert result.errors == []


def test_phase_one_runtime_persists_failure_when_docs_missing(tmp_path: Path) -> None:
    context = _make_phase_one_context(
        tmp_path, ready=False, reason="missing docs-meta", selector_selection={}
    )
    result = PhaseOneRuntime(context).execute()

    assert result["success"] is False
    assert result["error"] == "missing docs-meta"
    assert context.saved is not None
    assert context.saved["phase1_status"]["status"] == "failed"


def test_phase_one_runtime_loads_selector_discovery_on_success(tmp_path: Path) -> None:
    class _Generator:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def run(self) -> dict:
            return {"success": True}

    context = _make_phase_one_context(
        tmp_path,
        ready=True,
        reason="",
        selector_selection={"selected_ids": ["M001"], "resolved_ids": ["M001", "M002"]},
        config={"language": "Go", "enforcement_mode": "strict_mode"},
    )
    (context.phase1_choices_dir / "mandate.md").write_text("# ok", encoding="utf-8")
    runtime = PhaseOneRuntime(context)
    runtime._load_generator = lambda: _Generator  # type: ignore[method-assign]

    result = runtime.execute()

    assert result["success"] is True
    assert context.saved is not None
    assert context.saved["selector_selection"]["resolved_ids"] == [
        "M001",
        "M002",
    ]
    assert context.saved["phase1_status"]["artifacts"] == ["mandate.md"]


def test_phase_two_runtime_stages_supported_files(tmp_path: Path) -> None:
    context = _PhaseTwoContext(tmp_path)
    result = PhaseTwoRuntime(context).execute()
    assert result["success"] is True
    assert result["copied_files"] == ["test.md"]
    assert (context.phase2_input_dir / "test.md").exists()


def test_interactive_flow_runtime_scenario_a_success(
    monkeypatch, tmp_path: Path
) -> None:
    """Single guided flow: Scenario A (no custom_governance_path) runs
    Phase 1-3 then Phase 4, with no phase-choice menu."""
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)

    class _Context:
        non_interactive = False
        custom_governance_path = None

        def ask_user_preferences(self) -> dict:
            return {"language": "all"}

        def _ask_seedling_selection(self):
            return None

        def phase_1_generate_templates(self) -> dict:
            return {"success": True}

        def phase_2_show_instructions(self) -> dict:
            return {"success": True}

        def phase_3_compile_templates(self) -> dict:
            return {"success": True}

        def phase_4_generate_project(self) -> dict:
            return {"success": True}

        def _emit(self, _message: str) -> None:
            pass

    assert InteractiveFlowRuntime(_Context()).execute() is True


def test_interactive_flow_runtime_scenario_a_stops_on_phase2_failure(
    monkeypatch,
) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)

    class _Context:
        non_interactive = False
        custom_governance_path = None

        def ask_user_preferences(self) -> dict:
            return {"language": "all"}

        def _ask_seedling_selection(self):
            return None

        def phase_1_generate_templates(self) -> dict:
            return {"success": True}

        def phase_2_show_instructions(self) -> dict:
            return {"success": False}

        def phase_3_compile_templates(self) -> dict:
            return {"success": False}

        def phase_4_generate_project(self) -> dict:
            return {"success": False}

        def _emit(self, _message: str) -> None:
            pass

    assert InteractiveFlowRuntime(_Context()).execute() is False


class _PhaseOneContext:
    SUPPORTED_PHASE2_PATTERNS = ("*.md",)

    def __init__(
        self,
        tmp_path: Path,
        *,
        ready: bool,
        reason: str,
        selector_selection: dict,
        config: dict | None = None,
    ) -> None:
        self.repo_root = tmp_path
        self.phase1_choices_dir = tmp_path / "phase-1"
        self.wizard_config_path = tmp_path / "wizard-config.json"
        self.debug = False
        self.saved: dict | None = None
        self.messages: list[str] = []
        self.ready = ready
        self.reason = reason
        self.selector_selection = selector_selection
        self.config = config or {"language": "Python", "enforcement_mode": "warn_mode"}
        self.phase1_choices_dir.mkdir(parents=True, exist_ok=True)

    def ask_user_preferences(self) -> dict:
        return dict(self.config)

    def _load_selector_selection_config(self) -> dict:
        return dict(self.selector_selection)

    def _build_selector_discovery_config(self, selector_selection: dict) -> dict:
        return {"selection_loaded": bool(selector_selection)}

    def _emit_selector_phase1_hint(self, selector_selection: dict) -> None:
        self.messages.append(str(selector_selection))

    def _ensure_docs_meta_ready(self) -> tuple[bool, str]:
        return self.ready, self.reason

    def save_config(self, config: dict) -> Path:
        self.saved = config
        self.wizard_config_path.write_text("{}", encoding="utf-8")
        return self.wizard_config_path

    def _build_phase1_status(
        self, status: str, reason: str = "", artifacts: list[str] | None = None
    ) -> dict:
        return {"status": status, "reason": reason, "artifacts": artifacts or []}

    def _emit(self, message: str) -> None:
        self.messages.append(message)


def _make_phase_one_context(
    tmp_path: Path,
    *,
    ready: bool,
    reason: str,
    selector_selection: dict,
    config: dict | None = None,
) -> _PhaseOneContext:
    return _PhaseOneContext(
        tmp_path,
        ready=ready,
        reason=reason,
        selector_selection=selector_selection,
        config=config,
    )


class _Prompter:
    def confirm(self, _question: str, default: bool = True) -> bool:
        return default


class _PhaseTwoContext:
    SUPPORTED_PHASE2_PATTERNS = ("*.md",)

    def __init__(self, tmp_path: Path) -> None:
        self.phase1_choices_dir = tmp_path / "phase-1-choices"
        self.phase2_input_dir = tmp_path / "phase-2-input"
        self.wizard_config_path = tmp_path / "wizard-config.json"
        self._prompter = _Prompter()
        self.messages: list[str] = []
        self.phase1_choices_dir.mkdir(parents=True, exist_ok=True)
        (self.phase1_choices_dir / "test.md").write_text("# Test", encoding="utf-8")

    def _emit(self, message: str) -> None:
        self.messages.append(message)
