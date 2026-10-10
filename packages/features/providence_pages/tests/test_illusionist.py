from __future__ import annotations

import hashlib
import io
import tarfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from providence_pages.illusionist import (
    IllusionistSurfaceComposer,
    PreparedSurface,
    SurfaceError,
    SurfaceRelease,
    _download,
    illusionist_enabled,
)

pytestmark = pytest.mark.unit


def _archive(entries: list[tuple[str, bytes]]) -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as bundle:
        for name, content in entries:
            info = tarfile.TarInfo(name)
            info.size = len(content)
            bundle.addfile(info, io.BytesIO(content))
    return output.getvalue()


def _surface_archive(
    surface: str, *, extra: list[tuple[str, bytes]] | None = None
) -> bytes:
    if surface == "landing":
        entries = [
            ("index.html", b"new landing"),
            ("detalhe-tecnico/index.html", b"technical"),
            ("instalacao/index.html", b"install"),
            ("_astro/app.js", b"landing js"),
        ]
    else:
        entries = [
            ("index.html", b"new selector"),
            ("site-header.js", b"header js"),
            ("site-header.css", b"header css"),
            ("_astro/app.js", b"selector js"),
        ]
    return _archive(entries + (extra or []))


def _configured_composer(
    landing: bytes,
    selector: bytes,
    *,
    landing_extra: list[tuple[str, bytes]] | None = None,
) -> IllusionistSurfaceComposer:
    landing = landing if landing else _surface_archive("landing", extra=landing_extra)
    selector = selector if selector else _surface_archive("selector")
    landing_tag = "providence-v1.2.3"
    selector_tag = "providence-selector-v1.2.3"
    landing_asset = "illusionist-providence-surface-v1.2.3.tar.gz"
    selector_asset = "illusionist-providence-selector-surface-v1.2.3.tar.gz"
    landing_sha = hashlib.sha256(landing).hexdigest()
    selector_sha = hashlib.sha256(selector).hexdigest()
    environment = {
        "ILLUSIONIST_REPOSITORY": "Example/illusionist-web",
        "ILLUSIONIST_PROVIDENCE_LANDING_VERSION": landing_tag,
        "ILLUSIONIST_PROVIDENCE_LANDING_ASSET": landing_asset,
        "ILLUSIONIST_PROVIDENCE_LANDING_SHA256": landing_sha,
        "ILLUSIONIST_PROVIDENCE_SELECTOR_VERSION": selector_tag,
        "ILLUSIONIST_PROVIDENCE_SELECTOR_ASSET": selector_asset,
        "ILLUSIONIST_PROVIDENCE_SELECTOR_SHA256": selector_sha,
    }
    releases = (
        SurfaceRelease(
            "landing",
            environment["ILLUSIONIST_REPOSITORY"],
            landing_tag,
            landing_asset,
            landing_sha,
        ),
        SurfaceRelease(
            "selector",
            environment["ILLUSIONIST_REPOSITORY"],
            selector_tag,
            selector_asset,
            selector_sha,
        ),
    )
    payloads = {}
    for release, archive in zip(releases, (landing, selector), strict=True):
        payloads[release.archive_url] = archive
        payloads[release.checksum_url] = f"{release.sha256}  {release.asset}\n".encode()

    def download(url: str) -> bytes:
        return payloads[url]

    return IllusionistSurfaceComposer(
        environment["ILLUSIONIST_REPOSITORY"], download, environment
    )


def test_default_release_coordinates_are_pinned() -> None:
    landing = SurfaceRelease.from_environment("landing", {})
    selector = SurfaceRelease.from_environment("selector", {})
    assert landing.tag == "providence-v0.1.0"
    assert (
        landing.sha256
        == "699552ac2928195c5175e88a6bcfa4ce9b6b4a263d2ceac223ecd06db324d7e6"
    )
    assert selector.tag == "providence-selector-v0.1.0"
    assert (
        selector.sha256
        == "2393483af3a73dbc6693ac1e21b60282ae777cc27d20a4512796ef3cceea320c"
    )


def test_unknown_surface_is_rejected() -> None:
    with pytest.raises(SurfaceError, match="unknown ILUSIONISTA surface"):
        SurfaceRelease.from_environment("unknown", {})


def test_invalid_repository_is_rejected() -> None:
    with pytest.raises(SurfaceError, match="invalid ILUSIONISTA repository"):
        SurfaceRelease.from_environment(
            "landing", {"ILLUSIONIST_REPOSITORY": "not-a-repository"}
        )


def test_from_environment_uses_configured_repository() -> None:
    composer = IllusionistSurfaceComposer.from_environment(
        {"ILLUSIONIST_REPOSITORY": "Example/illusionist-web"}
    )
    assert composer.repository == "Example/illusionist-web"


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("ILLUSIONIST_PROVIDENCE_LANDING_VERSION", "latest"),
        ("ILLUSIONIST_PROVIDENCE_SELECTOR_VERSION", "main"),
        ("ILLUSIONIST_PROVIDENCE_LANDING_SHA256", "not-a-digest"),
    ],
)
def test_release_configuration_rejects_mutable_or_invalid_values(
    key: str, value: str
) -> None:
    with pytest.raises(SurfaceError):
        SurfaceRelease.from_environment(
            "selector" if "SELECTOR" in key else "landing", {key: value}
        )


