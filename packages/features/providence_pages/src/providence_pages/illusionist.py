"""Verified ILUSIONISTA presentation-surface acquisition and composition."""

from __future__ import annotations

import hashlib
import io
import os
import re
import shutil
import tarfile
import tempfile
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

Download = Callable[[str], bytes]
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_TAG = re.compile(r"^providence(?:-selector)?-v\d+\.\d+\.\d+$")
_DEFAULTS = {
    "landing": (
        "providence-v0.1.0",
        "illusionist-providence-surface-v0.1.0.tar.gz",
        "699552ac2928195c5175e88a6bcfa4ce9b6b4a263d2ceac223ecd06db324d7e6",
    ),
    "selector": (
        "providence-selector-v0.1.0",
        "illusionist-providence-selector-surface-v0.1.0.tar.gz",
        "2393483af3a73dbc6693ac1e21b60282ae777cc27d20a4512796ef3cceea320c",
    ),
}


class SurfaceError(RuntimeError):
    """Raised when a presentation surface cannot be trusted or composed."""


@dataclass(frozen=True)
class SurfaceRelease:
    """Immutable coordinates and structural contract for one surface."""

    surface: str
    repository: str
    tag: str
    asset: str
    sha256: str

    @classmethod
    def from_environment(
        cls, surface: str, environ: Mapping[str, str] | None = None
    ) -> SurfaceRelease:
        """Resolve one pinned surface contract from environment overrides."""
        if surface not in _DEFAULTS:
            raise SurfaceError(f"unknown ILUSIONISTA surface: {surface}")
        env = os.environ if environ is None else environ
        tag, asset, digest = _DEFAULTS[surface]
        prefix = "ILLUSIONIST_PROVIDENCE" + (
            "_SELECTOR" if surface == "selector" else "_LANDING"
        )
        return cls(
            surface,
            env.get("ILLUSIONIST_REPOSITORY", "SergioLacerda/illusionist-web"),
            env.get(f"{prefix}_VERSION", tag),
            env.get(f"{prefix}_ASSET", asset),
            env.get(f"{prefix}_SHA256", digest),
        )

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[^/\s]+/[^/\s]+", self.repository):
            raise SurfaceError(f"invalid ILUSIONISTA repository: {self.repository!r}")
        if not _TAG.fullmatch(self.tag) or self.tag.lower() in {"main", "latest"}:
            raise SurfaceError(f"mutable or invalid ILUSIONISTA tag: {self.tag!r}")
        expected_prefix = f"illusionist-providence{'-selector' if self.surface == 'selector' else ''}-surface-"
        version = self.tag.rsplit("-v", 1)[1]
        if not self.asset.startswith(expected_prefix) or not self.asset.endswith(
            f"-v{version}.tar.gz"
        ):
            raise SurfaceError(f"invalid ILUSIONISTA archive: {self.asset!r}")
        if Path(self.asset).name != self.asset or not _SHA256.fullmatch(self.sha256):
            raise SurfaceError("ILUSIONISTA archive name or SHA-256 is invalid")

    @property
    def base_url(self) -> str:
        """Return the versioned GitHub Releases base URL."""
        return f"https://github.com/{self.repository}/releases/download/{self.tag}"

    @property
    def archive_url(self) -> str:
        """Return the exact archive URL."""
        return f"{self.base_url}/{self.asset}"

    @property
    def checksum_url(self) -> str:
        """Return the exact sidecar checksum URL."""
        return f"{self.archive_url}.sha256"


@dataclass(frozen=True)
class PreparedSurface:
    """A verified surface extracted into an isolated staging directory."""

    release: SurfaceRelease
    root: Path


def illusionist_enabled(environ: Mapping[str, str] | None = None) -> bool:
    """Return whether Phase A is active; false is the explicit rollback path."""
    env = os.environ if environ is None else environ
    return env.get("PROVIDENCE_USE_ILLUSIONIST_SURFACES", "1").lower() not in {
        "0",
        "false",
        "no",
    }


def _download(url: str) -> bytes:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise SurfaceError(f"ILUSIONISTA asset URL must use HTTPS: {url!r}")
    request = urllib.request.Request(url, headers={"User-Agent": "providence-pages"})
    try:
        # The scheme and authority are validated immediately above; file/custom
        # URL handlers cannot reach urlopen here.
        with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310
            payload = response.read()
            if not isinstance(payload, bytes):
                raise SurfaceError("ILUSIONISTA asset response was not bytes")
            return payload
    except Exception as exc:
        raise SurfaceError(f"failed to download ILUSIONISTA asset: {url}") from exc


