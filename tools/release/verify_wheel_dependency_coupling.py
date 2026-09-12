"""Verify internal dependencies of every built wheel resolve within dist/.

Release gate: the workspace packages depend on each other by name
(`providence-core`, `providence-wizard`, ...). Inside the uv workspace or the `--no-index`
wheelhouse this is safe, but nothing structurally guaranteed that a release's
dist/ set is complete and version-aligned. This check reads each wheel's
METADATA `Requires-Dist` entries and requires that every internal dependency
is satisfied by a wheel of the SAME version present in the same dist/ set —
an exact-coupling gate without hardcoding versions in source.
"""

from __future__ import annotations

import re
import sys
import zipfile
from email.parser import Parser
from pathlib import Path

_INTERNAL_PREFIX = "providence-"
_REQUIRES_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*")


def _canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _wheel_name_version(wheel: Path) -> tuple[str, str]:
    name, version = wheel.name.split("-")[:2]
    return _canonical(name), version


def _requires_dist(wheel: Path) -> list[str]:
    with zipfile.ZipFile(wheel) as archive:
        metadata_name = next(
            member
            for member in archive.namelist()
            if member.endswith(".dist-info/METADATA")
        )
        metadata = Parser().parsestr(archive.read(metadata_name).decode("utf-8"))
    return metadata.get_all("Requires-Dist") or []


def verify_wheel_dependency_coupling(dist_dir: str | Path = "dist") -> None:
    wheels = sorted(Path(dist_dir).glob("providence_*.whl"))
    if not wheels:
        raise SystemExit(f"no providence_* wheels found in {dist_dir}")

    built = {
        _wheel_name_version(wheel)[0]: _wheel_name_version(wheel)[1] for wheel in wheels
    }
    problems: list[str] = []
    for wheel in wheels:
        name, version = _wheel_name_version(wheel)
        for requirement in _requires_dist(wheel):
            match = _REQUIRES_NAME_RE.match(requirement.strip())
            if not match:
                continue
            dep = _canonical(match.group(0))
            if not dep.startswith(_INTERNAL_PREFIX):
                continue
            if dep not in built:
                problems.append(
                    f"{wheel.name}: internal dependency '{dep}' has no wheel in dist/"
                )
            elif built[dep] != version:
                problems.append(
                    f"{wheel.name}: internal dependency '{dep}' is version "
                    f"{built[dep]}, expected {version} (same-release coupling)"
                )
    if problems:
        raise SystemExit(
            "wheel dependency coupling check failed:\n  " + "\n  ".join(problems)
        )


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    dist_dir = args[0] if args else "dist"
    verify_wheel_dependency_coupling(dist_dir)
    print(f"OK: all internal wheel dependencies in {dist_dir} are version-coupled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
