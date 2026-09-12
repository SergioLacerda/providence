"""Compile telemetry emission and agent seed regeneration for `providence governance compile`."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from rich.console import Console

from providence_cli.services._governance_compile_flow import regenerate_seeds_flow
from providence_cli.services._governance_compile_support import (
    compliance_components,
    resolve_output_base_path,
)
from providence_cli.utils.providence_authority import resolve_workspace_root

logger = logging.getLogger(__name__)


class RuntimeHandbookRegenerationError(RuntimeError):
    """Raised when mandatory docs-derived runtime handbook generation fails."""


def _resolve_output_base(output_dir: Path) -> Path:
    return resolve_output_base_path(
        output_dir,
        override=os.environ.get("SDD_TEST_OUTPUT_DIR", "").strip(),
        resolve_workspace_root_fn=resolve_workspace_root,
    )


def emit_compile_telemetry(
    *,
    core_fingerprint: str,
    is_error: bool,
    consistency_ok: bool,
    profile: str | None,
) -> None:
    """Emit telemetry events for a governance compile run."""
    try:
        import uuid

        from providence_runtime.telemetry import RuntimeEvent, TelemetrySink

        from providence_cli.utils.telemetry_paths import resolve_compliance_events_path
        from providence_core.utils.environment import find_workspace_root as _fws

        _ws = _fws()
        _events_path = (
            resolve_compliance_events_path(workspace_root=_ws)
            if _ws
            else resolve_compliance_events_path()
        )
        _trace_id = str(uuid.uuid4())
        sink = TelemetrySink(jsonl_path=_events_path, logging_mode="active")
        sink.emit(
            RuntimeEvent(
                event="governance.compile.complete",
                command="governance compile",
                status="ok",
                trace_id=_trace_id,
                details={
                    "core_hash": core_fingerprint[:16] if core_fingerprint else ""
                },
            )
        )

        _score, _components = compliance_components(
            compile_ok=not is_error,
            consistency_ok=consistency_ok,
            drift_detected=not consistency_ok,
        )
        _score_status = "ok" if _score >= 75 else ("warn" if _score >= 50 else "fail")
        sink.emit(
            RuntimeEvent(
                event="governance.compliance.score",
                command="governance compile",
                status=_score_status,
                trace_id=_trace_id,
                details={
                    "score": _score,
                    "components": _components,
                    "profile": profile or "client",
                },
            )
        )
        sink.flush()
    except Exception as _event_err:
        logger.debug("Failed to append governance compile event: %s", _event_err)


def regenerate_seeds(*, console: Console | None = None) -> None:
    """Regenerate agent seed files from the current governance config."""
    if console is None:
        console = Console()
    from providence_cli.generators.agent_seeds import generate_agent_instruction_files
    from providence_cli.services.governance_docs_handbook_gen import (
        generate_runtime_handbook,
    )
    from providence_cli.utils.loader import (
        load_governance_config,
        validate_governance_path,
    )

    def generate_runtime_handbook_required(*args: Any, **kwargs: Any) -> list[Path]:
        try:
            return generate_runtime_handbook(*args, **kwargs)
        except Exception as exc:
            raise RuntimeHandbookRegenerationError(
                f"could not regenerate runtime handbook: {exc}"
            ) from exc

    try:
        regenerate_seeds_flow(
            console=console,
            resolve_workspace_root_fn=resolve_workspace_root,
            validate_governance_path_fn=validate_governance_path,
            load_governance_config_fn=load_governance_config,
            resolve_output_base_fn=_resolve_output_base,
            generate_agent_instruction_files_fn=generate_agent_instruction_files,
            generate_runtime_handbook_fn=generate_runtime_handbook_required,
        )
    except RuntimeHandbookRegenerationError:
        raise
    except Exception as _gen_err:
        console.print(
            f"[yellow]WARN: could not auto-regenerate agent files: {_gen_err}[/yellow]"
        )
