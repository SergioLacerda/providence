"""Contract test session setup.

Recompiles governance artifacts before the contract test suite runs.
This prevents stale-artifact failures when tests are invoked via
'providence test run', 'make check', or 'pytest tests/contract/' directly.

In CI, the bootstrap action already compiles and validates artifacts
(providence governance compile + sync). The fixture skips recompilation when
valid artifacts are already present to avoid a redundant pipeline run
that could fail due to env differences (e.g. missing .providence/source/).
"""

from __future__ import annotations

import contextlib
import os
import re
import shutil
import time
from pathlib import Path

import pytest

from providence_cli.utils.providence_authority import (
    compiled_active_dir,
    resolve_workspace_root,
)

_ITEM_ID_PATTERN = re.compile(r"^[A-Z]\d{2,3}$")


def _repo_compiled_dir(repo_root: Path) -> Path:
    return repo_root / ".providence" / "compiled"


def _repo_artifacts_valid(repo_root: Path) -> bool:
    import json as _json

    compiled_dir = _repo_compiled_dir(repo_root)
    core = compiled_dir / "governance-core.json"
    client = compiled_dir / "governance-client.json"
    if not core.exists() or not client.exists():
        return False
    with contextlib.suppress(Exception):
        core_data = _json.loads(core.read_text(encoding="utf-8"))
        client_data = _json.loads(client.read_text(encoding="utf-8"))
        core_items = core_data.get("items", [])
        client_items = client_data.get("items", [])
        if (
            len(core_items) >= 4
            and len(client_items) >= 2
            and all("id" in item for item in core_items)
            and all(
                _ITEM_ID_PATTERN.match(str(item.get("id", ""))) for item in client_items
            )
        ):
            return True
    return False


def _sync_repo_artifacts_into_workspace(repo_root: Path, workspace_root: Path) -> None:
    compiled_src = _repo_compiled_dir(repo_root)
    compiled_dst = workspace_root / ".providence" / "compiled"
    compiled_dst.mkdir(parents=True, exist_ok=True)
    for name in (
        "governance-core.json",
        "governance-client.json",
        "governance-core.compiled.msgpack",
        "governance-client-template.compiled.msgpack",
        "metadata-core.json",
        "metadata-client-template.json",
    ):
        src = compiled_src / name
        if src.exists():
            shutil.copy2(src, compiled_dst / name)


def _artifacts_valid(repo_root: Path) -> bool:
    """Return True if compiled artifacts exist and contain a viable mandate set."""
    import json as _json

    del repo_root
    compiled_dir = compiled_active_dir()
    canonical = compiled_dir / "governance-core.json"
    client = compiled_dir / "governance-client.json"
    if not canonical.exists() or not client.exists():
        return False
    with contextlib.suppress(Exception):
        core_data = _json.loads(canonical.read_text(encoding="utf-8"))
        core_items = core_data.get("items", [])
        client_data = _json.loads(client.read_text(encoding="utf-8"))
        client_items = client_data.get("items", [])
        if (
            len(core_items) >= 4
            and all("id" in item for item in core_items)
            and all(
                _ITEM_ID_PATTERN.match(str(item.get("id", ""))) for item in client_items
            )
        ):
            return True
    return False


def _sync_repo_artifacts_if_available(repo_root: Path, workspace_root: Path) -> None:
    if _repo_artifacts_valid(repo_root):
        _sync_repo_artifacts_into_workspace(repo_root, workspace_root)


def _artifact_state_ready(repo_root: Path, workspace_root: Path) -> bool:
    if not _artifacts_valid(repo_root):
        return False
    _sync_repo_artifacts_if_available(repo_root, workspace_root)
    return True


def _acquire_compile_lock(
    lock_file: Path, *, timeout_seconds: float, repo_root: Path
) -> int:
    deadline = time.time() + timeout_seconds
    while True:
        try:
            lock_fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(lock_fd, str(os.getpid()).encode("utf-8"))
            return lock_fd
        except FileExistsError:
            if _artifacts_valid(repo_root):
                return -1
            if time.time() >= deadline:
                pytest.fail(f"Timeout waiting for governance compile lock: {lock_file}")
            time.sleep(0.2)


def _compile_fresh_governance(repo_root: Path, workspace_root: Path) -> None:
    from providence_core.governance_orchestrator import GovernanceOrchestrator

    result = GovernanceOrchestrator(
        repo_root=str(repo_root),
        workspace_root=str(workspace_root),
    ).run_full_pipeline()
    if not result.get("full_pipeline_success"):
        pytest.fail(f"Governance compilation failed before contract tests: {result}")
    _sync_repo_artifacts_if_available(repo_root, workspace_root)


@pytest.fixture(scope="session", autouse=True)
def fresh_governance_artifact() -> None:
    """Ensure governance-core.json is up to date before contract tests run.

    Skips recompilation when valid artifacts already exist (CI bootstrap path).
    Forces recompilation when run directly or artifacts are missing/stale.
    """
    repo_root = Path(__file__).parent.parent.parent
    workspace_root = resolve_workspace_root()

    if _artifact_state_ready(repo_root, workspace_root):
        return

    # xdist workers can enter this fixture concurrently and race while
    # writing/reading governance artifacts. Serialize compilation with a lock.
    lock_file = workspace_root / ".providence" / "runtime" / "contract-compile.lock"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = _acquire_compile_lock(
        lock_file, timeout_seconds=60.0, repo_root=repo_root
    )
    if lock_fd == -1:
        _sync_repo_artifacts_if_available(repo_root, workspace_root)
        return

    try:
        if _artifact_state_ready(repo_root, workspace_root):
            return
        _compile_fresh_governance(repo_root, workspace_root)
    finally:
        if lock_fd >= 0:
            os.close(lock_fd)
        with contextlib.suppress(Exception):
            lock_file.unlink(missing_ok=True)
