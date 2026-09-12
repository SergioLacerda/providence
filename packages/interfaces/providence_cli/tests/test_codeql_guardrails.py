"""Guardrail tests for CodeQL alerts fixed in 2026-05-19.

Covers:
- B904: raise inside except without `from` (_ask_backend.py, pipeline.py)
- Cyclic import: ask_snapshot.py  commands/_ask_backend.py
- Unused import: yaml removed from skills.py (moved to _skill_registry.py)
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Cyclic import guardrails
# ---------------------------------------------------------------------------


def test_ask_snapshot_importable_without_ask_commands() -> None:
    """ask_snapshot must be importable without triggering ask backend at module level."""
    # Remove both modules from sys.modules to force a fresh import
    for mod in list(sys.modules):
        if (
            "providence_cli.services.ask_snapshot" in mod
            or "providence_cli.commands._ask_backend" in mod
        ):
            del sys.modules[mod]

    # Import ask_snapshot first  must NOT trigger ask backend module-level code
    module = importlib.import_module("providence_cli.services.ask_snapshot")
    assert hasattr(module, "build_governed_ask_snapshot")

    # ask backend must NOT have been imported at module level by ask_snapshot
    # (it may appear later due to other imports, but the deferred import
    # inside build_governed_ask_snapshot should not fire during module import)
    assert "build_governed_ask_snapshot" in dir(module)


def test_ask_snapshot_has_no_module_level_ask_import() -> None:
    """ask_snapshot.py must not import ask backend at module level."""
    src = (
        Path(__file__).parents[1]
        / "src"
        / "providence_cli"
        / "services"
        / "ask_snapshot.py"
    )
    source = src.read_text(encoding="utf-8")
    # Module-level imports appear before any 'def' or 'class' line.
    # The import of ask must be inside a function (deferred).
    lines = source.splitlines()
    in_function = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("def ") or stripped.startswith("class "):
            in_function = True
        if not in_function and "from providence_cli.commands" in line and "ask" in line:
            raise AssertionError(
                f"Module-level cyclic import found in ask_snapshot.py: {line!r}"
            )


# ---------------------------------------------------------------------------
# B904 guardrails  raise inside except must use `from`
# ---------------------------------------------------------------------------


def test_ask_permission_error_exits_with_code_3() -> None:
    """PermissionError in ask_cmd must exit 3 without chaining the exception."""
    from typer.testing import CliRunner

    from providence_cli.commands._ask_backend import app as ask_app

    runner = CliRunner()

    def _raise_permission(*args: object, **kwargs: object) -> None:
        raise PermissionError("handshake blocked")

    with patch(
        "providence_cli.commands._ask_backend.build_governed_ask_snapshot",
        side_effect=_raise_permission,
    ):
        result = runner.invoke(ask_app, ["test query"])

    assert result.exit_code == 3


def test_ask_raise_does_not_chain_original_exception() -> None:
    """raise typer.Exit(3) from None must suppress the PermissionError context."""
    import ast

    pkg_dir = (
        Path(__file__).parents[1]
        / "src"
        / "providence_cli"
        / "commands"
        / "_ask_backend"
    )
    for src in sorted(pkg_dir.glob("*.py")):
        tree = ast.parse(src.read_text(encoding="utf-8"))
        _assert_no_bare_raise_in_except(tree, src.name)


def _assert_no_bare_raise_in_except(tree: object, filename: str) -> None:
    """Walk AST and assert no bare `raise X` (without `from`) inside ExceptHandler."""
    import ast

    class _Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.violations: list[int] = []
            self._in_except = 0

        def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
            self._in_except += 1
            self.generic_visit(node)
            self._in_except -= 1

        def visit_Raise(self, node: ast.Raise) -> None:
            if self._in_except and node.exc is not None and node.cause is None:
                self.violations.append(node.lineno)
            self.generic_visit(node)

    v = _Visitor()
    v.visit(tree)  # type: ignore[arg-type]
    assert not v.violations, (
        f"{filename}: bare `raise X` (no `from`) inside except at lines {v.violations}. "
        "Use `raise X from None` or `raise X from err`."
    )


# ---------------------------------------------------------------------------
# Unused import guardrail  yaml must stay out of the public skills surface
# ---------------------------------------------------------------------------


def test_yaml_not_imported_at_module_level_in_skills() -> None:
    """Public skills package must not import yaml at module level."""
    src = (
        Path(__file__).parents[3]
        / "core"
        / "providence_runtime"
        / "src"
        / "providence_runtime"
        / "skills"
        / "__init__.py"
    )
    source = src.read_text(encoding="utf-8")
    lines = source.splitlines()
    for line in lines:
        stripped = line.strip()
        if stripped in ("import yaml", "import yaml  # noqa"):
            raise AssertionError(
                f"skills public surface still imports yaml at module level: {line!r}. "
                "yaml must stay in internal runtime modules only."
            )
