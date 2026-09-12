from __future__ import annotations

from typing import Any, TypedDict


class Phase1Result(TypedDict, total=False):
    governance_core: dict[str, Any]
    governance_client: dict[str, Any]
    core_fingerprint: str
    client_fingerprint: str
    core_item_count: int
    client_item_count: int
    core_json: str
    client_json: str
    success: bool
    error: str


class Phase2Result(TypedDict, total=False):
    core_msgpack_file: str
    client_msgpack_file: str
    core_fingerprint_salt: str
    client_fingerprint: str
    success: bool
    error: str


class PipelineResult(TypedDict):
    full_pipeline_success: bool
    phase_1: Phase1Result
    phase_2: Phase2Result
    validated: bool
