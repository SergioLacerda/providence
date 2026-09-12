"""Application boundary for the Phase 3 staged-template compilation flow."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from providence_wizard.orchestration.wizard.messages import phase3_completed_message
from providence_wizard.orchestration.wizard.models import (
    InteractivePhase3CompileResult as Phase3CompileResult,
)
from providence_wizard.orchestration.wizard.models import (
    build_interactive_phase3_result,
)


class PhaseThreeContext(Protocol):
    """Narrow contract for Phase 3 compilation."""

    phase2_input_dir: Path
    client_compiled_dir: Path
    paths: dict[str, Any]
    debug: bool

    def _emit(self, message: str) -> None:
        """Send an operator-facing message."""

    def print_header(self, title: str, icon: str = "") -> None:
        """Print a formatted wizard header."""

    def phase_6_generate_seedlings(self, output_base: Path) -> bool:
        """Run Phase 6 seedling generation."""

    def _get_enforcement_label(self) -> str:
        """Return the enforcement label for operator messages."""


class PhaseThreeRuntime:
    """Boundary for staged template compilation and seedling follow-up."""

    def __init__(self, context: PhaseThreeContext) -> None:
        self._context = context

    def execute(self) -> Phase3CompileResult:
        """Compile staged templates and trigger seedling generation."""
        markdown_path = self._context.phase2_input_dir
        output_path = self._context.client_compiled_dir
        self._emit_paths(markdown_path, output_path)
        if not markdown_path.exists():
            return self._build_missing_templates(markdown_path, output_path)
        try:
            compiler = self._build_compiler(markdown_path, output_path)
            result = compiler.run()
            return self._handle_compiler_result(result, output_path)
        except Exception as exc:
            self._context._emit(f"\n Error: {exc}")
            import traceback

            traceback.print_exc()
            return build_interactive_phase3_result(
                success=False,
                output_path=output_path,
                error=str(exc),
            )

    def _emit_paths(self, markdown_path: Path, output_path: Path) -> None:
        if not self._context.debug:
            return
        self._context._emit(f"   Input (phase-2-input): {markdown_path}")
        self._context._emit(f"   Output (client-compiled): {output_path}")

    def _build_missing_templates(
        self, markdown_path: Path, output_path: Path
    ) -> Phase3CompileResult:
        self._context._emit(f"\n Templates not found: {markdown_path}")
        self._context._emit("\nYou need to:")
        self._context._emit("1. Run Phase 1 to generate templates")
        self._context._emit("2. Run Phase 2 to stage edited files into phase-2-input")
        self._context._emit("3. Run Phase 3 to compile")
        return build_interactive_phase3_result(
            success=False,
            output_path=output_path,
            error=f"Templates not found: {markdown_path}",
        )

    def _build_compiler(self, markdown_path: Path, output_path: Path) -> Any:
        from providence_wizard.orchestration.wizard.phase3_compiler import (
            Phase3Compiler,
        )

        return Phase3Compiler(
            markdown_path,
            output_path,
            self._context.paths["root"],
            verbose=self._context.debug,
        )

    def _handle_compiler_result(
        self, result: dict[str, Any], output_path: Path
    ) -> Phase3CompileResult:
        if not result["success"]:
            self._context._emit(f"\n Failed: {result.get('error', 'Unknown error')}")
            return build_interactive_phase3_result(
                success=False,
                output_path=Path(str(result.get("output_path", str(output_path)))),
                mandates=int(result.get("mandates", 0)),
                guidelines=int(result.get("guidelines", 0)),
                files=list(result.get("files", [])),
                seedlings_success=False,
                error=str(result.get("error", "Unknown error")),
            )
        self._emit_compile_success(result)
        self._emit_seedling_header()
        seedlings_success = self._context.phase_6_generate_seedlings(output_path)
        if seedlings_success:
            self._emit_seedling_success()
        else:
            self._emit_seedling_warning(output_path)
        return build_interactive_phase3_result(
            success=True,
            output_path=Path(str(result.get("output_path", str(output_path)))),
            mandates=int(result.get("mandates", 0)),
            guidelines=int(result.get("guidelines", 0)),
            files=list(result.get("files", [])),
            seedlings_success=seedlings_success,
        )

    def _emit_compile_success(self, result: dict[str, Any]) -> None:
        if not self._context.debug:
            return
        self._context._emit(
            f"""
 PHASE 3 COMPLETE!

 COMPILATION RESULTS:
    Mandates: {result.get("mandates", 0)}
    Guidelines: {result.get("guidelines", 0)}
    Output Files: {", ".join(result.get("files", []))}
    Location: {result.get("output_path")}

"""
        )

    def _emit_seedling_header(self) -> None:
        if not self._context.debug:
            return
        self._context._emit("\n" + "=" * 70)
        self._context.print_header("PHASE 6: Generate Intelligent Seedlings", "")
        self._context._emit("=" * 70)

    def _emit_seedling_success(self) -> None:
        if not self._context.debug:
            return
        self._context._emit(phase3_completed_message())
        self._context._emit(
            f"""
 Governance mandates are ready for agents
 Enforcement mode: {self._context._get_enforcement_label()}
 IDE integration configured
 CI/CD compliance hooks ready

  For more details, see README.md in your project root.
"""
        )

    def _emit_seedling_warning(self, output_path: Path) -> None:
        self._context._emit("\n  Phase 6 (Seedlings) had issues, but Phase 3 succeeded")
        self._context._emit(
            f"   You can manually run Phase 6 or copy files from {output_path}"
        )
