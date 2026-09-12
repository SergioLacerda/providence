"""Governance compilation orchestrator."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from providence_core._governance_orchestrator_support import (
    copy_build_artifacts,
    deployment_summary,
    ensure_spec_mandates,
    phase2_result_from_compile,
    pipeline_checks,
    publish_canonical_artifacts,
)
from providence_core._governance_orchestrator_types import (
    Phase1Result,
    Phase2Result,
    PipelineResult,
)
from providence_core.governance.spec_bootstrapper import SourceSpecBootstrapper
from providence_core.utils.compiler_runner import CompilerRunner
from providence_core.utils.environment import get_sdd_paths, resolve_profile
from providence_integration.builders.governance.pipeline_builder import PipelineBuilder

__all__ = ["GovernanceOrchestrator", "PipelineResult"]
logger = logging.getLogger(__name__)


class GovernanceOrchestrator:
    """Run the governed compilation pipeline end to end."""

    def __init__(
        self,
        repo_root: str | None = None,
        workspace_root: str | None = None,
        spec_path: str | None = None,
        compiled_dir: str | None = None,
        emit: Callable[[str], None] | None = None,
        profile: str | None = None,
    ):
        root_path = Path(repo_root).resolve() if repo_root is not None else None
        workspace_path = (
            Path(workspace_root).resolve() if workspace_root is not None else None
        )
        paths = get_sdd_paths(repo_root=root_path, workspace_root=workspace_path)
        self.repo_root = root_path or paths.get("repo_root", paths["root"])
        self.workspace_root = workspace_path or paths.get(
            "workspace_root", paths["root"]
        )
        self.spec = Path(spec_path) if spec_path else paths["source_spec"]
        if compiled_dir:
            self.compiled_dir, self.build_dir = (
                Path(compiled_dir),
                paths["master_build"],
            )
        else:
            active_profile = profile or self._resolve_active_profile(
                self.workspace_root
            )
            self.compiled_dir = (
                paths["master_compiled"]
                if active_profile == "master"
                else paths["client_compiled"]
            )
            self.build_dir = (
                paths["master_build"]
                if active_profile == "master"
                else paths["client_build"]
            )
        self.compiled_dir.mkdir(parents=True, exist_ok=True)
        self.build_dir.mkdir(parents=True, exist_ok=True)
        self._emit = emit
        self._spec_bootstrapper = SourceSpecBootstrapper(
            self.spec, self.repo_root, emit
        )

    @staticmethod
    def _resolve_active_profile(root: Path) -> str:
        try:
            return resolve_profile(root=root).type
        except Exception:
            return "master"

    def _out(self, message: str, *, level: int = logging.INFO) -> None:
        logger.log(level, message)
        if self._emit is not None:
            self._emit(message)

    def run_full_pipeline(self) -> PipelineResult:
        """Execute the build, compile, and validation pipeline."""
        self._out("🚀 Starting governance compilation pipeline...")
        self._out("📝 PHASE 1: Building governance pipeline...")
        phase1_result = self._run_phase_1()
        if not phase1_result.get("success", False):
            self._out("❌ PHASE 1 failed", level=logging.ERROR)
            return {
                "full_pipeline_success": False,
                "phase_1": phase1_result,
                "phase_2": {},
                "validated": False,
            }
        self._out("✅ PHASE 1 complete:")
        self._out(f"   - Core items: {phase1_result['core_item_count']}")
        self._out(f"   - Client items: {phase1_result['client_item_count']}")
        self._out(f"   - Core fingerprint: {phase1_result['core_fingerprint'][:16]}...")
        self._out("🔨 PHASE 2: Compiling to msgpack...")
        phase2_result = self._run_phase_2()
        if not phase2_result.get("success", False):
            self._out("❌ PHASE 2 failed", level=logging.ERROR)
            return {
                "full_pipeline_success": False,
                "phase_1": phase1_result,
                "phase_2": phase2_result,
                "validated": False,
            }
        self._out("✅ PHASE 2 complete:")
        self._out(f"   - Core msgpack: {Path(phase2_result['core_msgpack_file']).name}")
        self._out(
            f"   - Client msgpack: {Path(phase2_result['client_msgpack_file']).name}"
        )
        combined: PipelineResult = {
            "phase_1": phase1_result,
            "phase_2": phase2_result,
            "full_pipeline_success": False,
            "validated": False,
        }
        self._out("✔️ Validating complete pipeline...")
        combined["validated"] = self._validate_full_pipeline(combined)
        combined["full_pipeline_success"] = combined["validated"]
        self._out(
            "✅ All validations passed"
            if combined["validated"]
            else "❌ Validation failed",
            level=logging.INFO if combined["validated"] else logging.ERROR,
        )
        return combined

    def _run_phase_1(self) -> Phase1Result:
        try:
            self._spec_bootstrapper.bootstrap()
            spec_mandates_path = ensure_spec_mandates(
                self.repo_root, self.workspace_root
            )
            builder = PipelineBuilder(
                str(self.spec),
                spec_mandates_path=spec_mandates_path
                if spec_mandates_path.exists()
                else None,
            )
            result = builder.build()
            builder.save_outputs(str(self.build_dir))
            return {
                "governance_core": result["governance_core"],
                "governance_client": result["governance_client"],
                "core_fingerprint": result["governance_core"]["fingerprint"],
                "client_fingerprint": result["governance_client"]["fingerprint"],
                "core_item_count": len(result["core_items"]),
                "client_item_count": len(result["client_items"]),
                "core_json": str(self.build_dir / "governance-core.json"),
                "client_json": str(self.build_dir / "governance-client.json"),
                "success": True,
            }
        except Exception as exc:
            self._out(f"❌ PHASE 1 error: {exc}", level=logging.ERROR)
            return {"success": False, "error": str(exc)}

    def _run_phase_2(self) -> Phase2Result:
        try:
            runner = CompilerRunner(repo_root=self.repo_root)
            result = runner.compile(str(self.build_dir), str(self.compiled_dir))
            validation = runner.validate_compilation_detailed(str(self.compiled_dir))
            if not validation.get("ok", False):
                failed = [
                    check
                    for check in validation.get("checks", [])
                    if not check.get("ok")
                ]
                self._out(
                    f"❌ Compilation validation failed in {self.compiled_dir}",
                    level=logging.ERROR,
                )
                for check in failed:
                    self._out(
                        f"   ❌ {check.get('name')}: {check.get('details')}",
                        level=logging.ERROR,
                    )
                detail = "; ".join(
                    f"{check.get('name')}: {check.get('details')}" for check in failed
                ) or "; ".join(validation.get("errors", []))
                error = "Compilation validation failed"
                if detail:
                    error = f"{error}: {detail}"
                return {"success": False, "error": error}
            copy_build_artifacts(self.build_dir, self.compiled_dir)
            publish_canonical_artifacts(self.workspace_root, self.compiled_dir)
            return phase2_result_from_compile(result)
        except Exception as exc:
            self._out(f"❌ PHASE 2 error: {exc}", level=logging.ERROR)
            return {"success": False, "error": str(exc)}

    def _validate_full_pipeline(self, combined_result: PipelineResult) -> bool:
        all_passed = True
        for check_name, result in pipeline_checks(
            combined_result.get("phase_1", {}), combined_result.get("phase_2", {})
        ):
            self._out(f"   {'✅' if result else '❌'} {check_name}")
            if not result:
                all_passed = False
        return all_passed

    def get_deployment_summary(self) -> dict[str, Any]:
        """Return the deployment artifact summary."""
        return deployment_summary(self.compiled_dir)