class IllusionistSurfaceComposer:
    """Stage, verify, and overlay both immutable surfaces without deleting files."""

    def __init__(
        self,
        repository: str,
        downloader: Download | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        self.repository = repository
        self.downloader = downloader or _download
        self.environ = os.environ if environ is None else environ

    @classmethod
    def from_environment(
        cls, environ: Mapping[str, str] | None = None
    ) -> IllusionistSurfaceComposer:
        """Create a composer using the configured repository and pins."""
        env = os.environ if environ is None else environ
        return cls(
            env.get("ILLUSIONIST_REPOSITORY", "SergioLacerda/illusionist-web"),
            environ=env,
        )

    @contextmanager
    def staged(
        self, build_dir: Path
    ) -> Iterator[tuple[PreparedSurface, PreparedSurface]]:
        """Download and verify both surfaces before yielding staging paths."""
        build_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".illusionist-", dir=build_dir) as raw:
            root = Path(raw)
            prepared = tuple(
                self._stage(
                    SurfaceRelease.from_environment(surface, self.environ), root
                )
                for surface in ("landing", "selector")
            )
            yield prepared  # type: ignore[misc]

    def _stage(self, release: SurfaceRelease, staging: Path) -> PreparedSurface:
        archive = self._fetch(release.archive_url)
        actual = hashlib.sha256(archive).hexdigest()
        if actual != release.sha256:
            raise SurfaceError(
                f"{release.surface} SHA-256 mismatch: expected {release.sha256}, got {actual}"
            )
        manifest = (
            self._fetch(release.checksum_url).decode("utf-8", errors="strict").split()
        )
        if (
            len(manifest) < 2
            or manifest[0] != actual
            or Path(manifest[1].lstrip("*")).name != release.asset
        ):
            raise SurfaceError(
                f"{release.surface} checksum manifest does not match {release.asset}"
            )
        destination = staging / release.surface
        self._extract(archive, release, destination)
        return PreparedSurface(release, destination)

    def _fetch(self, url: str) -> bytes:
        try:
            return self.downloader(url)
        except SurfaceError:
            raise
        except Exception as exc:
            raise SurfaceError(f"failed to acquire ILUSIONISTA asset: {url}") from exc

    def _extract(
        self, archive: bytes, release: SurfaceRelease, destination: Path
    ) -> None:
        seen: set[str] = set()
        files: set[str] = set()
        destination.mkdir(parents=True)
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
            for member in bundle.getmembers():
                raw = member.name.replace("\\", "/")
                parts = PurePosixPath(raw).parts
                rel = "/".join(parts)
                if (
                    not parts
                    or raw.startswith("/")
                    or any(part in {"", ".", ".."} for part in parts)
                ):
                    raise SurfaceError(
                        f"{release.surface} archive contains unsafe path: {raw!r}"
                    )
                if rel in seen or any(
                    parent in files
                    for parent in ("/".join(parts[:i]) for i in range(1, len(parts)))
                ):
                    raise SurfaceError(
                        f"{release.surface} archive contains a path collision: {rel}"
                    )
                if (
                    member.issym()
                    or member.islnk()
                    or not (member.isdir() or member.isfile())
                ):
                    raise SurfaceError(
                        f"{release.surface} archive contains an unsupported entry: {raw!r}"
                    )
                top = parts[0]
                if (release.surface == "landing" and top in {"docs", "selector"}) or (
                    release.surface == "selector"
                    and (
                        rel in {"data.json", "docs.index.json"}
                        or top in {"fixtures", "compat", ".providence", "node_modules"}
                    )
                ):
                    raise SurfaceError(
                        f"{release.surface} archive contains forbidden path: {rel}"
                    )
                target = destination.joinpath(*parts)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    source = bundle.extractfile(member)
                    if source is None:
                        raise SurfaceError(f"cannot read archive entry: {rel}")
                    target.write_bytes(source.read())
                    files.add(rel)
                seen.add(rel)
        required = (
            {"index.html"}
            if release.surface == "selector"
            else {"index.html", "detalhe-tecnico/index.html", "instalacao/index.html"}
        )
        if not required.issubset(files):
            raise SurfaceError(
                f"{release.surface} archive is missing required files: {sorted(required - files)}"
            )

    def compose(self, site_dir: Path, prepared: Sequence[PreparedSurface]) -> None:
        """Overlay verified presentation files without deleting rollback files."""
        for surface in prepared:
            target_root = site_dir / (
                "selector" if surface.release.surface == "selector" else ""
            )
            for source in sorted(surface.root.rglob("*")):
                if not source.is_file():
                    continue
                relative = source.relative_to(surface.root)
                target = target_root / relative
                current = target_root
                for part in relative.parts:
                    current /= part
                    if current.is_symlink():
                        raise SurfaceError(
                            f"refusing to write through symlink: {current}"
                        )
                if target.exists() and target.is_dir():
                    raise SurfaceError(f"surface destination is a directory: {target}")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
