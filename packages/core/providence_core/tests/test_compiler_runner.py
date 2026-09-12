"""Tests for the sdd-compile binary resolver."""

from __future__ import annotations

import builtins
import hashlib
import ssl
import stat
import sys
import urllib.error
from pathlib import Path
from types import SimpleNamespace

import pytest

from providence_core.utils import compiler_runner
from providence_core.utils.compiler_runner import CompilerRunner, CompilerRunnerError
from providence_core.utils.text_io import write_text_utf8


def test_fetch_release_binary_error_names_standalone_remediation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing release assets should explain the standalone install fix path."""

    monkeypatch.setattr(compiler_runner, "_download", lambda _url: None)

    with pytest.raises(CompilerRunnerError) as exc_info:
        compiler_runner._fetch_release_binary("1.0.0", "sdd-compile-linux-amd64")

    message = str(exc_info.value)
    assert "No sdd-compile release binary found for version 1.0.0" in message
    assert "asset sdd-compile-linux-amd64" in message
    assert "tried tags v1.0.0 and V1.0.0" in message
    assert "Standalone installs need a release asset" in message
    assert "SDD_COMPILE_BIN" in message


def test_release_version_candidates_include_base_release_for_dev_version() -> None:
    candidates = compiler_runner._release_version_candidates("1.0.3.dev15+g725459b8d")

    assert candidates == ["1.0.3.dev15+g725459b8d", "1.0.3"]


def test_fetch_release_binary_falls_back_to_base_release_for_dev_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A dev/local package version can use the nearest release compiler asset."""

    attempts: list[str] = []

    def _fake_download(url: str) -> bytes | None:
        attempts.append(url)
        if "/v1.0.3/" not in url:
            return None
        if url.endswith("SHA256SUMS"):
            return b"deadbeef  sdd-compile-linux-amd64\n"
        return b"binary-bytes"

    monkeypatch.setattr(compiler_runner, "_download", _fake_download)

    payload, digest = compiler_runner._fetch_release_binary(
        "1.0.3.dev15+g725459b8d", "sdd-compile-linux-amd64"
    )

    assert payload == b"binary-bytes"
    assert digest == "deadbeef"
    assert any("/v1.0.3.dev15+g725459b8d/" in url for url in attempts)
    assert any("/v1.0.3/" in url for url in attempts)


def test_fetch_release_binary_error_when_sha256sums_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A binary present without a SHA256SUMS manifest must be refused, not trusted."""

    def _fake_download(url: str) -> bytes | None:
        if url.endswith("SHA256SUMS"):
            return None
        return b"binary-payload"

    monkeypatch.setattr(compiler_runner, "_download", _fake_download)

    with pytest.raises(CompilerRunnerError) as exc_info:
        compiler_runner._fetch_release_binary("1.0.0", "sdd-compile-linux-amd64")

    message = str(exc_info.value)
    assert "SHA256SUMS is missing" in message
    assert "refusing to use an unverified binary" in message


def test_fetch_release_binary_error_when_checksum_entry_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A SHA256SUMS manifest that omits the requested asset must be refused."""

    def _fake_download(url: str) -> bytes | None:
        if url.endswith("SHA256SUMS"):
            return b"deadbeef  sdd-compile-darwin-arm64\n"
        return b"binary-payload"

    monkeypatch.setattr(compiler_runner, "_download", _fake_download)

    with pytest.raises(CompilerRunnerError) as exc_info:
        compiler_runner._fetch_release_binary("1.0.0", "sdd-compile-linux-amd64")

    message = str(exc_info.value)
    assert "SHA256SUMS for tag v1.0.0 does not list sdd-compile-linux-amd64" in message
    assert "refusing to use an unverified binary" in message


