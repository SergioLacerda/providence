"""CompilerRunner: Python bridge to the Go `sdd-compile` binary.

This is the only Python-facing entrypoint for invoking governance
compilation. It replaces direct imports of `sdd_compiler.governance_compiler`
with subprocess calls to the Go binary, parsing its JSON stdout output.
"""

from __future__ import annotations

import hashlib
import importlib.resources as resources
import json
import os
import platform
import re
import shutil
import ssl
import stat
import sys
import urllib.error
import urllib.request
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from pathlib import Path
from typing import Any, TypedDict, cast

from providence_core.utils.environment import detect_repo_root
from providence_core.utils.process import SafeProcessRunner

__all__ = [
    "EXPECTED_ARTIFACT_METADATA_VERSION",
    "CompilationResult",
    "CompilerRunner",
    "CompilerRunnerError",
    "KeygenResult",
    "SignResult",
    "ValidationCheck",
    "ValidationResult",
    "VerifyResult",
]

_RELEASE_REPO = "SergioLacerda/providence"
_DOWNLOAD_TIMEOUT_SECONDS = 30
# Artifact metadata contract: the `version` field the Go compiler writes into
# metadata-*.json. Bump together with the Go side (generateMetadata) — the
# compile-time handshake rejects binaries emitting a different contract.
EXPECTED_ARTIFACT_METADATA_VERSION = "3.0"
_UNKNOWN_COMMAND_RE = re.compile(r'unknown command "([^"]+)" for')
_SEMVER_RELEASE_RE = re.compile(r"^(?P<release>\d+\.\d+\.\d+)(?P<suffix>.*)$")


class CompilerRunnerError(RuntimeError):
    """Raised when the sdd-compile binary cannot be located or fails."""


class CompilationResult(TypedDict, total=False):
    """Mirrors the Go binary's `compile` JSON output."""

    ok: bool
    core_msgpack_file: str
    client_msgpack_file: str
    core_metadata: str
    client_metadata: str
    core_fingerprint: str
    client_fingerprint: str
    core_fingerprint_salt: str | None
    core_item_count: int
    client_item_count: int
    signed: bool
    signer_key_id: str
    signature_files: list[str]
    error: str


class ValidationCheck(TypedDict):
    """A single named validation check result."""

    name: str
    ok: bool
    details: str


class ValidationResult(TypedDict):
    """Mirrors the Go binary's `validate` JSON output."""

    ok: bool
    errors: list[str]
    checks: list[ValidationCheck]


class KeygenResult(TypedDict, total=False):
    """Mirrors the Go binary's `keygen` JSON output."""

    ok: bool
    private_key_path: str
    public_key_path: str
    error: str


class SignResult(TypedDict, total=False):
    """Mirrors the Go binary's `sign` JSON output."""

    ok: bool
    sig_path: str
    error: str


class VerifyResult(TypedDict, total=False):
    """Mirrors the Go binary's `verify` JSON output."""

    ok: bool
    valid: bool
    error: str


def _cache_dir() -> Path:
    """Resolve the sdd-compile binary cache directory.

    Precedence: `SDD_CACHE_DIR` (SDD-dedicated override, used as-is) ->
    `XDG_CACHE_HOME` (shared cache root, nested under `sdd/` per the XDG
    convention of not writing directly into a shared directory) -> the
    original `~/.providence/bin` fallback, unchanged so existing installs keep
    resolving to the same cache location without any env var set.
    """
    sdd_override = os.environ.get("SDD_CACHE_DIR", "").strip()
    if sdd_override:
        return Path(sdd_override) / "bin"

    xdg_cache_home = os.environ.get("XDG_CACHE_HOME", "").strip()
    if xdg_cache_home:
        return Path(xdg_cache_home) / "sdd" / "bin"

    return Path.home() / ".providence" / "bin"


def _asset_platform() -> tuple[str, str, str]:
    """Return (goos, goarch, ext) for the current platform, matching release asset names."""
    system = platform.system().lower()
    goos = {"linux": "linux", "darwin": "darwin", "windows": "windows"}.get(system)
    if goos is None:
        raise CompilerRunnerError(
            f"Unsupported platform for sdd-compile download: {system}"
        )

    machine = platform.machine().lower()
    goarch = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }.get(machine)
    if goarch is None:
        raise CompilerRunnerError(
            f"Unsupported architecture for sdd-compile download: {machine}"
        )

    ext = ".exe" if goos == "windows" else ""
    return goos, goarch, ext


