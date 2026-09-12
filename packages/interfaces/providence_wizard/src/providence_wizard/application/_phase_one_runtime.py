"""Application boundary for the Phase 1 template-generation flow."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from providence_wizard.orchestration.wizard.models import Phase1GenerateResult

from ._phase_one_results import build_phase1_failure, build_phase1_result


class PhaseOneContext(Protocol):
    """Narrow contract for delegating Phase 1 orchestration."""

    repo_root: Path
    phase1_choices_dir: Path
    wizard_config_path: Path
    SUPPORTED_PHASE2_PATTERNS: tuple[str, ...]
    debug: bool

    def ask_user_preferences(self) -> dict[str, Any]:
        """Return the Phase 1 preference payload."""

    def _load_selector_selection_config(self) -> dict[str, Any]:
        """Load selector selection metadata when present."""

    def _build_selector_discovery_config(
        self, selector_selection: dict[str, Any]
    ) -> dict[str, Any]:
        """Build audit metadata for selector discovery."""

    def _emit_selector_phase1_hint(self, selector_selection: dict[str, Any]) -> None:
        """Emit the optional selector hint to the operator."""

    def _ensure_docs_meta_ready(self) -> tuple[bool, str]:
        """Validate that Phase 1 source inputs are ready."""

    def save_config(self, config: dict[str, Any]) -> Path:
        """Persist wizard config and return its path."""

    def _build_phase1_status(
        self,
        status: str,
        reason: str = "",
        artifacts: list[str] | None = None,
    ) -> dict[str, Any]:
        """Build the persisted Phase 1 status block."""

    def _emit(self, message: str) -> None:
        """Send an operator-facing message."""


class PhaseOneRuntime:
    """Application boundary for the Phase 1 template-generation flow."""

    def __init__(self, context: PhaseOneContext) -> None:
        self._context = context

    def execute(self) -> Phase1GenerateResult:
        """Run the Phase 1 flow and return the legacy result payload."""
        try:
            generator_type = self._load_generator()
            config = self._context.ask_user_preferences()
            selector_result = self._load_selector_config(config)
            if selector_result is not None:
                return selector_result
            readiness_result = self._ensure_docs_ready(config)
            if readiness_result is not None:
                return readiness_result
            return self._run_generator(generator_type, config)
        except Exception as exc:
            self._context._emit(f"\n Error: {exc}")
            import traceback

            traceback.print_exc()
            return self._build_failure(
                error=str(exc),
                config_path=str(self._context.wizard_config_path),
            )

    def _load_generator(self) -> type[Any]:
        from providence_wizard.orchestration.wizard.phase1_generator import (
            Phase1Generator,
        )

        return Phase1Generator

    def _load_selector_config(
        self, config: dict[str, Any]
    ) -> Phase1GenerateResult | None:
        from providence_wizard.orchestration.wizard.selector_bridge import (
            SelectorBridgeError,
        )

        try:
            selector_selection = self._context._load_selector_selection_config()
        except SelectorBridgeError as exc:
            config["selector_discovery"] = (
                self._context._build_selector_discovery_config({})
            )
            config["selector_discovery"]["validation_error"] = str(exc)
            reason = f"Invalid selector artifact: {exc}"
            self._context._emit(f"\n {reason}")
            return self._persist_failure(config, reason)
        if selector_selection:
            config["selector_selection"] = selector_selection
        config["selector_discovery"] = self._context._build_selector_discovery_config(
            selector_selection
        )
        self._context._emit_selector_phase1_hint(selector_selection)
        return None

    def _ensure_docs_ready(self, config: dict[str, Any]) -> Phase1GenerateResult | None:
        ready, reason = self._context._ensure_docs_meta_ready()
        if ready:
            return None
        return self._persist_failure(config, reason)

    def _persist_failure(
        self, config: dict[str, Any], reason: str
    ) -> Phase1GenerateResult:
        config["phase1_status"] = self._context._build_phase1_status(
            status="failed", reason=reason
        )
        config_path = self._context.save_config(config)
        self._context._emit(f"\n Configuration saved to: {config_path}")
        return self._build_failure(
            error=reason, config_path=str(config_path), config=config
        )

    def _run_generator(
        self, generator_type: type[Any], config: dict[str, Any]
    ) -> Phase1GenerateResult:
        output_path = self._context.phase1_choices_dir
        generator = generator_type(
            self._context.repo_root / "packages",
            output_path,
            verbose=self._context.debug,
            config=config,
        )
        result = generator.run()
        if result["success"]:
            generated_files = self._collect_generated_files(output_path)
            config["phase1_status"] = self._context._build_phase1_status(
                status="completed", artifacts=generated_files
            )
            self._context._emit(f"templates...OK {output_path}")
        else:
            config["phase1_status"] = self._context._build_phase1_status(
                status="failed",
                reason=str(result.get("error") or "phase1_generation_failed"),
            )
        config_path = self._context.save_config(config)
        self._context._emit(f"config...OK {config_path}")
        return self._build_result(
            success=bool(result["success"]),
            config_path=str(config_path),
            output_path=str(output_path),
            config=config,
        )

    def _collect_generated_files(self, output_path: Path) -> list[str]:
        return sorted(
            path.name
            for pattern in self._context.SUPPORTED_PHASE2_PATTERNS
            for path in output_path.glob(pattern)
        )

    def _build_failure(
        self,
        *,
        error: str,
        config_path: str,
        config: dict[str, Any] | None = None,
    ) -> Phase1GenerateResult:
        return build_phase1_failure(
            phase1_choices_dir=str(self._context.phase1_choices_dir),
            error=error,
            config_path=config_path,
            config=config,
        )

    def _build_result(
        self,
        *,
        success: bool,
        config_path: str,
        output_path: str,
        config: dict[str, Any],
    ) -> Phase1GenerateResult:
        return build_phase1_result(
            success=success,
            config_path=config_path,
            output_path=output_path,
            config=config,
        )