def test_download_logs_attempted_urls_when_debug_env_set(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """SDD_COMPILE_DEBUG_DOWNLOADS should surface the exact URLs attempted."""

    monkeypatch.setenv("SDD_COMPILE_DEBUG_DOWNLOADS", "1")

    class _FakeResponse:
        def __enter__(self) -> _FakeResponse:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def read(self) -> bytes:
            return b"payload"

    monkeypatch.setattr(
        compiler_runner.urllib.request, "urlopen", lambda *_a, **_kw: _FakeResponse()
    )

    result = compiler_runner._download("https://github.com/example/asset")

    assert result == b"payload"
    stderr = capsys.readouterr().err
    assert "https://github.com/example/asset" in stderr


def test_download_debug_logging_disabled_by_default(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("SDD_COMPILE_DEBUG_DOWNLOADS", raising=False)

    class _FakeResponse:
        def __enter__(self) -> _FakeResponse:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def read(self) -> bytes:
            return b"payload"

    monkeypatch.setattr(
        compiler_runner.urllib.request, "urlopen", lambda *_a, **_kw: _FakeResponse()
    )

    compiler_runner._download("https://github.com/example/asset")

    assert capsys.readouterr().err == ""


def test_asset_platform_rejects_unsupported_os(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(compiler_runner.platform, "system", lambda: "PlayStation")

    with pytest.raises(CompilerRunnerError, match="Unsupported platform"):
        compiler_runner._asset_platform()


def test_asset_platform_rejects_unsupported_arch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(compiler_runner.platform, "system", lambda: "Linux")
    monkeypatch.setattr(compiler_runner.platform, "machine", lambda: "riscv64")

    with pytest.raises(CompilerRunnerError, match="Unsupported architecture"):
        compiler_runner._asset_platform()


def test_installed_cli_version_raises_when_package_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise(_name: str) -> str:
        raise compiler_runner.PackageNotFoundError()

    monkeypatch.setattr(compiler_runner, "_pkg_version", _raise)

    with pytest.raises(
        CompilerRunnerError, match="Cannot determine providence-cli version"
    ):
        compiler_runner._installed_cli_version()


def test_tls_context_loads_certifi_bundle() -> None:
    ctx = compiler_runner._tls_context()

    assert isinstance(ctx, ssl.SSLContext)
    assert ctx.cert_store_stats()["x509_ca"] > 0


def test_tls_context_survives_missing_certifi(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import = builtins.__import__

    def _fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "certifi":
            raise ImportError("certifi not installed")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    assert isinstance(compiler_runner._tls_context(), ssl.SSLContext)


def test_download_passes_tls_context_to_urlopen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class _FakeResponse:
        def __enter__(self) -> _FakeResponse:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def read(self) -> bytes:
            return b"payload"

    def _fake_urlopen(_url: str, **kwargs: object) -> _FakeResponse:
        captured.update(kwargs)
        return _FakeResponse()

    monkeypatch.setattr(compiler_runner.urllib.request, "urlopen", _fake_urlopen)

    compiler_runner._download("https://github.com/example/asset")

    assert isinstance(captured.get("context"), ssl.SSLContext)


def test_download_rejects_non_github_url() -> None:
    with pytest.raises(CompilerRunnerError, match="non-GitHub URL"):
        compiler_runner._download("https://evil.example.com/asset")


def test_download_raises_on_http_error_non_404(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_urlopen(*_a: object, **_kw: object) -> None:
        raise urllib.error.HTTPError(
            url="https://github.com/x", code=500, msg="err", hdrs=None, fp=None
        )

    monkeypatch.setattr(compiler_runner.urllib.request, "urlopen", _raise_urlopen)

    with pytest.raises(CompilerRunnerError, match="Failed to download"):
        compiler_runner._download("https://github.com/example/asset")


def test_download_raises_on_url_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_urlopen(*_a: object, **_kw: object) -> None:
        raise urllib.error.URLError("network down")

    monkeypatch.setattr(compiler_runner.urllib.request, "urlopen", _raise_urlopen)

    with pytest.raises(CompilerRunnerError, match="Failed to download"):
        compiler_runner._download("https://github.com/example/asset")


def test_fetch_release_binary_succeeds_and_returns_matching_checksum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_download(url: str) -> bytes:
        if url.endswith("SHA256SUMS"):
            return b"deadbeef  sdd-compile-linux-amd64\n"
        return b"binary-bytes"

    monkeypatch.setattr(compiler_runner, "_download", _fake_download)

    payload, digest = compiler_runner._fetch_release_binary(
        "1.0.0", "sdd-compile-linux-amd64"
    )

    assert payload == b"binary-bytes"
    assert digest == "deadbeef"


def test_download_and_cache_binary_returns_existing_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(compiler_runner, "_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(
        compiler_runner, "_asset_platform", lambda: ("linux", "amd64", "")
    )
    cached = tmp_path / "1.0.0" / "sdd-compile-linux-amd64"
    cached.parent.mkdir(parents=True)
    cached.write_bytes(b"cached")

    result = compiler_runner._download_and_cache_binary("1.0.0")

    assert result == cached


def test_download_and_cache_binary_raises_on_checksum_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(compiler_runner, "_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(
        compiler_runner, "_asset_platform", lambda: ("linux", "amd64", "")
    )
    monkeypatch.setattr(
        compiler_runner, "_fetch_release_binary", lambda *_a: (b"payload", "0" * 64)
    )

    with pytest.raises(CompilerRunnerError, match="checksum mismatch"):
        compiler_runner._download_and_cache_binary("1.0.0")


def test_download_and_cache_binary_writes_and_marks_executable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(compiler_runner, "_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(
        compiler_runner, "_asset_platform", lambda: ("linux", "amd64", "")
    )
    payload = b"payload"
    digest = hashlib.sha256(payload).hexdigest()
    monkeypatch.setattr(
        compiler_runner, "_fetch_release_binary", lambda *_a: (payload, digest)
    )

    result = compiler_runner._download_and_cache_binary("1.0.0")

    assert result.read_bytes() == payload
    if sys.platform != "win32":
        # NTFS has no POSIX exec bit for stat() to report, even though
        # chmod() is still called for a non-Windows target asset.
        assert result.stat().st_mode & stat.S_IXUSR


def test_locate_binary_env_override_returns_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    binary = tmp_path / "sdd-compile"
    write_text_utf8(binary, "x")
    monkeypatch.setenv("SDD_COMPILE_BIN", str(binary))

    assert compiler_runner._locate_binary() == binary


def test_locate_binary_env_override_raises_when_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    missing = tmp_path / "nope"
    monkeypatch.setenv("SDD_COMPILE_BIN", str(missing))

    with pytest.raises(CompilerRunnerError, match="does not exist"):
        compiler_runner._locate_binary()


def test_locate_binary_finds_binary_on_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("SDD_COMPILE_BIN", raising=False)
    monkeypatch.setattr(compiler_runner, "_try_detect_repo_root", lambda: None)
    fake_path = tmp_path / "sdd-compile"
    write_text_utf8(fake_path, "x")
    monkeypatch.setattr(compiler_runner.shutil, "which", lambda _name: str(fake_path))

    assert compiler_runner._locate_binary() == fake_path


def test_locate_binary_uses_packaged_binary_before_download(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    packaged = tmp_path / "packaged-sdd-compile"
    write_text_utf8(packaged, "native")
    monkeypatch.delenv("SDD_COMPILE_BIN", raising=False)
    monkeypatch.setattr(compiler_runner, "_try_detect_repo_root", lambda: None)
    monkeypatch.setattr(compiler_runner.shutil, "which", lambda _name: None)
    monkeypatch.setattr(
        compiler_runner,
        "_materialize_packaged_binary",
        lambda _asset_name: packaged,
    )
    monkeypatch.setattr(
        compiler_runner,
        "_download_and_cache_binary",
        lambda _version: (_ for _ in ()).throw(AssertionError("unexpected download")),
    )

    assert compiler_runner._locate_binary() == packaged


def test_materialize_packaged_binary_copies_resource_to_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    package_root = tmp_path / "package"
    native_dir = package_root / "_native"
    native_dir.mkdir(parents=True)
    write_text_utf8(native_dir / "sdd-compile-linux-amd64", "native")
    monkeypatch.setattr(compiler_runner, "_cache_dir", lambda: tmp_path / "cache")
    monkeypatch.setattr(
        compiler_runner.resources, "files", lambda _package: package_root
    )

    result = compiler_runner._materialize_packaged_binary("sdd-compile-linux-amd64")

    assert result is not None
    assert result.exists()
    assert result.name == "sdd-compile-linux-amd64"
    if sys.platform != "win32":
        # NTFS has no POSIX exec bit for stat() to report, even though
        # chmod() is still called for a non-Windows target asset.
        assert result.stat().st_mode & stat.S_IXUSR


def test_locate_binary_raises_when_nothing_found_and_download_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SDD_COMPILE_BIN", raising=False)
    monkeypatch.setattr(compiler_runner, "_try_detect_repo_root", lambda: None)
    monkeypatch.setattr(compiler_runner.shutil, "which", lambda _name: None)
    monkeypatch.setattr(compiler_runner, "_materialize_packaged_binary", lambda _: None)
    monkeypatch.setenv("SDD_COMPILE_NO_DOWNLOAD", "1")

    with pytest.raises(CompilerRunnerError, match="sdd-compile binary not found"):
        compiler_runner._locate_binary()


def test_try_detect_repo_root_returns_none_on_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise() -> Path:
        raise RuntimeError("no repo")

    monkeypatch.setattr(compiler_runner, "detect_repo_root", _raise)

    assert compiler_runner._try_detect_repo_root() is None


def _make_runner(
    fake_result: SimpleNamespace, resolution_rule: str = "env_override"
) -> CompilerRunner:
    runner = CompilerRunner.__new__(CompilerRunner)
    runner._binary = Path("/fake/sdd-compile")  # type: ignore[attr-defined]
    runner._runner = SimpleNamespace(run=lambda _args: fake_result)  # type: ignore[attr-defined]
    runner.resolution_rule = resolution_rule
    runner._handshake = None  # type: ignore[attr-defined]
    return runner


def test_version_returns_stripped_stdout_on_success() -> None:
    runner = _make_runner(SimpleNamespace(success=True, stdout=" 1.2.3 \n", stderr=""))

    assert runner.version() == "1.2.3"


def test_version_raises_on_process_failure() -> None:
    runner = _make_runner(SimpleNamespace(success=False, stdout="", stderr="boom"))

    with pytest.raises(CompilerRunnerError, match="sdd-compile version failed: boom"):
        runner.version()


def test_compile_raises_when_result_reports_not_ok() -> None:
    runner = _make_runner(
        SimpleNamespace(
            success=True, stdout='{"ok": false, "error": "bad spec"}', stderr=""
        )
    )

    with pytest.raises(CompilerRunnerError, match="bad spec"):
        runner.compile("in", "out")


def test_parse_json_raises_on_empty_stdout_includes_stderr_and_returncode() -> None:
    result = SimpleNamespace(stdout="   ", stderr="boom", returncode=7)

    with pytest.raises(CompilerRunnerError) as exc_info:
        CompilerRunner._parse_json(result, context="compile")

    message = str(exc_info.value)
    assert "sdd-compile compile produced no output" in message
    assert "stderr: boom" in message
    assert "returncode: 7" in message


def test_parse_json_raises_on_invalid_json_includes_stderr_and_returncode() -> None:
    result = SimpleNamespace(stdout="not json", stderr="parse issue", returncode=1)

    with pytest.raises(CompilerRunnerError) as exc_info:
        CompilerRunner._parse_json(result, context="validate")

    message = str(exc_info.value)
    assert "sdd-compile validate produced invalid JSON" in message
    assert "stderr: parse issue" in message
    assert "returncode: 1" in message


def test_parse_json_empty_stdout_with_no_stderr_omits_stderr_line() -> None:
    result = SimpleNamespace(stdout="", stderr="", returncode=0)

    with pytest.raises(CompilerRunnerError) as exc_info:
        CompilerRunner._parse_json(result, context="compile")

    assert "stderr:" not in str(exc_info.value)


def test_cache_dir_is_under_home_sdd_bin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SDD_CACHE_DIR", raising=False)
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    assert compiler_runner._cache_dir() == Path.home() / ".providence" / "bin"


def test_cache_dir_honors_sdd_cache_dir_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("SDD_CACHE_DIR", str(tmp_path))
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    assert compiler_runner._cache_dir() == tmp_path / "bin"


def test_cache_dir_falls_back_to_xdg_cache_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("SDD_CACHE_DIR", raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    assert compiler_runner._cache_dir() == tmp_path / "sdd" / "bin"


def test_cache_dir_prefers_sdd_cache_dir_over_xdg(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("SDD_CACHE_DIR", str(tmp_path / "sdd-override"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    assert compiler_runner._cache_dir() == tmp_path / "sdd-override" / "bin"


def test_asset_platform_windows_uses_exe_extension(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(compiler_runner.platform, "system", lambda: "Windows")
    monkeypatch.setattr(compiler_runner.platform, "machine", lambda: "AMD64")

    goos, goarch, ext = compiler_runner._asset_platform()

    assert (goos, goarch, ext) == ("windows", "amd64", ".exe")


def test_download_returns_none_on_http_404(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_urlopen(*_a: object, **_kw: object) -> None:
        raise urllib.error.HTTPError(
            url="https://github.com/x", code=404, msg="not found", hdrs=None, fp=None
        )

    monkeypatch.setattr(compiler_runner.urllib.request, "urlopen", _raise_urlopen)

    assert compiler_runner._download("https://github.com/example/asset") is None


def test_locate_binary_finds_repo_built_binary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("SDD_COMPILE_BIN", raising=False)
    binary_name = "sdd-compile.exe" if sys.platform == "win32" else "sdd-compile"
    built_path = tmp_path / "tools" / "sdd-compile" / "bin" / binary_name
    built_path.parent.mkdir(parents=True)
    write_text_utf8(built_path, "x")

    assert compiler_runner._locate_binary(tmp_path) == built_path


def test_locate_binary_downloads_when_nothing_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("SDD_COMPILE_BIN", raising=False)
    monkeypatch.delenv("SDD_COMPILE_NO_DOWNLOAD", raising=False)
    monkeypatch.setattr(compiler_runner.shutil, "which", lambda _name: None)
    monkeypatch.setattr(compiler_runner, "_materialize_packaged_binary", lambda _: None)
    monkeypatch.setattr(compiler_runner, "_installed_cli_version", lambda: "1.0.0")
    downloaded = tmp_path / "downloaded-sdd-compile"
    write_text_utf8(downloaded, "x")
    monkeypatch.setattr(
        compiler_runner, "_download_and_cache_binary", lambda _version: downloaded
    )

    assert compiler_runner._locate_binary(tmp_path) == downloaded


def test_compiler_runner_init_locates_binary_via_env_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    binary = tmp_path / "sdd-compile"
    write_text_utf8(binary, "x")
    monkeypatch.setenv("SDD_COMPILE_BIN", str(binary))

    runner = CompilerRunner(repo_root=tmp_path)

    assert runner._binary == binary
    assert runner.repo_root == tmp_path.resolve()


def test_compiler_runner_init_does_not_require_repo_root_for_standalone_env_binary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    binary = tmp_path / "sdd-compile"
    write_text_utf8(binary, "x")
    monkeypatch.setenv("SDD_COMPILE_BIN", str(binary))
    monkeypatch.setattr(
        compiler_runner,
        "detect_repo_root",
        lambda: (_ for _ in ()).throw(RuntimeError("repo root missing")),
    )

    runner = CompilerRunner()

    assert runner._binary == binary
    assert runner.repo_root is None


def test_locate_binary_uses_windows_repo_binary_name(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    binary = tmp_path / "tools" / "sdd-compile" / "bin" / "sdd-compile.exe"
    binary.parent.mkdir(parents=True)
    write_text_utf8(binary, "x")
    monkeypatch.delenv("SDD_COMPILE_BIN", raising=False)
    monkeypatch.setattr(compiler_runner.platform, "system", lambda: "Windows")

    assert compiler_runner._locate_binary(tmp_path) == binary


def test_compile_returns_payload_on_success() -> None:
    runner = _make_runner(
        SimpleNamespace(
            success=True, stdout='{"ok": true, "core_item_count": 3}', stderr=""
        )
    )

    result = runner.compile("in", "out")

    assert result["ok"] is True
    assert result["core_item_count"] == 3


def test_validate_compilation_detailed_returns_parsed_payload() -> None:
    runner = _make_runner(
        SimpleNamespace(
            success=True, stdout='{"ok": true, "errors": [], "checks": []}', stderr=""
        )
    )

    result = runner.validate_compilation_detailed("out")

    assert result["ok"] is True


def test_validate_compilation_returns_ok_flag() -> None:
    runner = _make_runner(
        SimpleNamespace(
            success=True,
            stdout='{"ok": false, "errors": ["x"], "checks": []}',
            stderr="",
        )
    )

    assert runner.validate_compilation("out") is False


def _make_handshake_runner(
    version_stdout: str, resolution_rule: str = "download"
) -> CompilerRunner:
    return _make_runner(
        SimpleNamespace(success=True, stdout=version_stdout, stderr=""),
        resolution_rule=resolution_rule,
    )


def test_handshake_ok_on_exact_version_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(compiler_runner, "_installed_cli_version", lambda: "1.0.3")
    runner = _make_handshake_runner("sdd-compile 1.0.3\n")

    report = runner.verify_version_handshake()

    assert report["status"] == "ok"
    assert report["binary_version"] == "1.0.3"
    assert report["cli_version"] == "1.0.3"


def test_handshake_accepts_base_release_for_dev_cli_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        compiler_runner, "_installed_cli_version", lambda: "1.0.3.dev15+g725459b8d"
    )
    runner = _make_handshake_runner("sdd-compile 1.0.3\n")

    assert runner.verify_version_handshake()["status"] == "ok"


def test_handshake_raises_compiler_version_skew_on_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(compiler_runner, "_installed_cli_version", lambda: "1.0.4")
    runner = _make_handshake_runner("sdd-compile 1.0.3\n")

    with pytest.raises(CompilerRunnerError, match="compiler_version_skew") as exc_info:
        runner.verify_version_handshake()
    message = str(exc_info.value)
    assert "1.0.3" in message
    assert "1.0.4" in message
    assert "rm -rf" in message
    assert "SDD_COMPILE_BIN" in message


def test_handshake_skipped_for_dev_override_rules() -> None:
    def _fail_run(_args: list[str]) -> SimpleNamespace:
        raise AssertionError("version must not be invoked for dev overrides")

    for rule in ("env_override", "repo_build"):
        runner = CompilerRunner.__new__(CompilerRunner)
        runner._binary = Path("/fake/sdd-compile")  # type: ignore[attr-defined]
        runner._runner = SimpleNamespace(run=_fail_run)  # type: ignore[attr-defined]
        runner.resolution_rule = rule
        runner._handshake = None  # type: ignore[attr-defined]

        assert runner.verify_version_handshake()["status"] == "skipped_dev_override"


def test_handshake_skipped_for_dev_binary_version() -> None:
    runner = _make_handshake_runner("sdd-compile dev\n")

    report = runner.verify_version_handshake()

    assert report["status"] == "skipped_dev_binary"
    assert report["binary_version"] == "dev"


def test_handshake_skipped_when_cli_version_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise() -> str:
        raise CompilerRunnerError("no package")

    monkeypatch.setattr(compiler_runner, "_installed_cli_version", _raise)
    runner = _make_handshake_runner("sdd-compile 1.0.3\n")

    assert runner.verify_version_handshake()["status"] == "skipped_no_cli_version"


def test_compile_blocked_by_version_skew_before_invoking_compile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(compiler_runner, "_installed_cli_version", lambda: "1.0.4")
    invoked: list[list[str]] = []

    def _fake_run(args: list[str]) -> SimpleNamespace:
        invoked.append(args)
        if "version" in args:
            return SimpleNamespace(
                success=True, stdout="sdd-compile 1.0.3\n", stderr=""
            )
        return SimpleNamespace(success=True, stdout='{"ok": true}', stderr="")

    runner = CompilerRunner.__new__(CompilerRunner)
    runner._binary = Path("/fake/sdd-compile")  # type: ignore[attr-defined]
    runner._runner = SimpleNamespace(run=_fake_run)  # type: ignore[attr-defined]
    runner.resolution_rule = "download"
    runner._handshake = None  # type: ignore[attr-defined]

    with pytest.raises(CompilerRunnerError, match="compiler_version_skew"):
        runner.compile("in", "out")
    assert all("compile" not in args for args in invoked)


def _compile_runner_with_metadata(tmp_path: Path, metadata: str) -> CompilerRunner:
    meta_path = tmp_path / "metadata-core.json"
    write_text_utf8(meta_path, metadata)
    stdout = (
        '{"ok": true, "core_metadata": "' + str(meta_path).replace("\\", "\\\\") + '"}'
    )
    return _make_runner(SimpleNamespace(success=True, stdout=stdout, stderr=""))


def test_compile_accepts_matching_artifact_metadata_version(tmp_path: Path) -> None:
    runner = _compile_runner_with_metadata(
        tmp_path,
        '{"version": "'
        + compiler_runner.EXPECTED_ARTIFACT_METADATA_VERSION
        + '", "fingerprint": "abc"}',
    )

    assert runner.compile("in", "out")["ok"] is True


def test_compile_raises_artifact_schema_skew_on_metadata_version_mismatch(
    tmp_path: Path,
) -> None:
    runner = _compile_runner_with_metadata(
        tmp_path, '{"version": "9.9", "fingerprint": "abc"}'
    )

    with pytest.raises(CompilerRunnerError, match="artifact_schema_skew") as exc_info:
        runner.compile("in", "out")
    message = str(exc_info.value)
    assert "'9.9'" in message
    assert compiler_runner.EXPECTED_ARTIFACT_METADATA_VERSION in message
    assert "SDD_COMPILE_BIN" in message


def test_compile_skips_schema_check_when_metadata_missing(tmp_path: Path) -> None:
    stdout = (
        '{"ok": true, "core_metadata": "'
        + str(tmp_path / "nonexistent.json").replace("\\", "\\\\")
        + '"}'
    )
    runner = _make_runner(SimpleNamespace(success=True, stdout=stdout, stderr=""))

    assert runner.compile("in", "out")["ok"] is True


def test_keygen_returns_payload_on_success() -> None:
    runner = _make_runner(
        SimpleNamespace(
            success=True,
            stdout='{"ok": true, "private_key_path": "t/k.key", "public_key_path": "t/k.pub.pem"}',
            stderr="",
        )
    )

    result = runner.keygen(private_key_path="t/k.key", public_key_path="t/k.pub.pem")

    assert result["ok"] is True
    assert result["private_key_path"] == "t/k.key"
    assert result["public_key_path"] == "t/k.pub.pem"


def test_keygen_raises_when_result_reports_not_ok() -> None:
    runner = _make_runner(
        SimpleNamespace(
            success=True, stdout='{"ok": false, "error": "disk full"}', stderr=""
        )
    )

    with pytest.raises(CompilerRunnerError, match="disk full"):
        runner.keygen(private_key_path="k.key", public_key_path="k.pub.pem")


def test_keygen_raises_actionable_error_when_binary_missing_subcommand() -> None:
    def _fake_run(args: list[str]) -> SimpleNamespace:
        if "version" in args:
            return SimpleNamespace(
                success=True, stdout="1.0.0\n", stderr="", returncode=0
            )
        return SimpleNamespace(
            success=False,
            stdout="",
            stderr='Error: unknown command "keygen" for "sdd-compile"',
            returncode=1,
        )

    runner = CompilerRunner.__new__(CompilerRunner)
    runner._binary = Path("/fake/sdd-compile")  # type: ignore[attr-defined]
    runner._runner = SimpleNamespace(run=_fake_run)  # type: ignore[attr-defined]

    with pytest.raises(CompilerRunnerError, match="does not support the 'keygen'"):
        runner.keygen(private_key_path="k.key", public_key_path="k.pub.pem")


def test_sign_returns_payload_on_success() -> None:
    runner = _make_runner(
        SimpleNamespace(
            success=True, stdout='{"ok": true, "sig_path": "a.json.sig"}', stderr=""
        )
    )

    result = runner.sign(
        artifact_path="a.json", key_path="k.key", key_id="k1", profile="master"
    )

    assert result["ok"] is True
    assert result["sig_path"] == "a.json.sig"


def test_sign_raises_when_result_reports_not_ok() -> None:
    runner = _make_runner(
        SimpleNamespace(
            success=True, stdout='{"ok": false, "error": "bad key"}', stderr=""
        )
    )

    with pytest.raises(CompilerRunnerError, match="bad key"):
        runner.sign(
            artifact_path="a.json", key_path="k.key", key_id="k1", profile="master"
        )


def test_sign_raises_actionable_error_when_binary_missing_subcommand() -> None:
    call_log: list[list[str]] = []

    def _fake_run(args: list[str]) -> SimpleNamespace:
        call_log.append(args)
        if "version" in args:
            return SimpleNamespace(
                success=True, stdout="1.0.0\n", stderr="", returncode=0
            )
        return SimpleNamespace(
            success=False,
            stdout="",
            stderr='Error: unknown command "sign" for "sdd-compile"',
            returncode=1,
        )

    # Mirrors the real download-cache layout: <cache_dir>/<installed_cli_version>/<asset>.
    # The binary's own self-reported version (queried via `version`) is a distinct
    # value (the sdd-compile release version) and must not be used to reconstruct
    # the cache path.
    binary_path = Path("/home/user/.providence/bin/1.0.0/sdd-compile-linux-amd64")
    runner = CompilerRunner.__new__(CompilerRunner)
    runner._binary = binary_path  # type: ignore[attr-defined]
    runner._runner = SimpleNamespace(run=_fake_run)  # type: ignore[attr-defined]

    with pytest.raises(CompilerRunnerError) as exc_info:
        runner.sign(
            artifact_path="a.json", key_path="k.key", key_id="k1", profile="master"
        )

    message = str(exc_info.value)
    assert "does not support the 'sign' subcommand" in message
    assert str(binary_path) in message
    assert "reports: 1.0.0" in message
    assert f"rm -rf {binary_path.parent}" in message
    assert "SDD_COMPILE_BIN" in message


def _make_verify_runner(fake_result: SimpleNamespace) -> CompilerRunner:
    runner = CompilerRunner.__new__(CompilerRunner)
    runner._binary = Path("/fake/sdd-compile")  # type: ignore[attr-defined]
    runner._runner = SimpleNamespace(  # type: ignore[attr-defined]
        run=lambda _args, **_kwargs: fake_result
    )
    return runner


def test_verify_returns_valid_true_on_success() -> None:
    runner = _make_verify_runner(
        SimpleNamespace(success=True, stdout='{"ok": true, "valid": true}', stderr="")
    )

    result = runner.verify(
        public_key_pem="pem", message="deadbeef", signature_b64="c2ln"
    )

    assert result["valid"] is True


def test_verify_returns_valid_false_on_bad_signature() -> None:
    runner = _make_verify_runner(
        SimpleNamespace(success=True, stdout='{"ok": true, "valid": false}', stderr="")
    )

    result = runner.verify(
        public_key_pem="pem", message="deadbeef", signature_b64="c2ln"
    )

    assert result["valid"] is False


def test_verify_returns_valid_false_on_malformed_output() -> None:
    runner = _make_verify_runner(
        SimpleNamespace(success=False, stdout="", stderr="boom")
    )

    result = runner.verify(
        public_key_pem="pem", message="deadbeef", signature_b64="c2ln"
    )

    assert result["ok"] is False
    assert result["valid"] is False
    assert "boom" in result["error"]


def _locate_built_binary() -> Path | None:
    """Find the locally-built sdd-compile binary, if `make build-compiler` ran."""
    from providence_core.utils.environment import detect_repo_root

    try:
        repo_root = detect_repo_root()
    except RuntimeError:
        return None
    binary = repo_root / "tools" / "sdd-compile" / "bin" / "sdd-compile"
    return binary if binary.is_file() else None


@pytest.mark.skipif(
    _locate_built_binary() is None,
    reason="sdd-compile binary not built locally (run `make build-compiler`)",
)
def test_real_binary_executes_from_path_with_space_and_non_ascii(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """doc02 E2E criterion: execution must work from non-ASCII/space paths.

    Copies the real, locally-built sdd-compile binary into a directory whose
    name contains both a space and a non-ASCII character (simulating a user
    home directory like ``/home/José Álvarez/``), then resolves and runs it
    through the real, unmocked `CompilerRunner` -> `SafeProcessRunner` chain
    via `SDD_COMPILE_BIN` (the same env var a real standalone install would
    use to pin a specific binary). `SafeProcessRunner` uses list-form
    `subprocess.run(..., shell=False, ...)` (no shell involved), so this
    exercises the Go binary's own argv/file-path handling — the one part of
    the chain this test can't verify by reading Python source alone.
    """
    import shutil

    built_binary = _locate_built_binary()
    assert built_binary is not None  # guaranteed by skipif above

    weird_dir = tmp_path / "usuário José Álvarez ção"
    weird_dir.mkdir()
    copied_binary = weird_dir / "sdd-compile"
    shutil.copy(built_binary, copied_binary)
    copied_binary.chmod(copied_binary.stat().st_mode | stat.S_IXUSR)

    monkeypatch.setenv("SDD_COMPILE_BIN", str(copied_binary))
    runner = CompilerRunner()
    assert runner.resolution_rule == "env_override"

    version_output = runner.version()
    assert version_output.strip()
