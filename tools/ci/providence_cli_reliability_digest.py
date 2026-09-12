#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def _parse_counts(log_text: str) -> tuple[int, int]:
    skipped = 0
    warnings = 0

    skipped_match = re.search(r"(\d+)\s+skipped", log_text)
    if skipped_match:
        skipped = int(skipped_match.group(1))

    warnings_match = re.search(r"(\d+)\s+warning(?:s)?", log_text)
    if warnings_match:
        warnings = int(warnings_match.group(1))

    return skipped, warnings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build reliability digest from providence_cli pytest output."
    )
    parser.add_argument(
        "--log", required=True, help="Path to pytest stdout/stderr log."
    )
    parser.add_argument(
        "--json-out",
        required=True,
        help="Path to write machine-readable digest JSON.",
    )
    parser.add_argument(
        "--md-out",
        required=True,
        help="Path to write markdown summary digest.",
    )
    parser.add_argument(
        "--max-warnings",
        type=int,
        default=-1,
        help="Optional threshold; fail when warnings exceed this value.",
    )
    args = parser.parse_args()

    log_path = Path(args.log)
    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    skipped, warnings = _parse_counts(log_text)

    status = "ok"
    if args.max_warnings >= 0 and warnings > args.max_warnings:
        status = "warning_threshold_exceeded"

    digest = {
        "status": status,
        "source": str(log_path),
        "skipped": skipped,
        "warnings": warnings,
        "max_warnings": args.max_warnings,
    }

    json_path = Path(args.json_out)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(digest, indent=2) + "\n", encoding="utf-8")

    md_path = Path(args.md_out)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(
        "\n".join(
            [
                "# providence_cli reliability digest",
                "",
                f"- status: `{status}`",
                f"- skipped: `{skipped}`",
                f"- warnings: `{warnings}`",
                f"- max_warnings: `{args.max_warnings}`",
                f"- source: `{log_path}`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    if status != "ok":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
