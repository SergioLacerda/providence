"""Compiler toolchain diagnostics for `providence doctor compiler`.

Builds a stable JSON-serializable report about the sdd-compile binary: how it
was resolved, its version, the CLI<->binary handshake state, the download
cache, the packaged native assets, and a dry validation of compiled artifacts.
Every probe is best-effort  failures are reported as strings inside the
report, never raised, so the doctor can always print a full picture.

The optional prune operation (`--prune`) is the single mutating capability:
it removes stale download-cache entries, keeping only the versions the
installed CLI can legitimately resolve and the packaged digest in use.
"""

from __future__ import annotations

import hashlib
import importlib.resources as resources
import os
import shutil
from pathlib import Path
from typing import Any

REPORT_SCHEMA_VERSION = "1.0"


def _probe_cli_version() -> tuple[str | None, str | None]:
    try:
        from importlib.metadata import version as _pkg_version

        return _pkg_version("providence-cli"), None
    except Exception as exc:
        return None, str(exc)


def _probe_cache(cache_dir: Path) -> dict[str, Any]:
    if not cache_dir.exists():
        return {"dir": str(cache_dir), "entries": []}
    entries = sorted(
        path.relative_to(cache_dir).as_posix()
        for path in cache_dir.rglob("*")
        if path.is_file()
    )
    return {"dir": str(cache_dir), "entries": entries}


def _probe_packaged_native() -> dict[str, Any]:
    try:
        native = resources.files("providence_core") / "_native"
        if not native.is_dir():
            return {"present": False, "assets": []}
        assets = sorted(entry.name for entry in native.iterdir() if entry.is_file())
        return {"present": bool(assets), "assets": assets}
    except Exception as exc:
        return {"present": False, "assets": [], "error": str(exc)}


def _probe_validate(runner: Any, workspace_root: Path) -> dict[str, Any]:
    compiled_dir = workspace_root / ".providence" / "compiled"
    if not compiled_dir.exists():
        return {"ran": False, "compiled_dir": str(compiled_dir)}
    try:
        result = runner.validate_compilation_detailed(str(compiled_dir))
        return {
            "ran": True,
            "compiled_dir": str(compiled_dir),
            "ok": result.get("ok", False),
            "errors": result.get("errors", []),
        }
    except Exception as exc:
        return {"ran": True, "compiled_dir": str(compiled_dir), "error": str(exc)}


def _current_packaged_digest() -> str | None:
    """Return the sha256 of the bundled binary for this platform, if any."""
    try:
        from providence_core.utils.compiler_runner import _asset_platform

        goos, goarch, ext = _asset_platform()
        asset = (
            resources.files("providence_core")
            / "_native"
            / (f"sdd-compile-{goos}-{goarch}{ext}")
        )
        if not asset.is_file():
            return None
        return hashlib.sha256(asset.read_bytes()).hexdigest()
    except Exception:
        return None


def prune_cache(
    cache_dir: Path,
    *,
    keep_versions: list[str],
    keep_packaged_digest: str | None,
) -> dict[str, Any]:
    """Remove stale cache entries; pure function over an explicit cache dir.

    Deletes version directories not in `keep_versions` and `packaged/<digest>/`
    directories other than `keep_packaged_digest`. When no packaged digest is
    known, packaged entries are left untouched (cannot tell which is in use).
    """
    removed: list[str] = []
    kept: list[str] = []
    if not cache_dir.exists():
        return {"removed": removed, "kept": kept}
    for entry in sorted(cache_dir.iterdir()):
        if not entry.is_dir():
            kept.append(entry.name)
            continue
        if entry.name == "packaged":
            for digest_dir in sorted(entry.iterdir()):
                if (
                    keep_packaged_digest is None
                    or not digest_dir.is_dir()
                    or digest_dir.name == keep_packaged_digest
                ):
                    kept.append(f"packaged/{digest_dir.name}")
                else:
                    shutil.rmtree(digest_dir, ignore_errors=True)
                    removed.append(f"packaged/{digest_dir.name}")
            continue
        if entry.name in keep_versions:
            kept.append(entry.name)
        else:
            shutil.rmtree(entry, ignore_errors=True)
            removed.append(entry.name)
    return {"removed": removed, "kept": kept}


def run_prune() -> dict[str, Any]:
    """Resolve the real keep-set and prune the real cache (CLI entrypoint)."""
    from providence_core.utils.compiler_runner import (
        _cache_dir,
        _release_version_candidates,
    )

    if os.environ.get("SDD_COMPILE_BIN", "").strip():
        return {"skipped": "SDD_COMPILE_BIN override active; nothing pruned"}
    cli_version, cli_error = _probe_cli_version()
    if cli_version is None:
        return {
            "skipped": "cannot determine installed providence-cli version; nothing pruned",
            "error": cli_error,
        }
    return prune_cache(
        _cache_dir(),
        keep_versions=_release_version_candidates(cli_version),
        keep_packaged_digest=_current_packaged_digest(),
    )


def build_compiler_report(workspace_root: Path | None = None) -> dict[str, Any]:
    """Build the full read-only compiler diagnostics report."""
    from providence_core.utils.compiler_runner import CompilerRunner, _cache_dir

    cli_version, cli_error = _probe_cli_version()
    report: dict[str, Any] = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "cli_version": cli_version,
        "binary": {},
        "handshake": {},
        "cache": _probe_cache(_cache_dir()),
        "packaged_native": _probe_packaged_native(),
        "validate": {"ran": False},
    }
    if cli_error:
        report["cli_version_error"] = cli_error

    try:
        runner = CompilerRunner()
    except Exception as exc:
        report["binary"] = {"resolved": False, "error": str(exc)}
        report["handshake"] = {"status": "unavailable"}
        return report

    report["binary"] = {
        "resolved": True,
        "path": str(runner._binary),
        "resolution_rule": runner.resolution_rule,
    }
    try:
        report["binary"]["version"] = runner.version()
    except Exception as exc:
        report["binary"]["version_error"] = str(exc)

    try:
        report["handshake"] = dict(runner.verify_version_handshake())
    except Exception as exc:
        report["handshake"] = {"status": "skew", "error": str(exc)}

    root = workspace_root or Path.cwd()
    report["validate"] = _probe_validate(runner, root)
    return report
