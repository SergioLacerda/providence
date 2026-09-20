"""Repository-root pytest guard: forbid writes to the real M015 handshake state.

This must live at the repository root, not under `tests/`. Pytest's
`testpaths` include both `tests` and `packages`, and package-local test
trees such as `packages/core/providence_runtime/tests/` are not descendants
of `tests/` — a conftest.py fixture defined only in `tests/conftest.py`
never applies to them. Placing the guard here makes it autouse for every
test collected anywhere in the repository.

This guard was added after confirming that
`packages/core/providence_runtime/tests/test_handshake_enforcement.py::
test_handshake_challenge_generation` instantiated `AgentHandshakeProtocol()`
with no `project_root`, which resolves to this repository's real root, and
silently rewrote the live `.providence/runtime/handshake-challenge.json`
on every run — invalidating any handshake response bound to the previous
challenge and causing `providence governance validate` to report
`Active handshake (M015): FAIL` for reasons unrelated to governance
artifact integrity. See
`.analysis/refined/20260912-m015-handshake-runtime-drift/`.

Deliberately narrow: this only guards the three files
`.providence/runtime/{handshake-challenge,handshake-response,
governance-state}.json` — the handshake/session-authorization state named in
that mission's Forbidden list — not the whole `.providence/` tree. A wider
guard (e.g. blocking any write under `.providence/runtime/`) was tried first
and broke unrelated, pre-existing test behavior: several `packages/**/tests`
suites (deployment, skill runtime, CLI generate) legitimately create other
`.providence/runtime/` state when `SDD_WORKSPACE_ROOT` isn't set, which only
happens to point at the real repo because `tests/conftest.py`'s
session-wide isolation setup didn't run for that invocation. That is a
separate, pre-existing test-isolation gap unrelated to M015 and out of
scope here.
"""

from __future__ import annotations

import builtins
import io
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parent
_REPO_SDD_RUNTIME = (_REPO_ROOT / ".providence" / "runtime").resolve()
_FORBIDDEN_NAMES = {
    "handshake-challenge.json",
    "handshake-response.json",
    "governance-state.json",
}


def _resolve_candidate_path(target: Any) -> Path | None:
    """Best-effort conversion of path-like target to absolute Path."""
    try:
        candidate = Path(target)
    except Exception:
        return None
    if not candidate.is_absolute():
        candidate = (Path.cwd() / candidate).resolve()
    else:
        candidate = candidate.resolve()
    return candidate


def _is_repo_sdd_path(target: Any) -> bool:
    candidate = _resolve_candidate_path(target)
    if candidate is None:
        return False
    if candidate.name not in _FORBIDDEN_NAMES:
        return False
    try:
        return candidate.parent == _REPO_SDD_RUNTIME
    except Exception:
        return False


def _guard_repo_sdd_write(target: Any, op: str) -> None:
    if _is_repo_sdd_path(target):
        raise RuntimeError(
            f"TEST POLICY: write to repository M015 handshake state is "
            f"forbidden (op={op}, path={target}). Pass an explicit "
            f"project_root=tmp_path instead of relying on cwd-based "
            f"resolution (AgentHandshakeProtocol()/HandshakeChallenge() with "
            f"no project_root resolves to the real repository root)."
        )


