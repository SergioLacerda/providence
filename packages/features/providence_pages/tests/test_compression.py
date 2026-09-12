"""Tests for providence_pages.compression."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from providence_pages.compression import CompressionEngine

pytestmark = pytest.mark.unit


class TestCompressGzip:
    def test_compresses_file_above_threshold(self, tmp_path: Path) -> None:
        file_path = tmp_path / "app.js"
        file_path.write_bytes(b"x" * 2048)

        result = CompressionEngine().compress_gzip(file_path, threshold=1024)

        assert result is not None
        assert result.algorithm == "gzip"
        assert result.original_size == 2048
        assert result.compressed_size > 0
        output_path = Path(result.output)
        assert output_path.exists()
        assert output_path.suffix == ".gz"
        decompressed = gzip.decompress(output_path.read_bytes())
        assert decompressed == b"x" * 2048

    def test_skips_file_below_threshold(self, tmp_path: Path) -> None:
        file_path = tmp_path / "small.js"
        file_path.write_bytes(b"x" * 10)

        result = CompressionEngine().compress_gzip(file_path, threshold=1024)

        assert result is None

    def test_ratio_is_between_zero_and_one_for_compressible_data(
        self, tmp_path: Path
    ) -> None:
        file_path = tmp_path / "repeat.txt"
        file_path.write_bytes(b"a" * 5000)

        result = CompressionEngine().compress_gzip(file_path, threshold=1024)

        assert result is not None
        assert 0.0 < result.ratio <= 1.0


class TestCompressBrotli:
    def test_returns_none_when_brotli_unavailable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from providence_pages import compression as mod

        monkeypatch.setattr(mod, "_BROTLI_AVAILABLE", False)
        file_path = tmp_path / "app.js"
        file_path.write_bytes(b"x" * 2048)

        result = CompressionEngine().compress_brotli(file_path)
        assert result is None

    def test_compresses_when_brotli_available(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from providence_pages import compression as mod

        class _FakeBrotli:
            @staticmethod
            def compress(data: bytes) -> bytes:
                return data[: len(data) // 2] or b"x"

        monkeypatch.setattr(mod, "_BROTLI_AVAILABLE", True)
        monkeypatch.setattr(mod, "_brotli", _FakeBrotli())

        file_path = tmp_path / "app.js"
        file_path.write_bytes(b"x" * 2048)

        result = CompressionEngine().compress_brotli(file_path)

        assert result is not None
        assert result.algorithm == "brotli"
        output_path = Path(result.output)
        assert output_path.exists()
        assert output_path.suffix == ".br"


class TestHashedName:
    def test_hashed_name_inserts_hash_before_extension(self, tmp_path: Path) -> None:
        file_path = tmp_path / "app.js"
        file_path.write_bytes(b"console.log('hi')")

        name = CompressionEngine().hashed_name(file_path)

        assert name.startswith("app.")
        assert name.endswith(".js")
        parts = name.split(".")
        assert len(parts) == 3
        assert len(parts[1]) == 8

    def test_hashed_name_is_deterministic_for_same_content(
        self, tmp_path: Path
    ) -> None:
        file1 = tmp_path / "a.js"
        file2 = tmp_path / "b.js"
        file1.write_bytes(b"same content")
        file2.write_bytes(b"same content")

        engine = CompressionEngine()
        hash1 = engine.hashed_name(file1).split(".")[1]
        hash2 = engine.hashed_name(file2).split(".")[1]
        assert hash1 == hash2

    def test_hashed_name_differs_for_different_content(self, tmp_path: Path) -> None:
        file1 = tmp_path / "a.js"
        file2 = tmp_path / "b.js"
        file1.write_bytes(b"content one")
        file2.write_bytes(b"content two")

        engine = CompressionEngine()
        name1 = engine.hashed_name(file1)
        name2 = engine.hashed_name(file2)
        assert name1 != name2


class TestGenerateManifest:
    def test_generates_valid_json_manifest(self, tmp_path: Path) -> None:
        file_path = tmp_path / "app.js"
        file_path.write_bytes(b"x" * 2048)
        engine = CompressionEngine()
        result = engine.compress_gzip(file_path, threshold=1024)
        assert result is not None

        manifest_path = tmp_path / "manifest.json"
        engine.generate_manifest([result], manifest_path)

        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert len(data["entries"]) == 1
        assert data["entries"][0]["algorithm"] == "gzip"

    def test_generates_empty_manifest_for_no_results(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "manifest.json"
        CompressionEngine().generate_manifest([], manifest_path)

        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert data["entries"] == []
