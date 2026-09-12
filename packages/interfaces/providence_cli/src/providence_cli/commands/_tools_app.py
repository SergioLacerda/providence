"""Shared `app` instance and repo-root resolver for the `tools` command group.

Exists solely to break the import cycle between `tools.py` and
`tools_run.py` (T11 split): both files need the same Typer `app` to attach
commands to, and both need `_find_repo_root`. If either imported the other
directly, one would have to be imported before it finishes defining `app`
the exact shape flagged by CodeQL's cyclic-import query, and also flagged by
`tools/architecture/validate_cycles.py`, which does not distinguish deferred
(function-local) imports from module-level ones  any textual cross-reference
between the two files counts as a cycle edge to that checker. Both files now
depend one-way on this module instead of on each other.
"""

from __future__ import annotations

from pathlib import Path

import typer

app = typer.Typer(invoke_without_command=True)


def _find_repo_root() -> Path:
    from providence_cli.utils.environment import detect_repo_root

    return detect_repo_root()