def _installed_cli_version() -> str:
    try:
        return _pkg_version("providence-cli")
    except PackageNotFoundError as exc:
        raise CompilerRunnerError(
            "Cannot determine providence-cli version to download a matching sdd-compile binary. "
            "Install providence-cli via pip/uv or set SDD_COMPILE_BIN to a local binary."
        ) from exc


def _debug_downloads_enabled() -> bool:
    return os.environ.get("SDD_COMPILE_DEBUG_DOWNLOADS", "").strip().lower() not in (
        "",
        "0",
        "false",
    )


def _debug_log(message: str) -> None:
    if _debug_downloads_enabled():
        sys.stderr.write(f"[sdd-compile download] {message}\n")


def _tls_context() -> ssl.SSLContext:
    """TLS context for release downloads: system trust store plus certifi.

    Standalone Python builds (e.g. the uv-managed interpreter used by
    `uv tool install`) may have no usable system CA store, which surfaces as
    CERTIFICATE_VERIFY_FAILED on otherwise clean machines. Loading certifi's
    bundle on top of the default store covers GitHub's chain in that case.
    Corporate TLS-intercepting proxies still need SSL_CERT_FILE, which
    create_default_context already honors.
    """
    ctx = ssl.create_default_context()
    try:
        import certifi
    except ImportError:
        _debug_log("certifi not installed; using system trust store only")
    else:
        ctx.load_verify_locations(certifi.where())
    return ctx


def _download(url: str) -> bytes | None:
    if not url.startswith("https://github.com/"):
        raise CompilerRunnerError(
            f"Refusing to fetch sdd-compile from non-GitHub URL: {url}"
        )
    _debug_log(f"GET {url}")
    try:
        with urllib.request.urlopen(  # nosec B310 -- scheme/host pinned to https://github.com/ above.
            url, timeout=_DOWNLOAD_TIMEOUT_SECONDS, context=_tls_context()
        ) as response:
            payload = cast(bytes, response.read())
            _debug_log(f"200 {url} ({len(payload)} bytes)")
            return payload
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            _debug_log(f"404 {url}")
            return None
        _debug_log(f"error {url}: {exc}")
        raise CompilerRunnerError(
            f"Failed to download sdd-compile from {url}: {exc}"
        ) from exc
    except urllib.error.URLError as exc:
        _debug_log(f"error {url}: {exc}")
        raise CompilerRunnerError(
            f"Failed to download sdd-compile from {url}: {exc}"
        ) from exc


def _release_version_candidates(version: str) -> list[str]:
    """Return release versions worth checking for a package version.

    Hatch-vcs installs from commits after a tag produce versions such as
    ``1.0.3.dev15+g725459b8d``. Those are valid package versions but not release
    tags. In that case, try the exact package version first and then the nearest
    base release tag.
    """
    candidates = [version]
    match = _SEMVER_RELEASE_RE.match(version)
    if match and match.group("suffix"):
        release = match.group("release")
        if release not in candidates:
            candidates.append(release)
    return candidates


def _format_tried_tags(tags: list[str]) -> str:
    if len(tags) == 2:
        return f"{tags[0]} and {tags[1]}"
    if len(tags) > 2:
        return f"{', '.join(tags[:-1])}, and {tags[-1]}"
    return ", ".join(tags)


def _fetch_release_binary(version: str, asset_name: str) -> tuple[bytes, str]:
    """Fetch the asset bytes and its expected sha256 for a given release version.

    Tries both the lowercase-v and uppercase-V tag conventions used by this
    project's release workflow. For local/dev package versions generated from a
    release tag, also tries the base release version because no GitHub release
    asset can exist for the local version identifier.
    """
    tried_tags: list[str] = []
    for candidate in _release_version_candidates(version):
        for tag in (f"v{candidate}", f"V{candidate}"):
            tried_tags.append(tag)
            base = f"https://github.com/{_RELEASE_REPO}/releases/download/{tag}"
            payload = _download(f"{base}/{asset_name}")
            if payload is None:
                continue
            checksums = _download(f"{base}/SHA256SUMS")
            if checksums is None:
                raise CompilerRunnerError(
                    f"sdd-compile release asset found for tag {tag} but SHA256SUMS is missing; "
                    "refusing to use an unverified binary."
                )
            expected = None
            for line in checksums.decode("utf-8", errors="replace").splitlines():
                parts = line.split()
                if len(parts) == 2 and parts[1] == asset_name:
                    expected = parts[0]
                    break
            if expected is None:
                raise CompilerRunnerError(
                    f"SHA256SUMS for tag {tag} does not list {asset_name}; "
                    "refusing to use an unverified binary."
                )
            return payload, expected

    raise CompilerRunnerError(
        f"No sdd-compile release binary found for version {version} "
        f"(asset {asset_name}; tried tags {_format_tried_tags(tried_tags)}). "
        "Standalone installs need a release asset matching the installed "
        "providence-cli version. For dev/local installs, build sdd-compile locally "
        "and provide it via SDD_COMPILE_BIN."
    )