def test_release_configuration_requires_matching_asset_version() -> None:
    with pytest.raises(SurfaceError, match="invalid ILUSIONISTA archive"):
        SurfaceRelease.from_environment(
            "landing",
            {"ILLUSIONIST_PROVIDENCE_LANDING_VERSION": "providence-v1.2.3"},
        )


def test_rollback_is_explicit() -> None:
    assert illusionist_enabled({}) is True
    assert illusionist_enabled({"PROVIDENCE_USE_ILLUSIONIST_SURFACES": "0"}) is False
    assert (
        illusionist_enabled({"PROVIDENCE_USE_ILLUSIONIST_SURFACES": "false"}) is False
    )


@pytest.mark.parametrize("url", ["file:///tmp/archive.tar.gz", "custom://asset"])
def test_download_rejects_non_https_schemes(url: str) -> None:
    with pytest.raises(SurfaceError, match="must use HTTPS"):
        _download(url)


def test_download_returns_bytes_from_https_response() -> None:
    response = MagicMock()
    response.__enter__.return_value = response
    response.read.return_value = b"archive"
    with patch(
        "providence_pages.illusionist.urllib.request.urlopen",
        return_value=response,
    ) as urlopen:
        assert _download("https://example.test/archive.tar.gz") == b"archive"
    urlopen.assert_called_once()


def test_download_rejects_non_bytes_response() -> None:
    response = MagicMock()
    response.__enter__.return_value = response
    response.read.return_value = "not bytes"
    with (
        patch(
            "providence_pages.illusionist.urllib.request.urlopen",
            return_value=response,
        ),
        pytest.raises(SurfaceError, match="failed to download"),
    ):
        _download("https://example.test/archive.tar.gz")


def test_stage_and_compose_preserves_governed_selector_files(tmp_path: Path) -> None:
    composer = _configured_composer(b"", b"")
    site = tmp_path / "build" / "site"
    selector = site / "selector"
    selector.mkdir(parents=True)
    (selector / "data.json").write_text('{"version":"1.0"}', encoding="utf-8")
    (selector / "docs.index.json").write_text('{"documents":[]}', encoding="utf-8")

    with composer.staged(tmp_path / "build") as prepared:
        composer.compose(site, prepared)

    assert (site / "index.html").read_bytes() == b"new landing"
    assert (selector / "index.html").read_bytes() == b"new selector"
    assert (selector / "data.json").read_text(encoding="utf-8") == '{"version":"1.0"}'
    assert (selector / "docs.index.json").read_text(
        encoding="utf-8"
    ) == '{"documents":[]}'


def test_selector_artifact_composes_without_landing_surface(tmp_path: Path) -> None:
    source = tmp_path / "selector-artifact"
    source.mkdir()
    (source / "index.html").write_bytes(b"selector artifact")
    (source / "site-header.js").write_bytes(b"selector header")
    release = SurfaceRelease.from_environment(
        "selector",
        {
            "ILLUSIONIST_REPOSITORY": "Example/illusionist-web",
            "ILLUSIONIST_PROVIDENCE_SELECTOR_VERSION": "providence-selector-v1.2.3",
            "ILLUSIONIST_PROVIDENCE_SELECTOR_ASSET": (
                "illusionist-providence-selector-surface-v1.2.3.tar.gz"
            ),
            "ILLUSIONIST_PROVIDENCE_SELECTOR_SHA256": "a" * 64,
        },
    )
    site = tmp_path / "site"
    selector = site / "selector"
    selector.mkdir(parents=True)
    (selector / "data.json").write_text('{"items":[]}', encoding="utf-8")
    (selector / "docs.index.json").write_text('{"documents":[]}', encoding="utf-8")

    IllusionistSurfaceComposer.from_environment({}).compose(
        site, (PreparedSurface(release, source),)
    )

    assert (selector / "index.html").read_bytes() == b"selector artifact"
    assert (selector / "site-header.js").read_bytes() == b"selector header"
    assert (selector / "data.json").read_text(encoding="utf-8") == '{"items":[]}'
    assert (selector / "docs.index.json").read_text(
        encoding="utf-8"
    ) == '{"documents":[]}'
    assert not (site / "index.html").exists()


def test_stage_rejects_archive_checksum_mismatch(tmp_path: Path) -> None:
    composer = _configured_composer(b"", b"")
    original = composer.downloader

    def tamper(url: str) -> bytes:
        payload = original(url)
        if url.endswith("illusionist-providence-surface-v1.2.3.tar.gz"):
            return payload + b"tampered"
        return payload

    composer.downloader = tamper
    with (
        pytest.raises(SurfaceError, match="SHA-256 mismatch"),
        composer.staged(tmp_path / "build"),
    ):
        pass


def test_stage_rejects_unavailable_asset(tmp_path: Path) -> None:
    composer = _configured_composer(b"", b"")

    def unavailable(_url: str) -> bytes:
        raise OSError("network unavailable")

    composer.downloader = unavailable
    with (
        pytest.raises(SurfaceError, match="failed to acquire"),
        composer.staged(tmp_path / "build"),
    ):
        pass


