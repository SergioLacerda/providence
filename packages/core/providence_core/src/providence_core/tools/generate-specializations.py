#!/usr/bin/env python3
"""Generate project-specific SPECIALIZATIONS from CANONICAL rules."""

from __future__ import annotations

import argparse
import io
import sys

if sys.platform == "win32":
    # Windows consoles default to the legacy codepage (e.g. cp1252), which
    # can't encode the emoji used in status output below.
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    if isinstance(sys.stderr, io.TextIOWrapper):
        sys.stderr.reconfigure(encoding="utf-8")

from _generate_specializations_support import (
    load_config,
    validate_config,
    write_specialization_files,
)


def main() -> int:
    """Generate specialization files for the requested project."""
    parser = argparse.ArgumentParser(
        description="Generate project-specific SPECIALIZATIONS from CANONICAL rules"
    )
    parser.add_argument("--project", required=True, help="Project name")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()
    config = load_config(args.project)
    if config is None:
        sys.exit(1)
    if not validate_config(config):
        sys.exit(3)
    if not write_specialization_files(args.project, config, args.force):
        sys.exit(1)
    sys.stdout.write(f"✅ SPECIALIZATIONS generated for {args.project}\n")
    sys.stdout.write(
        f"📝 Files created in: docs/ia/custom/{args.project}/SPECIALIZATIONS/\n"
    )
    sys.stdout.write("📋 Next step: Commit and push for CI/CD validation\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