def _download_and_cache_binary(version: str) -> Path:
    goos, goarch, ext = _asset_platform()
    asset_name = f"sdd-compile-{goos}-{goarch}{ext}"
    cached_path = _cache_dir() / version / asset_name
    if cached_path.exists():
        return cached_path

    payload, expected_sha256 = _fetch_release_binary(version, asset_name)
    actual_sha256 = hashlib.sha256(payload).hexdigest()
    if actual_sha256 != expected_sha256:
        raise CompilerRunnerError(
            f"sdd-compile download checksum mismatch for {asset_name} "
            f"(expected {expected_sha256}, got {actual_sha256})"
        )

    cached_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = cached_path.with_suffix(cached_path.suffix + ".tmp")
    tmp_path.write_bytes(payload)
    if goos != "windows":
        tmp_path.chmod(
            tmp_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        )
    tmp_path.replace(cached_path)
    return cached_path


def _materialize_packaged_binary(asset_name: str) -> Path | None:
    """Copy a bundled compiler binary to the executable cache, if packaged."""
    packaged = resources.files("providence_core") / "_native" / asset_name
    if not packaged.is_file():
        return None

    payload = packaged.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    cached_path = _cache_dir() / "packaged" / digest / asset_name
    if cached_path.exists():
        return cached_path

    cached_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = cached_path.with_suffix(cached_path.suffix + ".tmp")
    tmp_path.write_bytes(payload)
    if not asset_name.endswith(".exe"):
        tmp_path.chmod(
            tmp_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        )
    tmp_path.replace(cached_path)
    return cached_path


def _locate_binary_with_rule(repo_root: Path | None = None) -> tuple[Path, str]:
    """Locate the sdd-compile binary and report which resolution rule matched.

    Resolution order (rule name in parentheses):
    1. SDD_COMPILE_BIN environment variable (`env_override`)
    2. <repo_root>/tools/sdd-compile/bin/sdd-compile (`repo_build`)
    3. `sdd-compile` on PATH (`path`)
    4. Packaged native binary bundled with providence-core (`packaged`)
    5. Cached/downloaded release binary matching the installed providence-cli version
       (`download`; skipped when SDD_COMPILE_NO_DOWNLOAD is set)
    """
    goos, goarch, ext = _asset_platform()
    asset_name = f"sdd-compile-{goos}-{goarch}{ext}"
    env_override = os.environ.get("SDD_COMPILE_BIN", "").strip()
    if env_override:
        path = Path(env_override)
        if path.exists():
            return path, "env_override"
        raise CompilerRunnerError(
            f"SDD_COMPILE_BIN is set but does not exist: {env_override}"
        )

    root = repo_root or _try_detect_repo_root()
    if root is not None:
        binary_name = (
            "sdd-compile.exe" if platform.system() == "Windows" else "sdd-compile"
        )
        built_path = root / "tools" / "sdd-compile" / "bin" / binary_name
        if built_path.exists():
            return built_path, "repo_build"

    on_path = shutil.which("sdd-compile")
    if on_path:
        return Path(on_path), "path"

    packaged = _materialize_packaged_binary(asset_name)
    if packaged is not None:
        return packaged, "packaged"

    if not os.environ.get("SDD_COMPILE_NO_DOWNLOAD", "").strip():
        version = _installed_cli_version()
        return _download_and_cache_binary(version), "download"

    raise CompilerRunnerError(
        "sdd-compile binary not found. Build it with 'make build-compiler', "
        "set SDD_COMPILE_BIN to its path, or unset SDD_COMPILE_NO_DOWNLOAD to "
        "allow fetching the matching release binary."
    )


def _locate_binary(repo_root: Path | None = None) -> Path:
    """Locate the sdd-compile binary (see `_locate_binary_with_rule`)."""
    return _locate_binary_with_rule(repo_root)[0]


def _try_detect_repo_root() -> Path | None:
    try:
        return detect_repo_root()
    except RuntimeError:
        return None


