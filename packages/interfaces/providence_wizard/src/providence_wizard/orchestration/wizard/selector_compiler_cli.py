"""CLI entry point for building the machine-readable Selector artifact."""

from __future__ import annotations

import argparse
from pathlib import Path

from .selector_compiler import SelectorCompiler


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Selector data artifact.")
    parser.add_argument("--repo-root", default=".", help="Workspace root.")
    parser.add_argument("--output-dir", required=True, help="Selector output dir.")
    return parser.parse_args()


def main() -> None:
    """CLI entry point for building the Selector data artifact."""
    args = _parse_args()
    compiler = SelectorCompiler(repo_root=Path(args.repo_root).resolve())
    compiler.build_artifact(Path(args.output_dir).resolve())


if __name__ == "__main__":
    main()
