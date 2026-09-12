"""Verify the built providence-core wheel bundles every native compiler binary.

Post-build release gate: staging assets into the package tree
(`stage_packaged_compiler_assets`) happens before `python -m build`, so a
packaging regression (hatchling include rules, path rename) could still ship a
wheel without the binaries. This check inspects the built wheel itself, which
is what standalone clients actually install.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

from tools.release.validate_release_assets import REQUIRED_COMPILER_ASSETS

WHEEL_NATIVE_PREFIX = "providence_core/_native/"


def verify_wheel_native_assets(dist_dir: str | Path = "dist") -> Path:
    """Return the verified providence-core wheel path, or raise SystemExit."""
    wheels = sorted(Path(dist_dir).glob("providence_core-*.whl"))
    if not wheels:
        raise SystemExit(f"no providence_core wheel found in {dist_dir}")
    if len(wheels) > 1:
        raise SystemExit(f"expected exactly one providence_core wheel, found: {wheels}")

    wheel = wheels[0]
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        missing = [
            asset
            for asset in REQUIRED_COMPILER_ASSETS
            if WHEEL_NATIVE_PREFIX + asset not in names
        ]
        if missing:
            raise SystemExit(
                f"{wheel.name} is missing bundled compiler binaries: "
                + ", ".join(missing)
            )
        empty = [
            asset
            for asset in REQUIRED_COMPILER_ASSETS
            if archive.getinfo(WHEEL_NATIVE_PREFIX + asset).file_size == 0
        ]
        if empty:
            raise SystemExit(
                f"{wheel.name} contains empty compiler binaries: " + ", ".join(empty)
            )
    return wheel


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    wheel = verify_wheel_native_assets(args[0] if args else "dist")
    print(
        f"OK: {wheel.name} bundles all {len(REQUIRED_COMPILER_ASSETS)} native compiler binaries"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
