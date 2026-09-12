#!/usr/bin/env python3
"""Validate that a release `dist/` directory has the required standalone
compiler assets and a correctly-shaped `SHA256SUMS` manifest.

Used by the release workflow's pre-publication staging gate and by unit
tests to keep the required asset matrix and checksum shape in one place.
"""

from __future__ import annotations

import sys
from pathlib import Path

REQUIRED_COMPILER_ASSETS = (
    "sdd-compile-linux-amd64",
    "sdd-compile-linux-arm64",
    "sdd-compile-darwin-amd64",
    "sdd-compile-darwin-arm64",
    "sdd-compile-windows-amd64.exe",
)
# PyInstaller cannot cross-compile the way `go build` can, so unlike
# REQUIRED_COMPILER_ASSETS above this is 3 targets, not 5 — no darwin-amd64,
# since GitHub-hosted macos-latest runners are Apple Silicon (arm64) only.
# See .analysis/refined/20260807-cli-binary-installer-followup/proposal.md.
REQUIRED_CLI_ASSETS = (
    "providence-linux-amd64",
    "providence-darwin-arm64",
    "providence-windows-amd64.exe",
)
SUMS_FILE = "SHA256SUMS"
REQUIRED_ASSETS = REQUIRED_COMPILER_ASSETS + REQUIRED_CLI_ASSETS + (SUMS_FILE,)


class ReleaseAssetValidationError(ValueError):
    """Raised when a `dist/` directory does not satisfy the release asset contract."""


def validate_release_assets(dist_dir: str | Path) -> None:
    """Raise `ReleaseAssetValidationError` if `dist_dir` fails the asset contract.

    Checks:
    - every required compiler binary and `SHA256SUMS` exist and are non-empty.
    - `SHA256SUMS` lists every compiler asset by exact, bare filename
      (no `dist/` prefix, no path separators).
    """
    dist = Path(dist_dir)

    for asset in REQUIRED_ASSETS:
        path = dist / asset
        if not path.exists() or path.stat().st_size == 0:
            raise ReleaseAssetValidationError(
                f"missing or empty release asset: {asset}"
            )

    sums_text = (dist / SUMS_FILE).read_text(encoding="utf-8")
    listed_names: dict[str, str] = {}
    for line in sums_text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 2:
            raise ReleaseAssetValidationError(
                f"malformed {SUMS_FILE} line (expected '<sha256>  <name>'): {line!r}"
            )
        digest, name = parts
        listed_names[name] = digest

    for name in listed_names:
        if "/" in name or "\\" in name:
            raise ReleaseAssetValidationError(
                f"{SUMS_FILE} entry must use a bare filename, not a path: {name!r}"
            )

    for asset in REQUIRED_COMPILER_ASSETS + REQUIRED_CLI_ASSETS:
        if asset not in listed_names:
            raise ReleaseAssetValidationError(
                f"{SUMS_FILE} does not list required asset by its bare name: {asset}"
            )


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    dist_dir = args[0] if args else "dist"
    try:
        validate_release_assets(dist_dir)
    except ReleaseAssetValidationError as exc:
        print(f"FAIL: RELEASE_ASSET_VALIDATION_ERROR: {exc}")
        return 1
    print(f"PASS: release assets in {dist_dir!r} satisfy the asset contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
