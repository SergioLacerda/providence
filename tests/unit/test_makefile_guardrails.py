from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
MAKEFILE = REPO_ROOT / "Makefile"
MK_INCLUDES_DIR = REPO_ROOT / "mk"


def _makefile_content() -> str:
    # The root Makefile is a thin orchestrator that `include`s mk/*.mk, grouped
    # by affinity (see .analysis/refined/20260809-makefile-worldclass-refactor/
    # design.md) — guardrails must cover the full effective Makefile, not just
    # the root file, or a recipe moved into mk/*.mk silently escapes them.
    parts = [MAKEFILE.read_text(encoding="utf-8")]
    parts.extend(
        path.read_text(encoding="utf-8")
        for path in sorted(MK_INCLUDES_DIR.glob("*.mk"))
    )
    return "\n".join(parts)


def test_makefile_disallows_inline_python_c() -> None:
    content = _makefile_content()
    assert "python -c" not in content
    assert '"-c"' not in content


def test_makefile_disallows_shell_c_inline_commands() -> None:
    content = _makefile_content()
    forbidden = re.compile(r"\b(?:sh|bash)\s+-c\b")
    assert forbidden.search(content) is None


def test_docs_build_publishes_selector_artifacts() -> None:
    content = _makefile_content()
    # docs-build must inline the selector compiler targeting the mkdocs output dir
    # (not docs/ — docs/ must not receive runtime-generated files)
    make_tasks = (REPO_ROOT / "tools" / "maintenance" / "make_tasks.py").read_text(
        encoding="utf-8"
    )
    assert "docs-build: build-web" in content
    assert "$(PYTHON) tools/maintenance/make_tasks.py docs-build" in content
    assert "providence_wizard.orchestration.wizard.selector_compiler_cli" in make_tasks
    assert '"build/site/selector"' in make_tasks


def test_docs_serve_runs_selector_build() -> None:
    content = _makefile_content()
    # docs-serve depends on docs-build, which already includes the selector compiler step
    assert "docs-serve: docs-build" in content


def test_makefile_recipes_delegate_shell_sensitive_logic_to_python() -> None:
    content = _makefile_content()
    forbidden = [
        " grep ",
        " awk ",
        " trap ",
        "ln -s",
        "PYTHONPATH=",
        " && ",
    ]
    for token in forbidden:
        assert token not in content
