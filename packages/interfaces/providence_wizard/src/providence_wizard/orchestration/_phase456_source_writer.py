"""Phase 5 source-writing helper for Phase456Generator."""

from __future__ import annotations

import contextlib
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .wizard.models import Phase456RunResult
from .writers.guidelines_writer import GuidelinesWriter
from .writers.mandates_writer import MandatesWriter
from .writers.readme_writer import ReadmeWriter


def write_phase5_sources(
    output_base: Path,
    mandates_dir: Path,
    guidelines_dir: Path,
    source_dir: Path,
    runtime_dir: Path,
    mandates: list[dict[str, Any]],
    guidelines: dict[str, dict[str, Any]],
    guidelines_by_category: dict[str, list[dict[str, Any]]],
    config: dict[str, Any],
    verbose: bool,
    result: Phase456RunResult,
    create_source_directories: Callable[[Path, Path, Path, Path], bool],
    generate_plugin_workspace_dirs: Callable[[Path, dict[str, Any]], bool],
) -> bool:
    """Write source files (Phase 5)."""
    from providence_core.utils.environment import is_repo_root

    if os.environ.get("SDD_TEST_OUTPUT_DIR"):
        with contextlib.suppress(OSError, ValueError):
            if is_repo_root(output_base.resolve()):
                result["errors"].append(
                    f"SDD_ISOLATION_ERROR: Mutation of repo root blocked ({output_base})"
                )
                return False
    mandates_wr = MandatesWriter(mandates_dir, mandates, config, verbose)
    guidelines_wr = GuidelinesWriter(guidelines_dir, guidelines_by_category, verbose)
    readme_wr = ReadmeWriter(
        source_dir,
        runtime_dir,
        mandates,
        guidelines,
        guidelines_by_category,
        config,
        verbose,
    )
    steps: list[tuple[Callable[[], bool], str]] = [
        (
            lambda: create_source_directories(
                output_base, mandates_dir, guidelines_dir, runtime_dir
            ),
            "Failed to create directories",
        ),
        (mandates_wr.generate, "Failed to generate mandates"),
        (guidelines_wr.generate, "Failed to generate guidelines"),
        (readme_wr.generate_source_readme, "Failed to generate source README"),
        (readme_wr.generate_runtime_readme, "Failed to generate runtime README"),
        (
            lambda: generate_plugin_workspace_dirs(output_base, config),
            "Failed to generate plugin workspace",
        ),
    ]
    for step, label in steps:
        if not step():
            result["errors"].append(label)
            return False
    return True
