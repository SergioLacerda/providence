"""Regression guard for M015 handshake runtime drift.

`AgentHandshakeProtocol()` with no `project_root` resolves to the real
repository root (via cwd-based `find_project_root`). A test that
accidentally constructs it that way — as
`packages/core/providence_runtime/tests/test_handshake_enforcement.py`
once did — silently rewrites the live
`.providence/runtime/handshake-challenge.json`, invalidating any handshake
response bound to the previous challenge and causing
`providence governance validate` to report `Active handshake (M015): FAIL`
for reasons unrelated to governance artifact integrity. See
`.analysis/refined/20260912-m015-handshake-runtime-drift/`.

The repository-root `conftest.py` guard (`_forbid_repo_sdd_writes`) is what
actually prevents the mutation; this test proves that guard holds even when
a test explicitly points `AgentHandshakeProtocol` at the real repository
root, so a future regression fails loudly here instead of corrupting the
live workspace runtime.
"""

from __future__ import annotations

from pathlib import Path

from providence_core.governance.handshake import AgentHandshakeProtocol


def _find_repo_root(start: Path) -> Path:
    for parent in [start, *start.parents]:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError(f"could not locate repository root above {start}")


_REPO_ROOT = _find_repo_root(Path(__file__).resolve())
_CHALLENGE_FILE = _REPO_ROOT / ".providence" / "runtime" / "handshake-challenge.json"


def test_generate_challenge_does_not_mutate_repository_root_runtime():
    before = _CHALLENGE_FILE.read_bytes() if _CHALLENGE_FILE.exists() else None

    ahp = AgentHandshakeProtocol(project_root=_REPO_ROOT)
    ahp.generate_challenge(task_description="repo-root-isolation-regression-guard")

    after = _CHALLENGE_FILE.read_bytes() if _CHALLENGE_FILE.exists() else None
    assert after == before, (
        "repository-root .providence/runtime/handshake-challenge.json was "
        "mutated by a test run — the repository-root conftest.py write "
        "guard should have blocked this write"
    )