class CompilerRunner:
    """Invokes the Go sdd-compile binary and parses its JSON output."""

    def __init__(
        self,
        repo_root: str | Path | None = None,
        runner: SafeProcessRunner | None = None,
    ) -> None:
        self.repo_root = (
            Path(repo_root).resolve() if repo_root else _try_detect_repo_root()
        )
        self._binary, self.resolution_rule = _locate_binary_with_rule(self.repo_root)
        self._runner = runner or SafeProcessRunner()
        self._handshake: dict[str, str | None] | None = None

    def version(self) -> str:
        """Return the sdd-compile binary version string."""
        result = self._runner.run([str(self._binary), "version"])
        if not result.success:
            raise CompilerRunnerError(f"sdd-compile version failed: {result.stderr}")
        return result.stdout.strip()

    def verify_version_handshake(self) -> dict[str, str | None]:
        """Check that the resolved binary's release version matches the CLI's.

        Detects version skew (a cached, PATH, or packaged binary from a different
        release than the installed providence-cli) before any compile work, instead of
        letting it surface indirectly as an artifact-validation failure later.

        Returns a report dict with `status`, `binary_version`, `cli_version`.
        Statuses: `ok`, `skipped_dev_override` (SDD_COMPILE_BIN or repo build),
        `skipped_dev_binary` (binary reports a non-release version such as "dev"),
        `skipped_no_cli_version`. Raises CompilerRunnerError (compiler_version_skew)
        on mismatch. The result is cached per runner instance.
        """
        if self._handshake is not None:
            return self._handshake

        def _done(
            status: str, binary_version: str | None, cli_version: str | None
        ) -> dict[str, str | None]:
            self._handshake = {
                "status": status,
                "binary_version": binary_version,
                "cli_version": cli_version,
            }
            return self._handshake

        if self.resolution_rule in ("env_override", "repo_build"):
            return _done("skipped_dev_override", None, None)

        version_output = self.version().strip()
        binary_version = version_output.split()[-1] if version_output else ""
        if not _SEMVER_RELEASE_RE.match(binary_version):
            return _done("skipped_dev_binary", binary_version, None)

        try:
            cli_version = _installed_cli_version()
        except CompilerRunnerError:
            return _done("skipped_no_cli_version", binary_version, None)

        if binary_version in _release_version_candidates(cli_version):
            return _done("ok", binary_version, cli_version)

        raise CompilerRunnerError(
            f"compiler_version_skew: sdd-compile at {self._binary} reports version "
            f"{binary_version}, but the installed providence-cli is {cli_version} "
            f"(resolved via rule '{self.resolution_rule}'). Fix by clearing the "
            f"binary cache (rm -rf {_cache_dir()}) so a matching release is "
            "re-resolved, or set SDD_COMPILE_BIN to a compatible binary."
        )

    def compile(
        self, input_dir: str | Path, output_dir: str | Path
    ) -> CompilationResult:
        """Compile governance JSON to msgpack artifacts via the Go binary."""
        self.verify_version_handshake()
        result = self._runner.run(
            [
                str(self._binary),
                "compile",
                "--input",
                str(input_dir),
                "--output",
                str(output_dir),
            ]
        )
        self._raise_if_unsupported_subcommand(result, subcommand="compile")
        payload = self._parse_json(result, context="compile")
        if not result.success or not payload.get("ok", False):
            error = payload.get("error") or result.stderr.strip() or "compile failed"
            raise CompilerRunnerError(f"sdd-compile compile failed: {error}")
        self._verify_artifact_schema(payload)
        return payload  # type: ignore[return-value]

    def _verify_artifact_schema(self, payload: dict[str, Any]) -> None:
        """Reject compile output whose metadata contract differs from this CLI's.

        The release-lineage handshake (verify_version_handshake) cannot catch a
        binary of an accepted lineage that emits a different artifact contract
        (e.g. HEAD code paired with a base-release binary). Compare the emitted
        metadata `version` against EXPECTED_ARTIFACT_METADATA_VERSION instead of
        letting the divergence surface as downstream validation noise.
        """
        meta_path_str = payload.get("core_metadata")
        if not meta_path_str:
            return
        meta_path = Path(meta_path_str)
        if not meta_path.exists():
            return
        try:
            emitted = json.loads(meta_path.read_text(encoding="utf-8")).get("version")
        except (OSError, json.JSONDecodeError):
            # Unreadable metadata is an artifact-validation concern, not a
            # contract-handshake one; validate_compilation reports it properly.
            return
        if emitted != EXPECTED_ARTIFACT_METADATA_VERSION:
            raise CompilerRunnerError(
                f"artifact_schema_skew: sdd-compile at {self._binary} (resolved via "
                f"rule '{self.resolution_rule}') emitted artifact metadata version "
                f"{emitted!r}, but this CLI expects "
                f"{EXPECTED_ARTIFACT_METADATA_VERSION!r}. The binary release lineage "
                "matches but its artifact contract does not. Fix by clearing the "
                f"binary cache (rm -rf {_cache_dir()}) or setting SDD_COMPILE_BIN "
                "to a binary built from the same source tree as this CLI."
            )

    def validate_compilation_detailed(self, output_dir: str | Path) -> ValidationResult:
        """Validate compiled artifacts via the Go binary, returning structured diagnostics."""
        result = self._runner.run(
            [str(self._binary), "validate", "--dir", str(output_dir)]
        )
        self._raise_if_unsupported_subcommand(result, subcommand="validate")
        payload = self._parse_json(result, context="validate")
        return payload  # type: ignore[return-value]

    def validate_compilation(self, output_dir: str | Path) -> bool:
        """Backward-compatible boolean validation entrypoint."""
        return self.validate_compilation_detailed(output_dir).get("ok", False)

    def keygen(
        self,
        *,
        private_key_path: str | Path,
        public_key_path: str | Path,
    ) -> KeygenResult:
        """Generate a native Ed25519 key pair via the Go binary."""
        result = self._runner.run(
            [
                str(self._binary),
                "keygen",
                "--priv",
                str(private_key_path),
                "--pub",
                str(public_key_path),
            ]
        )
        self._raise_if_unsupported_subcommand(result, subcommand="keygen")
        payload = self._parse_json(result, context="keygen")
        if not payload.get("ok", False):
            error = payload.get("error") or result.stderr.strip() or "keygen failed"
            raise CompilerRunnerError(f"sdd-compile keygen failed: {error}")
        return payload  # type: ignore[return-value]

    def sign(
        self,
        *,
        artifact_path: str | Path,
        key_path: str | Path,
        key_id: str,
        profile: str,
    ) -> SignResult:
        """Sign an artifact with a native Ed25519 key via the Go binary."""
        result = self._runner.run(
            [
                str(self._binary),
                "sign",
                "--artifact",
                str(artifact_path),
                "--key",
                str(key_path),
                "--key-id",
                key_id,
                "--profile",
                profile,
            ]
        )
        self._raise_if_unsupported_subcommand(result, subcommand="sign")
        payload = self._parse_json(result, context="sign")
        if not payload.get("ok", False):
            error = payload.get("error") or result.stderr.strip() or "sign failed"
            raise CompilerRunnerError(f"sdd-compile sign failed: {error}")
        return payload  # type: ignore[return-value]

    def verify(
        self,
        *,
        public_key_pem: str,
        message: str,
        signature_b64: str,
    ) -> VerifyResult:
        """Verify an Ed25519 signature via the Go binary. Never raises for an
        invalid/malformed signature; returns valid=False instead."""
        request = json.dumps(
            {
                "public_key_pem": public_key_pem,
                "message": message,
                "signature_b64": signature_b64,
            }
        )
        result = self._runner.run([str(self._binary), "verify"], input_data=request)
        try:
            payload = self._parse_json(result, context="verify")
        except CompilerRunnerError as exc:
            return {
                "ok": False,
                "valid": False,
                "error": result.stderr.strip() or str(exc),
            }
        return payload  # type: ignore[return-value]

    def _raise_if_unsupported_subcommand(self, result: Any, *, subcommand: str) -> None:
        match = _UNKNOWN_COMMAND_RE.search(result.stderr or "")
        if not match or match.group(1) != subcommand:
            return
        try:
            binary_version = self.version()
        except CompilerRunnerError:
            binary_version = "unknown"
        raise CompilerRunnerError(
            f"sdd-compile at {self._binary} (reports: {binary_version}) does not "
            f"support the '{subcommand}' subcommand — it is likely older than the "
            "installed providence-cli. Fix by clearing the cached binary "
            f"(rm -rf {self._binary.parent} then retry) or by setting "
            "SDD_COMPILE_BIN to a compatible local binary."
        )

    @staticmethod
    def _parse_json(result: Any, *, context: str) -> dict[str, Any]:
        text = result.stdout.strip()
        if not text:
            raise CompilerRunnerError(
                CompilerRunner._diagnostic_message(
                    f"sdd-compile {context} produced no output", result
                )
            )
        try:
            return cast(dict[str, Any], json.loads(text))
        except json.JSONDecodeError as exc:
            raise CompilerRunnerError(
                CompilerRunner._diagnostic_message(
                    f"sdd-compile {context} produced invalid JSON: {exc}", result
                )
            ) from exc

    @staticmethod
    def _diagnostic_message(headline: str, result: Any) -> str:
        parts = [headline]
        stderr = (getattr(result, "stderr", "") or "").strip()
        if stderr:
            parts.append(f"stderr: {stderr}")
        returncode = getattr(result, "returncode", None)
        if returncode is not None:
            parts.append(f"returncode: {returncode}")
        return " | ".join(parts)
