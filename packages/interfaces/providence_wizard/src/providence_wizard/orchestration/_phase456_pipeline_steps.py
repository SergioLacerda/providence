"""Phase 5-6 pipeline step helpers: compile, deploy, validate, scaffold."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from providence_adapters import AdapterGenerator
from providence_wizard.constants import RUNTIME_DIRNAME

from .deployer.seedling_injector import SeedlingInjector
from .deployer.template_deployer import TemplateDeployer
from .install_snapshot import GovernanceInstallSnapshot
from .phase5_artifact_compiler import ArtifactCompiler
from .phase6_output_validator import OutputValidator
from .wizard.models import Phase456RunResult


def _compile_artifacts(
    repo_root: Path,
    sdd_dir: Path,
    runtime_dir: Path,
    mandates: list[dict[str, Any]],
    guidelines: dict[str, dict[str, Any]],
    guidelines_by_category: dict[str, list[dict[str, Any]]],
    config: dict[str, Any],
    verbose: bool,
    emit: Callable[[str], None],
) -> tuple[bool, Any]:
    """Compile governance artifacts and generate metadata."""
    compiler = ArtifactCompiler(
        repo_root=repo_root,
        sdd_dir=sdd_dir,
        runtime_dir=runtime_dir,
        mandates=mandates,
        guidelines=guidelines,
        guidelines_by_category=guidelines_by_category,
        config=config,
        verbose=verbose,
        emitter=emit,
    )
    if not compiler.compile_artifacts() and verbose:
        emit("      Artifact compilation skipped or failed (non-critical)")
    if not compiler.generate_metadata():
        return False, compiler
    return True, compiler


def _deploy_ide_templates(
    repo_root: Path,
    output_base: Path,
    config: dict[str, Any],
    verbose: bool,
    compiler: Any,
    result: Phase456RunResult,
    selected_seedlings: set[str] | None = None,
) -> bool:
    """Deploy IDE templates and inject bootstrap metadata (Phase 6)."""
    deployer = TemplateDeployer(
        repo_root=repo_root,
        output_base=output_base,
        config=config,
        verbose=verbose,
        selected_seedlings=selected_seedlings,
    )
    injector = SeedlingInjector(
        repo_root=repo_root, output_base=output_base, verbose=verbose
    )
    if not deployer.copy_templates():
        result["errors"].append("Failed to copy templates")
        return False
    if not deployer.create_ide_templates():
        result["errors"].append("Failed to copy configuration templates")
        return False
    snapshot = GovernanceInstallSnapshot.from_compiler(
        compiler,
        workspace_root=str(repo_root),
        handshake_mode=config.get("handshake_mode", "standard"),
        hook_agents=config.get("prompt_submit_hook_agents", []),
    )
    injector.inject_bootstrap_metadata(
        fingerprint=snapshot.governance_fingerprint,
        generated_at=snapshot.generated_at,
        mandates_count=len(snapshot.mandates),
    )
    injector.populate_ide_rules(
        mandates=snapshot.mandates,
        fingerprint=snapshot.governance_fingerprint,
    )
    return True


def _validate_output(
    output_base: Path,
    guidelines_by_category: dict[str, list[dict[str, Any]]],
    config: dict[str, Any],
    verbose: bool,
    emit: Callable[[str], None],
    result: Phase456RunResult,
    selected_seedlings: set[str] | None = None,
) -> bool:
    """Validate generated output structure (Phase 6)."""
    sdd_dir = output_base / RUNTIME_DIRNAME
    source_dir = sdd_dir / "source"
    validator = OutputValidator(
        output_base=output_base,
        sdd_dir=sdd_dir,
        source_dir=source_dir,
        runtime_dir=sdd_dir / "runtime",
        mandates_dir=source_dir / "mandates",
        guidelines_dir=source_dir / "guidelines",
        guidelines_by_category=guidelines_by_category,
        config=config,
        verbose=verbose,
        emitter=emit,
        selected_seedlings=selected_seedlings,
    )
    valid, validation_result = validator.validate()
    if not valid:
        result["errors"].extend(validation_result["errors"])
        return False
    result["validation"] = validation_result["checks"]
    return True


def _create_source_directories(
    output_base: Path,
    mandates_dir: Path,
    guidelines_dir: Path,
    runtime_dir: Path,
) -> bool:
    """Create governance runtime output directory structure."""
    try:
        mandates_dir.mkdir(parents=True, exist_ok=True)
        guidelines_dir.mkdir(parents=True, exist_ok=True)
        runtime_dir.mkdir(parents=True, exist_ok=True)
        (output_base / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"   Failed to create directories: {e}")  # noqa: T201
        return False


def _generate_plugin_workspace_dirs(
    output_base: Path,
    config: dict[str, Any],
) -> bool:
    """Generate plugin workspace under the governance runtime directory."""
    try:
        from providence_cli.generators._contracts import generate_contracts
        from providence_cli.generators._plugins import generate_plugins_registry

        generate_plugins_registry(str(output_base), config)
        generate_contracts(str(output_base), config)
        for state in ("todo", "pending", "refined", "done"):
            (output_base / RUNTIME_DIRNAME / "analysis" / state).mkdir(
                parents=True, exist_ok=True
            )
        (output_base / RUNTIME_DIRNAME / "docs").mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"   Failed to generate plugin workspace: {e}")  # noqa: T201
        return False


def _generate_adapters(
    output_base: Path, emit: Callable[[str], None], verbose: bool = False
) -> None:
    """Generate Level 2 adapters (skills/commands per agent)."""
    try:
        adapter_gen = AdapterGenerator()
        adapter_results = adapter_gen.generate(output_dir=output_base)
        successes = 0
        failures: list[str] = []
        for target, adapter_result in adapter_results.items():
            if adapter_result.success:
                successes += 1
                if verbose:
                    emit(
                        f" Generated {len(adapter_result.files_written)} adapter files for {target}"
                    )
            else:
                failures.append(target)
                if verbose:
                    emit(
                        f"  Adapter generation for {target} had errors: {adapter_result.errors}"
                    )
        if failures:
            emit(f"adapters...WARN ({', '.join(failures)})")
        else:
            emit(f"adapters...OK ({successes})")
    except Exception as e:
        if verbose:
            emit(f"  Adapter generation failed (non-critical): {e}")
        emit("adapters...WARN")
