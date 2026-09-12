"""Regression tests for generate_runtime_handbook_required()'s repo-root
resolution  see .analysis/pending/20260906-editable-install-leak-repro.md.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from rich.console import Console

from providence_cli.services.governance_generate_prereqs import (
    generate_runtime_handbook_required,
)


def test_does_not_fall_back_to_leaked_repo_root_under_editable_install(
    tmp_path: Path,
) -> None:
    """Under an editable install, `detect_repo_root()`'s `__file__`-parents
    fallback used to resolve to this harness's own checkout, so this
    function would source the runtime handbook registry from the harness's
    own docs instead of the caller's workspace. It now passes
    `allow_file_fallback=False`, so a real cwd-search failure must not reach
    that fallback at all."""
    output_base = tmp_path / "output"
    output_base.mkdir()
    harness_like = tmp_path / "harness-checkout"
    (harness_like / "docs").mkdir(parents=True)

    with (
        patch(
            "providence_cli.utils.providence_authority.resolve_workspace_root",
            return_value=None,
        ),
        patch(
            "providence_cli.utils.environment.detect_repo_root",
            side_effect=RuntimeError("SDD Project root not found"),
        ),
        patch(
            "providence_cli.services.governance_docs_handbook_gen.generate_runtime_handbook",
            return_value=[],
        ) as mock_generate,
    ):
        generate_runtime_handbook_required(output_base, console=Console(), quiet=True)

    mock_generate.assert_called_once_with(output_base, runtime_root=output_base)


def test_uses_detected_repo_root_when_it_has_the_registry(tmp_path: Path) -> None:
    """When detect_repo_root() succeeds (e.g. a real cwd-based match, not the
    file-fallback), its registry is still used as a valid source_root."""
    from providence_cli.services.governance_docs_sources import DEFAULT_REGISTRY

    output_base = tmp_path / "output"
    output_base.mkdir()
    real_root = tmp_path / "real-repo"
    registry_path = real_root / DEFAULT_REGISTRY
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text("{}", encoding="utf-8")

    with (
        patch(
            "providence_cli.utils.providence_authority.resolve_workspace_root",
            return_value=None,
        ),
        patch(
            "providence_cli.utils.environment.detect_repo_root",
            return_value=real_root,
        ),
        patch(
            "providence_cli.services.governance_docs_handbook_gen.generate_runtime_handbook",
            return_value=[],
        ) as mock_generate,
    ):
        generate_runtime_handbook_required(output_base, console=Console(), quiet=True)

    mock_generate.assert_called_once_with(real_root, runtime_root=output_base)
