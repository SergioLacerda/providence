"""Integration tests for the full providence_pages pipeline: index -> compress -> publish."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from providence_pages.compression import CompressionEngine
from providence_pages.publisher import GitHubPagesPublisher
from providence_pages.selector import DocumentIndexer

pytestmark = pytest.mark.unit


class TestFullPipeline:
    def test_index_compress_publish(self, tmp_path: Path) -> None:
        site_dir = tmp_path / "site"
        site_dir.mkdir()
        (site_dir / "intro.md").write_text(
            "---\ntitle: Intro\ntags: [guide]\n---\nWelcome to the docs.\n",
            encoding="utf-8",
        )
        (site_dir / "app.js").write_bytes(b"console.log('hi');" * 200)

        indexer = DocumentIndexer()
        entries = indexer.index(site_dir, glob="**/*.md")
        index_path = site_dir / "index.json"
        indexer.to_json(entries, index_path)

        assert len(entries) == 1
        assert (
            json.loads(index_path.read_text(encoding="utf-8"))["documents"][0]["title"]
            == "Intro"
        )

        engine = CompressionEngine()
        compression_results = []
        for file_path in sorted(site_dir.glob("**/*")):
            if not file_path.is_file() or file_path.suffix == ".json":
                continue
            result = engine.compress_gzip(file_path, threshold=10)
            if result is not None:
                compression_results.append(result)

        manifest_path = site_dir / "manifest.json"
        engine.generate_manifest(compression_results, manifest_path)

        assert len(compression_results) >= 1
        assert manifest_path.exists()

        publisher = GitHubPagesPublisher(remote="origin")
        with patch("providence_pages.publisher.SafeProcessRunner.run") as mock_run:
            mock_run.return_value = MagicMock(
                success=True, stdout="", stderr="", returncode=0
            )
            publish_result = publisher.publish(site_dir, branch="gh-pages")

        assert publish_result.success is True
        assert publish_result.branch == "gh-pages"
