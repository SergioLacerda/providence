"""Shared `app` instance for the `audit` command group.

Exists solely to break the import cycle between `audit.py` and
`audit_export_commands.py` (T12 split): both files need the same Typer `app`
to attach commands to, but if either imported the other directly, one would
have to be imported before it finishes defining `app`  the exact shape
flagged by CodeQL's cyclic-import query. Both now depend one-way on this
module instead of on each other.
"""

from __future__ import annotations

import typer

app = typer.Typer(
    help="Governance audit and drift analytics", invoke_without_command=True
)
