from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    path = Path("tools/architecture/validate_cycles.py")
    spec = importlib.util.spec_from_file_location("validate_cycles", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _mk_repo(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    return tmp_path


def _write_module(repo: Path, rel: str, content: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_no_cycle_detected(tmp_path: Path) -> None:
    validate_cycles = _load_module()
    repo = _mk_repo(tmp_path)
    _write_module(
        repo,
        "packages/core/providence_core/src/providence_core/a.py",
        "import providence_core.b\n",
    )
    _write_module(
        repo, "packages/core/providence_core/src/providence_core/b.py", "x = 1\n"
    )

    graph, _ = validate_cycles._build_graph(repo)
    sccs = validate_cycles._tarjan_scc(graph)
    cycles = [c for c in sccs if len(c) > 1]
    assert cycles == []


def test_simple_cycle_detected(tmp_path: Path) -> None:
    validate_cycles = _load_module()
    repo = _mk_repo(tmp_path)
    _write_module(
        repo,
        "packages/core/providence_core/src/providence_core/a.py",
        "import providence_core.b\n",
    )
    _write_module(
        repo,
        "packages/core/providence_core/src/providence_core/b.py",
        "import providence_core.a\n",
    )

    graph, _ = validate_cycles._build_graph(repo)
    sccs = validate_cycles._tarjan_scc(graph)
    cycles = [c for c in sccs if len(c) > 1]
    assert any(set(c) == {"providence_core.a", "providence_core.b"} for c in cycles)


def test_package_reimport_cycle_detected(tmp_path: Path) -> None:
    """Mirrors the real-world `from package import submodule` idiom that
    caused audit.py/tools.py/telemetry.py's cyclic imports to go undetected
    by this tool while still being flagged by CodeQL."""
    validate_cycles = _load_module()
    repo = _mk_repo(tmp_path)
    _write_module(
        repo,
        "packages/core/providence_core/src/providence_core/a.py",
        "import providence_core.b\n",
    )
    _write_module(
        repo,
        "packages/core/providence_core/src/providence_core/b.py",
        "from providence_core import a\n",
    )

    graph, _ = validate_cycles._build_graph(repo)
    sccs = validate_cycles._tarjan_scc(graph)
    cycles = [c for c in sccs if len(c) > 1]
    assert any(set(c) == {"providence_core.a", "providence_core.b"} for c in cycles)


def test_external_imports_are_ignored(tmp_path: Path) -> None:
    validate_cycles = _load_module()
    repo = _mk_repo(tmp_path)
    _write_module(
        repo,
        "packages/core/providence_core/src/providence_core/a.py",
        "import json\nfrom pathlib import Path\n",
    )
    graph, _ = validate_cycles._build_graph(repo)
    assert graph.get("providence_core.a") == set()
