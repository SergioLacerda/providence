"""Compression engine: gzip/brotli compression and hash-based asset naming."""

from __future__ import annotations

import gzip
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_brotli: Any = None
try:
    import brotli as _brotli  # type: ignore[import-not-found,no-redef]

    _BROTLI_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only without optional dep
    _BROTLI_AVAILABLE = False

DEFAULT_THRESHOLD_BYTES = 1024
HASH_LENGTH = 8


@dataclass
class CompressionResult:
    """Outcome of compressing a single file."""

    source: str
    output: str
    algorithm: str
    original_size: int
    compressed_size: int
    ratio: float


class CompressionEngine:
    """Compresses files with gzip/brotli and produces a manifest."""

    def compress_gzip(
        self, path: Path, threshold: int = DEFAULT_THRESHOLD_BYTES
    ) -> CompressionResult | None:
        """Gzip-compress a file if it meets the size threshold.

        Returns None when the file is smaller than threshold (not worth compressing).
        """
        original_size = path.stat().st_size
        if original_size < threshold:
            return None

        data = path.read_bytes()
        compressed = gzip.compress(data)
        output_path = path.with_suffix(path.suffix + ".gz")
        output_path.write_bytes(compressed)

        return CompressionResult(
            source=str(path),
            output=str(output_path),
            algorithm="gzip",
            original_size=original_size,
            compressed_size=len(compressed),
            ratio=_ratio(original_size, len(compressed)),
        )

    def compress_brotli(self, path: Path) -> CompressionResult | None:
        """Brotli-compress a file. Returns None when brotli is unavailable."""
        if not _BROTLI_AVAILABLE:
            return None

        data = path.read_bytes()
        compressed = _brotli.compress(data)
        output_path = path.with_suffix(path.suffix + ".br")
        output_path.write_bytes(compressed)

        return CompressionResult(
            source=str(path),
            output=str(output_path),
            algorithm="brotli",
            original_size=len(data),
            compressed_size=len(compressed),
            ratio=_ratio(len(data), len(compressed)),
        )

    def hashed_name(self, path: Path, length: int = HASH_LENGTH) -> str:
        """Return a hash-based asset name: app.js -> app.<hash>.js."""
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:length]
        return f"{path.stem}.{digest}{path.suffix}"

    def generate_manifest(
        self, results: list[CompressionResult], output_path: Path
    ) -> Path:
        """Write a JSON manifest describing compression results."""
        manifest = {"entries": [asdict(r) for r in results]}
        output_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return output_path


def _ratio(original_size: int, compressed_size: int) -> float:
    if original_size == 0:
        return 0.0
    return round(1 - (compressed_size / original_size), 4)
