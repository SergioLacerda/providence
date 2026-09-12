"""CLI entry point for building selector site assets."""

from __future__ import annotations

import argparse
from pathlib import Path

from .selector_compiler import SelectorCompiler


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build selector site assets.")
    parser.add_argument("--repo-root", default=".", help="Workspace root.")
    parser.add_argument("--output-dir", required=True, help="Selector output dir.")
    return parser.parse_args()


def main() -> None:
    """CLI entry point for building selector assets."""
    args = _parse_args()
    compiler = SelectorCompiler(repo_root=Path(args.repo_root).resolve())
    compiler.build_site(Path(args.output_dir).resolve())


if __name__ == "__main__":
    main()
