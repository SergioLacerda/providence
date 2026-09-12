"""Stage native sdd-compile binaries into the providence-core wheel package data."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from tools.release.validate_release_assets import REQUIRED_COMPILER_ASSETS

PACKAGE_NATIVE_DIR = Path("packages/core/providence_core/src/providence_core/_native")


def stage_packaged_compiler_assets(dist_dir: str | Path = "dist") -> None:
    """Copy release compiler assets into the package data staging directory."""
    source_dir = Path(dist_dir)
    missing = [
        asset
        for asset in REQUIRED_COMPILER_ASSETS
        if not (source_dir / asset).is_file()
        or (source_dir / asset).stat().st_size == 0
    ]
    if missing:
        joined = ", ".join(missing)
        raise SystemExit(f"missing compiler assets for wheel packaging: {joined}")

    if PACKAGE_NATIVE_DIR.exists():
        shutil.rmtree(PACKAGE_NATIVE_DIR)
    PACKAGE_NATIVE_DIR.mkdir(parents=True, exist_ok=True)

    for asset in REQUIRED_COMPILER_ASSETS:
        shutil.copy2(source_dir / asset, PACKAGE_NATIVE_DIR / asset)


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    stage_packaged_compiler_assets(args[0] if args else "dist")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