@pytest.fixture(autouse=True)
def _forbid_repo_sdd_writes(monkeypatch: pytest.MonkeyPatch) -> Any:  # noqa: C901
    """Hard-fail any test-time write mutation under repository .providence."""
    original_open = builtins.open

    def guarded_builtin_open(file: Any, mode: str = "r", *args: Any, **kwargs: Any):
        if any(flag in mode for flag in ("w", "a", "x", "+")):
            _guard_repo_sdd_write(file, "open")
        return original_open(file, mode, *args, **kwargs)

    original_io_open = io.open

    def guarded_io_open(file: Any, mode: str = "r", *args: Any, **kwargs: Any):
        if any(flag in mode for flag in ("w", "a", "x", "+")):
            _guard_repo_sdd_write(file, "io.open")
        return original_io_open(file, mode, *args, **kwargs)

    original_path_open = Path.open

    def guarded_path_open(self: Path, mode: str = "r", *args: Any, **kwargs: Any):  # noqa: ANN001
        if any(flag in mode for flag in ("w", "a", "x", "+")):
            _guard_repo_sdd_write(self, "Path.open")
        return original_path_open(self, mode, *args, **kwargs)

    original_write_text = Path.write_text
    original_write_bytes = Path.write_bytes
    original_touch = Path.touch
    original_mkdir = Path.mkdir
    original_unlink = Path.unlink
    original_rename = Path.rename
    original_replace = Path.replace

    def guarded_write_text(self: Path, *args: Any, **kwargs: Any):
        _guard_repo_sdd_write(self, "Path.write_text")
        return original_write_text(self, *args, **kwargs)

    def guarded_write_bytes(self: Path, *args: Any, **kwargs: Any):
        _guard_repo_sdd_write(self, "Path.write_bytes")
        return original_write_bytes(self, *args, **kwargs)

    def guarded_touch(self: Path, *args: Any, **kwargs: Any):
        _guard_repo_sdd_write(self, "Path.touch")
        return original_touch(self, *args, **kwargs)

    def guarded_mkdir(self: Path, *args: Any, **kwargs: Any):
        _guard_repo_sdd_write(self, "Path.mkdir")
        return original_mkdir(self, *args, **kwargs)

    def guarded_unlink(self: Path, *args: Any, **kwargs: Any):
        _guard_repo_sdd_write(self, "Path.unlink")
        return original_unlink(self, *args, **kwargs)

    def guarded_rename(self: Path, target: Any, *args: Any, **kwargs: Any):
        _guard_repo_sdd_write(self, "Path.rename-src")
        _guard_repo_sdd_write(target, "Path.rename-dst")
        return original_rename(self, target, *args, **kwargs)

    def guarded_replace(self: Path, target: Any, *args: Any, **kwargs: Any):
        _guard_repo_sdd_write(self, "Path.replace-src")
        _guard_repo_sdd_write(target, "Path.replace-dst")
        return original_replace(self, target, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded_builtin_open)
    monkeypatch.setattr(io, "open", guarded_io_open)
    monkeypatch.setattr(Path, "open", guarded_path_open)
    monkeypatch.setattr(Path, "write_text", guarded_write_text)
    monkeypatch.setattr(Path, "write_bytes", guarded_write_bytes)
    monkeypatch.setattr(Path, "touch", guarded_touch)
    monkeypatch.setattr(Path, "mkdir", guarded_mkdir)
    monkeypatch.setattr(Path, "unlink", guarded_unlink)
    monkeypatch.setattr(Path, "rename", guarded_rename)
    monkeypatch.setattr(Path, "replace", guarded_replace)

    return


_WORKSPACE_ENV_VARS = (
    "PROVIDENCE_WORKSPACE_ROOT",
    "SDD_ASK_ENTRYPOINT",
)


@pytest.fixture
def hermetic_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Any:
    """Isolate a test from the developer's real runtime.

    Hook, entrypoint and seed tests must not depend on folders that only exist
    in a real checkout (`.providence/`, `.claude/`, `~/.providence/`, ...).
    This fixture gives the test a fake home that looks like a machine with the
    *global* CLI installed (`~/.providence/{bin,runtime}` and no workspace
    marker), drops inherited workspace-root variables, and returns a
    `SimpleNamespace(home=..., projects=...)`; use `governed_project` below to create
    a governed project under it.
    """
    from types import SimpleNamespace

    home = tmp_path / "home"
    (home / ".providence" / "bin").mkdir(parents=True)
    (home / ".providence" / "runtime").mkdir(parents=True)
    projects = home / "dev"
    projects.mkdir()
    for var in ("HOME", "USERPROFILE"):
        monkeypatch.setenv(var, str(home))
    for var in _WORKSPACE_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    return SimpleNamespace(home=home, projects=projects)


@pytest.fixture
def governed_project(hermetic_env: Any) -> Path:
    """A governed project root: own `.git` boundary and `.providence/metadata.json`."""
    root = hermetic_env.projects / "project"
    (root / ".git").mkdir(parents=True)
    (root / ".providence").mkdir()
    (root / ".providence" / "metadata.json").write_text("{}", encoding="utf-8")
    return root
