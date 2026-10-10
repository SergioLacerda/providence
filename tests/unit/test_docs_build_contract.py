from __future__ import annotations

import hashlib
import io
import json
import tarfile
from pathlib import Path

from providence_pages.illusionist import IllusionistSurfaceComposer
from providence_wizard.orchestration.wizard.selector_compiler import SelectorCompiler


def _archive(entries: list[tuple[str, bytes]]) -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as bundle:
        for name, content in entries:
            info = tarfile.TarInfo(name)
            info.size = len(content)
            bundle.addfile(info, io.BytesIO(content))
    return output.getvalue()


def _configured_composer() -> IllusionistSurfaceComposer:
    landing = _archive(
        [
            ("index.html", b"external landing"),
            ("detalhe-tecnico/index.html", b"technical"),
            ("instalacao/index.html", b"install"),
        ]
    )
    selector = _archive(
        [
            ("index.html", b"external selector"),
            ("selector.js", b"external selector js"),
            ("style.css", b"external selector css"),
        ]
    )
    environment = {
        "ILLUSIONIST_REPOSITORY": "Example/illusionist-web",
        "ILLUSIONIST_PROVIDENCE_LANDING_VERSION": "providence-v1.2.3",
        "ILLUSIONIST_PROVIDENCE_LANDING_ASSET": (
            "illusionist-providence-surface-v1.2.3.tar.gz"
        ),
        "ILLUSIONIST_PROVIDENCE_LANDING_SHA256": hashlib.sha256(landing).hexdigest(),
        "ILLUSIONIST_PROVIDENCE_SELECTOR_VERSION": "providence-selector-v1.2.3",
        "ILLUSIONIST_PROVIDENCE_SELECTOR_ASSET": (
            "illusionist-providence-selector-surface-v1.2.3.tar.gz"
        ),
        "ILLUSIONIST_PROVIDENCE_SELECTOR_SHA256": hashlib.sha256(selector).hexdigest(),
    }
    releases = (
        ("landing", landing, environment["ILLUSIONIST_PROVIDENCE_LANDING_ASSET"]),
        ("selector", selector, environment["ILLUSIONIST_PROVIDENCE_SELECTOR_ASSET"]),
    )
    payloads: dict[str, bytes] = {}
    for surface, archive, asset in releases:
        tag = environment[
            "ILLUSIONIST_PROVIDENCE_"
            + ("LANDING" if surface == "landing" else "SELECTOR")
            + "_VERSION"
        ]
        base = f"https://github.com/Example/illusionist-web/releases/download/{tag}"
        payloads[f"{base}/{asset}"] = archive
        payloads[f"{base}/{asset}.sha256"] = (
            f"{hashlib.sha256(archive).hexdigest()}  {asset}\n".encode()
        )

    return IllusionistSurfaceComposer(
        "Example/illusionist-web", payloads.__getitem__, environment
    )


def test_full_build_contract_keeps_artifact_local_and_pages_external(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    mandates = repo_root / ".providence" / "source" / "mandates"
    mandates.mkdir(parents=True)
    (repo_root / ".providence" / "metadata.json").write_text(
        json.dumps({"mandates": {"M001": "Clean Architecture"}}),
        encoding="utf-8",
    )
    (mandates / "mandates.md").write_text(
        "## M001: Clean Architecture\n\nKeep domain logic isolated.\n",
        encoding="utf-8",
    )

    site = tmp_path / "build" / "site"
    selector = site / "selector"
    SelectorCompiler(repo_root=repo_root).build_artifact(selector)
    (selector / "docs.index.json").write_text('{"documents": []}', encoding="utf-8")
    (site / ".compressed").mkdir(parents=True)
    (site / ".compressed" / "manifest.json").write_text(
        '{"entries": []}', encoding="utf-8"
    )

    data_before = (selector / "data.json").read_bytes()
    docs_index_before = (selector / "docs.index.json").read_bytes()

    composer = _configured_composer()
    with composer.staged(tmp_path / "build") as prepared:
        composer.compose(site, prepared)

    assert (site / "index.html").read_bytes() == b"external landing"
    assert (selector / "index.html").read_bytes() == b"external selector"
    assert (selector / "data.json").read_bytes() == data_before
    assert (selector / "docs.index.json").read_bytes() == docs_index_before
    assert (site / ".compressed" / "manifest.json").is_file()
    assert not (repo_root / "build" / "site" / "index.html").exists()
    repository_root = Path(__file__).resolve().parents[2]
    assert not (
        repository_root
        / "packages/interfaces/providence_wizard/src/providence_wizard/templates/selector"
    ).exists()