def test_stage_preserves_surface_error_from_downloader(tmp_path: Path) -> None:
    composer = _configured_composer(b"", b"")

    def unavailable(_url: str) -> bytes:
        raise SurfaceError("already classified")

    composer.downloader = unavailable
    with (
        pytest.raises(SurfaceError, match="already classified"),
        composer.staged(tmp_path / "build"),
    ):
        pass


def test_stage_rejects_checksum_manifest_mismatch(tmp_path: Path) -> None:
    composer = _configured_composer(b"", b"")
    original = composer.downloader

    def bad_manifest(url: str) -> bytes:
        if url.endswith(".sha256"):
            return b"0" * 64 + b"  wrong.tar.gz\n"
        return original(url)

    composer.downloader = bad_manifest
    with (
        pytest.raises(SurfaceError, match="checksum manifest"),
        composer.staged(tmp_path / "build"),
    ):
        pass


def test_stage_rejects_missing_required_entrypoint(tmp_path: Path) -> None:
    incomplete = _archive([("index.html", b"landing")])
    composer = _configured_composer(incomplete, b"")
    with (
        pytest.raises(SurfaceError, match="missing required files"),
        composer.staged(tmp_path / "build"),
    ):
        pass


def test_stage_accepts_directory_entries(tmp_path: Path) -> None:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as bundle:
        directory = tarfile.TarInfo("assets")
        directory.type = tarfile.DIRTYPE
        bundle.addfile(directory)
        for name, content in [
            ("index.html", b"landing"),
            ("detalhe-tecnico/index.html", b"technical"),
            ("instalacao/index.html", b"install"),
            ("assets/app.js", b"app"),
        ]:
            info = tarfile.TarInfo(name)
            info.size = len(content)
            bundle.addfile(info, io.BytesIO(content))

    composer = _configured_composer(output.getvalue(), b"")
    with composer.staged(tmp_path / "build") as prepared:
        assert (prepared[0].root / "assets" / "app.js").read_bytes() == b"app"


def test_stage_rejects_unsupported_archive_entry(tmp_path: Path) -> None:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as bundle:
        link = tarfile.TarInfo("link")
        link.type = tarfile.SYMTYPE
        link.linkname = "target"
        bundle.addfile(link)

    composer = _configured_composer(output.getvalue(), b"")
    with (
        pytest.raises(SurfaceError, match="unsupported entry"),
        composer.staged(tmp_path / "build"),
    ):
        pass


def test_stage_rejects_unreadable_archive_entry(tmp_path: Path) -> None:
    composer = _configured_composer(b"", b"")
    with (
        patch("tarfile.TarFile.extractfile", return_value=None),
        pytest.raises(SurfaceError, match="cannot read archive entry"),
        composer.staged(tmp_path / "build"),
    ):
        pass


def test_stage_rejects_traversal_and_duplicate_entries(tmp_path: Path) -> None:
    traversal = _archive(
        [
            ("index.html", b"ok"),
            ("detalhe-tecnico/index.html", b"ok"),
            ("instalacao/index.html", b"ok"),
            ("../escape.txt", b"escape"),
        ]
    )
    composer = _configured_composer(traversal, b"")
    with (
        pytest.raises(SurfaceError, match="unsafe path"),
        composer.staged(tmp_path / "build"),
    ):
        pass

    duplicate = _archive(
        [
            ("index.html", b"one"),
            ("index.html", b"two"),
            ("detalhe-tecnico/index.html", b"ok"),
            ("instalacao/index.html", b"ok"),
        ]
    )
    composer = _configured_composer(duplicate, b"")
    with (
        pytest.raises(SurfaceError, match="path collision"),
        composer.staged(tmp_path / "build"),
    ):
        pass


def test_stage_rejects_forbidden_selector_payload(tmp_path: Path) -> None:
    selector = _surface_archive("selector", extra=[("data.json", b"governed")])
    composer = _configured_composer(b"", selector)
    with (
        pytest.raises(SurfaceError, match="forbidden path"),
        composer.staged(tmp_path / "build"),
    ):
        pass


def test_compose_rejects_symlink_destination(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "nested").mkdir()
    (source / "nested" / "app.js").write_text("app", encoding="utf-8")
    site = tmp_path / "site"
    site.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (site / "nested").symlink_to(outside, target_is_directory=True)
    prepared = PreparedSurface(SurfaceRelease.from_environment("landing", {}), source)

    with pytest.raises(SurfaceError, match="symlink"):
        IllusionistSurfaceComposer.from_environment({}).compose(
            site, (prepared, prepared)
        )


def test_compose_rejects_directory_destination(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "index.html").write_text("app", encoding="utf-8")
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").mkdir()
    prepared = PreparedSurface(SurfaceRelease.from_environment("landing", {}), source)

    with pytest.raises(SurfaceError, match="is a directory"):
        IllusionistSurfaceComposer.from_environment({}).compose(
            site, (prepared, prepared)
        )
