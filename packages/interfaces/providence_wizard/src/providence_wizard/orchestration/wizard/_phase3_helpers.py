"""Module-level helper functions for Phase3Compiler."""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

from providence_core.utils.environment import get_sdd_paths
from providence_wizard.constants import (
    GOVERNANCE_CLIENT_FILENAME,
    GOVERNANCE_CORE_FILENAME,
)

from .guidelines_compiler import GuidelinesCompiler
from .mandates_compiler import MandatesCompiler
from .source_readme_compiler import SourceReadmeCompiler


def _copy_seedlings(
    repo_root: Path,
    output_path: Path,
    emitter: Callable[[str], None],
) -> bool:
    """Copy seedling templates from providence_integration into output_path."""
    try:
        source_seedling_dir = (
            repo_root
            / "packages"
            / "features"
            / "providence_integration"
            / "src"
            / "providence_integration"
            / "templates"
        )
        if not source_seedling_dir.exists():
            return True
        output_path.mkdir(parents=True, exist_ok=True)
        for seedling_type in (".github", ".vscode", ".cursor"):
            source_path = source_seedling_dir / seedling_type
            if source_path.exists():
                target_path = output_path / seedling_type
                target_path.mkdir(parents=True, exist_ok=True)
                for item in source_path.rglob("*"):
                    if item.is_file():
                        dest = target_path / item.relative_to(source_path)
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dest)
        return True
    except Exception as exc:
        emitter(f"   Error copying seedlings: {exc}")
        import traceback

        traceback.print_exc()
        return False


def _generate_spec_file(
    repo_root: Path, output_path: Path, emitter: Callable[[str], None]
) -> None:
    """Generate mandates.json spec file from canonical mandate markdown files."""
    try:
        from providence_integration.builders.governance.pipeline_builder import (
            PipelineBuilder,
        )

        canonical_dir = repo_root / "docs" / "spec" / "canonical" / "core" / "mandates"
        if not canonical_dir.is_dir() or not list(canonical_dir.glob("M*.md")):
            return
        spec_output = output_path / "spec" / "mandates.json"
        result = PipelineBuilder.generate_spec_file(
            canonical_mandates_dir=canonical_dir,
            output_path=spec_output,
            generated_by="providence-wizard",
        )
        emitter(f"   Spec file: {result['mandates_written']} mandates  {spec_output}")
    except Exception as exc:
        emitter(f"    Spec file generation skipped: {exc}")


def _compile_with_pipeline_builder(
    repo_root: Path,
    output_path: Path,
    items: dict[str, list[dict[str, Any]]],
    emitter: Callable[[str], None],
) -> bool:
    """Run PipelineBuilder on parsed items and save outputs to .providence/source/."""
    try:
        from providence_integration.builders.governance.pipeline_builder import (
            PipelineBuilder,
        )

        try:
            paths = get_sdd_paths()
            spec_path = paths.get("docs_meta", paths["client_build"] / "docs-meta")
        except RuntimeError:
            spec_path = repo_root / "generated" / "client" / "build" / "docs-meta"

        builder = PipelineBuilder(
            str(spec_path),
            parsed_items=items,
        )
        builder.build()
        source = output_path / "source"
        source.mkdir(parents=True, exist_ok=True)
        builder.save_outputs(str(source))
        return True
    except ImportError as exc:
        emitter(f" PipelineBuilder not available as package: {exc}")
        return False
    except Exception as exc:
        emitter(f" Pipeline builder error: {exc}")
        import traceback

        traceback.print_exc()
        return False


def _generate_source_files(
    output_path: Path,
    language: str,
    emitter: Callable[[str], None],
    mandates: list[dict[str, Any]],
    guidelines: list[dict[str, Any]],
) -> str | None:
    """Write mandates.md, guidelines files, and source README. Returns error msg or None."""
    if not MandatesCompiler(output_path, language, emitter).write(mandates):
        return "Failed to generate mandates.md"
    if not GuidelinesCompiler(output_path, emitter).write(guidelines):
        return "Failed to generate guidelines files"
    if not SourceReadmeCompiler(output_path, language, emitter).write(
        mandates, guidelines
    ):
        return "Failed to generate source README"
    return None


def _load_compiled_governance(
    output_path: Path,
    emitter: Callable[[str], None],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Load mandates and guidelines from compiled governance JSON files."""
    try:
        source_dir = output_path / "source"
        mandates: list[dict[str, Any]] = []
        guidelines: list[dict[str, Any]] = []
        core_file = source_dir / GOVERNANCE_CORE_FILENAME
        client_file = source_dir / GOVERNANCE_CLIENT_FILENAME
        if core_file.exists():
            with open(core_file, encoding="utf-8") as f:
                for item in json.load(f).get("items", []):
                    if item["type"] == "MANDATE":
                        mandates.append(item)
        if client_file.exists():
            with open(client_file, encoding="utf-8") as f:
                for item in json.load(f).get("items", []):
                    if item["type"] == "GUIDELINE":
                        guidelines.append(item)
        return mandates, guidelines
    except Exception as exc:
        emitter(f"   Error loading compiled governance: {exc}")
        import traceback

        traceback.print_exc()
        return [], []
