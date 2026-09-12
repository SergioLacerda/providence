"""ask_types  shared dataclasses for `providence ask` request/session state.

Extracted from `commands/_ask_backend.py` so that
`services/ask_response.py` can depend on these types without
creating a module-level cyclic import with `_ask_backend.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from providence_cli.commands._ask_backend._phase_timer import PhaseTimer


def _default_phase_timer() -> PhaseTimer:
    # Deferred import: avoids a module-load-time cycle with
    # `commands._ask_backend` (which imports from `services`). Safe here
    # because this only runs at dataclass-instantiation time, well after
    # both modules have finished importing.
    from providence_cli.commands._ask_backend._phase_timer import PhaseTimer

    return PhaseTimer()


@dataclass(frozen=True)
class _AskInputs:
    query: str
    dossier: bool
    skill: str | None
    budget: int | None
    full: bool
    log_path: str | None
    log_format: str
    tokens_input: int | None
    tokens_output: int | None


@dataclass(frozen=True)
class _AskSessionContext:
    workspace_root: Path
    organize_used: bool
    organize_reason: str
    organize_artifact_path: str
    organize_chunks: int
    organize_retrieval: str
    cached_handbook_task_type: str | None
    profile: str
    state: str
    agent_id: str
    trace_id: str
    start_mono: float
    start_ts: str
    phase_timer: PhaseTimer = field(default_factory=_default_phase_timer)
