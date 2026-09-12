"""providence ask  dossier build/load/error helpers.

Split out of `_telemetry.py` (T15,
`.analysis/pending/2026-06-15-providence-cli-refactoring-pending-followup.md`).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import typer

from providence_cli.services.ask_dossier import (
    build_and_output_dossier as _build_and_output_dossier_impl,
)
from providence_cli.services.ask_dossier import (
    handle_dossier_error as _handle_dossier_error_impl,
)
from providence_cli.services.ask_dossier import (
    load_dossier_artifact as _load_dossier_artifact_impl,
)
from providence_cli.utils.providence_authority import compiled_active_dir

logger = logging.getLogger(__name__)


def _handle_dossier_error(exc: Exception) -> None:
    _handle_dossier_error_impl(exc, logger=logger, typer_module=typer)


def _build_and_output_dossier(
    query: str,
    skill: str | None,
    budget: int | None,
    mandates_count: int,
    workspace_root: Path | None = None,
) -> None:
    from providence_cli.commands import _ask_backend as _backend

    _build_and_output_dossier_impl(
        query=query,
        skill=skill,
        budget=budget,
        mandates_count=mandates_count,
        workspace_root=workspace_root,
        resolve_workspace_root_fn=_backend._resolve_workspace_root,
        compiled_active_dir_fn=compiled_active_dir,
        logger=logger,
        typer_module=typer,
    )


def _load_dossier_artifact(workspace_root: Path) -> Any | None:
    artifact = _load_dossier_artifact_impl(
        workspace_root, compiled_active_dir_fn=compiled_active_dir
    )
    if artifact is None:
        compiled_path = compiled_active_dir(workspace_root) / "governance-core.json"
        logger.debug("Could not load artifact from %s", compiled_path)
    return artifact
