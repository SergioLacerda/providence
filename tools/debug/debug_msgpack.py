#!/usr/bin/env python3
"""
Debug helper — inspect compiled governance msgpack artifacts.

Usage:
    python tools/debug/debug_msgpack.py
    python tools/debug/debug_msgpack.py --spec-dir path/to/spec --out-dir /tmp/compiled
    python tools/debug/debug_msgpack.py --compiled-only  # skip build, read existing
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in [here.parent, *here.parents]:
        if (candidate / "pyproject.toml").is_file() and (
            candidate / "packages"
        ).is_dir():
            return candidate
    raise RuntimeError(f"Could not locate repo root from {__file__}.")


def _bootstrap_imports(repo_root: Path) -> None:
    """Add package src dirs to sys.path so we can import without installing."""
    for pkg in ("providence_integration", "providence_core"):
        for layer in ("core", "features", "interfaces"):
            src = repo_root / "packages" / layer / pkg / "src"
            if src.is_dir() and str(src) not in sys.path:
                sys.path.insert(0, str(src))


def _build_artifacts(spec_dir: Path, out_dir: Path) -> tuple[int, Path]:
    """Build pipeline and compile governance artifacts. Returns (exit_code, artifact_path)."""
    if not spec_dir.exists():
        print(f"ERROR: Spec directory not found: {spec_dir}")
        print("Use --spec-dir to specify the correct path.")
        return 1, Path()

    print(f"Building pipeline from: {spec_dir}")
    print(f"Output directory:       {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        from providence_integration.builders.governance.pipeline_builder import (
            PipelineBuilder,
        )

        PipelineBuilder(str(spec_dir)).save_outputs(str(out_dir))
        print("Pipeline built.")
    except ImportError as e:
        print(f"ERROR: Could not import PipelineBuilder: {e}")
        print("Ensure providence_integration is installed or run from the repo root.")
        return 1, Path()
    except Exception as e:
        print(f"ERROR: Pipeline build failed: {e}")
        return 1, Path()

    print("Compiling governance artifacts...")
    try:
        from providence_core.utils.compiler_runner import CompilerRunner

        result: Any = CompilerRunner().compile(out_dir, out_dir)
    except ImportError as e:
        print(f"ERROR: Could not import CompilerRunner: {e}")
        return 1, Path()
    except Exception as e:
        print(f"ERROR: Compilation failed: {e}")
        return 1, Path()

    return 0, Path(result.get("core_msgpack_file", ""))


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Inspect Providence compiled governance msgpack artifacts"
    )
    parser.add_argument(
        "--spec-dir",
        type=Path,
        default=None,
        help="Spec source directory (default: docs/spec/canonical)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Compiled output directory (default: <tmp>/providence-debug-compiled-<uid>)",
    )
    parser.add_argument(
        "--compiled-only",
        action="store_true",
        help="Skip build; read existing artifacts from --out-dir",
    )
    args = parser.parse_args()

    repo_root = _find_repo_root()
    _bootstrap_imports(repo_root)

    spec_dir = args.spec_dir or (repo_root / "docs" / "spec" / "canonical")
    out_dir = (
        args.out_dir
        or Path(tempfile.gettempdir()) / f"providence-debug-compiled-{os.getuid()}"
    )

    if args.compiled_only:
        candidates = list(out_dir.rglob("*.msgpack"))
        if not candidates:
            print(f"ERROR: No .msgpack files found in {out_dir}")
            return 1
        core_msgpack_path = max(candidates, key=lambda p: p.stat().st_mtime)
        print(f"Reading existing artifact: {core_msgpack_path}")
    else:
        code, core_msgpack_path = _build_artifacts(spec_dir, out_dir)
        if code != 0:
            return code

    if not core_msgpack_path.exists():
        print(f"ERROR: Artifact not found: {core_msgpack_path}")
        return 1

    try:
        import msgpack
    except ImportError:
        print("ERROR: msgpack not installed. Run: pip install msgpack")
        return 1

    print(f"\nArtifact: {core_msgpack_path}")
    print(f"Size:     {core_msgpack_path.stat().st_size:,} bytes")

    data: Any = msgpack.unpackb(core_msgpack_path.read_bytes(), raw=False)

    if isinstance(data, dict):
        print(f"Keys:     {list(data.keys())}")
        print(f"Category: {data.get('category', 'N/A')}")
        print(f"Items:    {len(data.get('items', []))}")
        print(f"Fingerprint: {data.get('fingerprint', 'N/A')}")
    print(f"\nFull contents:\n{json.dumps(data, indent=2, default=str)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
