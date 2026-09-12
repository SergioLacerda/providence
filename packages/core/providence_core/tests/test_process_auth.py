"""Tests for ProcessAuthorizer: argument validation and binary allow-listing."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from providence_core.utils._process_auth import ProcessAuthorizer
from providence_core.utils.process import SafeProcessRunner

pytestmark = pytest.mark.unit


class TestProcessAuthorizerValidateArgs:
    """Tests for ProcessAuthorizer.validate_args."""

    def test_run_with_non_string_arg(self) -> None:
        """Non-string argument raises ValueError."""
        auth = ProcessAuthorizer()
        with pytest.raises(ValueError, match="must be a string"):
            auth.validate_args(["git", 123])  # type: ignore

    def test_run_with_null_byte_arg(self) -> None:
        """Null byte in arg raises ValueError."""
        auth = ProcessAuthorizer()
        with pytest.raises(ValueError, match="null byte"):
            auth.validate_args(["git", "arg\x00invalid"])

    def test_run_with_oversized_arg(self) -> None:
        """Arg > 65536 chars raises ValueError."""
        auth = ProcessAuthorizer()
        with pytest.raises(ValueError, match="exceeds maximum length"):
            auth.validate_args(["git", "x" * 65537])

    def test_empty_args_raises(self) -> None:
        """Empty args list raises ValueError."""
        auth = ProcessAuthorizer()
        with pytest.raises(ValueError, match="cannot be empty"):
            auth.validate_args([])


class TestProcessAuthorizerAuthorize:
    """Tests for ProcessAuthorizer.authorize."""

    def test_unauthorized_binary_raises(self) -> None:
        """Unauthorized binary raises ValueError."""
        auth = ProcessAuthorizer()
        with pytest.raises(ValueError, match="not authorized"):
            auth.authorize(["/nonexistent/binary/path", "arg"])

    def test_custom_authorized_binaries(self) -> None:
        """Custom allow-list restricts what is permitted."""
        auth = ProcessAuthorizer(authorized_binaries={"git"})
        with pytest.raises(ValueError, match="not authorized"):
            auth.authorize(["sdd", "ask"])

    def test_versioned_python_resolved(self) -> None:
        """python3.11 resolves to python3 for authorization."""
        auth = ProcessAuthorizer()
        # Should resolve to python3 and pass authorization
        binary = auth.resolve_binary_name("python3.11")
        assert binary == "python3"

    def test_windows_exe_suffix_resolved(self) -> None:
        """providence.exe resolves to providence so Windows installs are authorized."""
        auth = ProcessAuthorizer()
        assert auth.resolve_binary_name("providence.exe") == "providence"
        auth.authorize(["providence.exe", "governance", "generate"])

    def test_windows_bat_cmd_suffix_resolved(self) -> None:
        """uv.bat / uv.cmd resolve to uv for authorization."""
        auth = ProcessAuthorizer()
        assert auth.resolve_binary_name("uv.bat") == "uv"
        assert auth.resolve_binary_name("uv.cmd") == "uv"

    def test_make_task_binaries_are_authorized(self) -> None:
        """Make wrappers delegate to these governed toolchain binaries."""
        auth = ProcessAuthorizer()
        for binary in (
            "npm.cmd",
            "go.exe",
            "docker.exe",
            "bash.exe",
            "golangci-lint.exe",
        ):
            auth.authorize([binary, "--version"])
        # cmd.exe is only authorized for the Windows junction helper invocation.
        auth.authorize(["cmd.exe", "/c", "mklink", "/J", "link", "target"])

    def test_release_compiler_asset_names_resolve_to_sdd_compile(self) -> None:
        """Platform-suffixed release compiler assets remain governed compiler runs."""
        auth = ProcessAuthorizer()
        assert auth.resolve_binary_name("sdd-compile-linux-amd64") == "sdd-compile"
        assert auth.resolve_binary_name("sdd-compile-windows-amd64.exe") == (
            "sdd-compile"
        )
        auth.authorize(["sdd-compile-linux-amd64", "version"])
        auth.authorize(["sdd-compile-windows-amd64.exe", "version"])


class TestValidatePythonArgsCoverage:
    """Extended coverage for Python argument validation."""

    def test_python_script_with_multiple_options(self) -> None:
        """Should allow python with multiple legitimate options."""
        auth = ProcessAuthorizer()
        auth.validate_python_args(
            "python3",
            ["python3", "-u", "-W", "ignore", "script.py", "--arg", "value"],
        )

    def test_detect_c_flag_with_equals(self) -> None:
        """Current implementation requires exact '-c' match, not '-c='."""
        auth = ProcessAuthorizer()
        # -c=code format is not detected by exact match; it passes
        auth.validate_python_args("python3", ["python3", "-c=code"])

    def test_python_in_script_path_ignored(self) -> None:
        """Word 'python' in script path should not trigger validation error."""
        auth = ProcessAuthorizer()
        auth.validate_python_args(
            "python3", ["python3", "/path/to/run-python-tests.py"]
        )

    def test_m_flag_variations(self) -> None:
        """Should allow -m flag in various positions."""
        auth = ProcessAuthorizer()
        auth.validate_python_args("python3", ["python3", "-m", "json.tool"])
        auth.validate_python_args("python3", ["python3", "-u", "-m", "module"])

    def test_bandit_config_argument_rejects_inline_like_payload(self) -> None:
        """Bandit -c must look like a file path, not inline code payload."""
        auth = ProcessAuthorizer()
        with pytest.raises(ValueError, match="config file path"):
            auth.validate_python_args(
                "python3",
                ["python3", "-m", "bandit", "-r", "packages/", "-c", "print('x')"],
            )


class TestSafeProcessRunnerValidation:
    """Tests for process runner argument validation via run()."""

    def test_validate_python_args_called_for_python(self) -> None:
        """Validation should be triggered for python binary via run()."""
        runner = SafeProcessRunner()
        with pytest.raises(ValueError, match="not permitted"):
            runner.run(["python3", "-c", "print('test')"])

    def test_validate_both_python_and_python3(self) -> None:
        """Should validate both 'python' and 'python3' binaries."""
        runner = SafeProcessRunner()
        with pytest.raises(ValueError, match="not permitted"):
            runner.run(["python", "-c", "code"])
        with pytest.raises(ValueError, match="not permitted"):
            runner.run(["python3", "-c", "code"])

    def test_run_with_non_string_arg(self) -> None:
        """run() with non-string argument raises ValueError."""
        runner = SafeProcessRunner()
        with pytest.raises(ValueError, match="must be a string"):
            runner.run(["git", 123])  # type: ignore

    def test_run_with_null_byte_arg(self) -> None:
        """run() with null byte in arg raises ValueError."""
        runner = SafeProcessRunner()
        with pytest.raises(ValueError, match="null byte"):
            runner.run(["git", "arg\x00invalid"])

    def test_run_with_oversized_arg(self) -> None:
        """run() with arg > 65536 chars raises ValueError."""
        runner = SafeProcessRunner()
        with pytest.raises(ValueError, match="exceeds maximum length"):
            runner.run(["git", "x" * 65537])

    def test_run_interactive_empty_args(self) -> None:
        """run_interactive([]) raises ValueError."""
        runner = SafeProcessRunner()
        with pytest.raises(ValueError, match="cannot be empty"):
            runner.run_interactive([])

    def test_run_interactive_non_string_arg(self) -> None:
        """run_interactive() with non-string arg raises ValueError."""
        runner = SafeProcessRunner()
        with pytest.raises(ValueError, match="must be a string"):
            runner.run_interactive(["git", 123])  # type: ignore

    def test_run_interactive_null_byte_arg(self) -> None:
        """run_interactive() with null byte in arg raises ValueError."""
        runner = SafeProcessRunner()
        with pytest.raises(ValueError, match="null byte"):
            runner.run_interactive(["git", "arg\x00invalid"])

    def test_run_interactive_oversized_arg(self) -> None:
        """run_interactive() with arg > 65536 chars raises ValueError."""
        runner = SafeProcessRunner()
        with pytest.raises(ValueError, match="exceeds maximum length"):
            runner.run_interactive(["git", "x" * 65537])

    def test_run_interactive_unauthorized_binary(self) -> None:
        """run_interactive with unauthorized binary raises ValueError."""
        runner = SafeProcessRunner()
        with pytest.raises(ValueError, match="not authorized"):
            runner.run_interactive(["/nonexistent/binary/path", "script.sh"])


class TestProcessSecurityPatterns:
    """Tests for security patterns in process handling."""

    def test_no_shell_injection_via_args(self) -> None:
        """Arguments should not be interpreted as shell code."""
        runner = SafeProcessRunner()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            import contextlib

            with contextlib.suppress(FileNotFoundError, ValueError):
                runner.run(["git", "'; rm -rf /; echo '"])

    def test_python_arbitrary_import_blocked(self) -> None:
        """Should block -c flag attempts to import arbitrary modules."""
        runner = SafeProcessRunner()
        with pytest.raises(ValueError, match="not permitted"):
            runner.run(["python3", "-c", "__import__('os').system('cmd')"])

    def test_python_eval_blocked(self) -> None:
        """Should block -c flag attempts to eval code."""
        runner = SafeProcessRunner()
        with pytest.raises(ValueError, match="not permitted"):
            runner.run(["python3", "-c", "eval('dangerous_code')"])


class TestProcessRunnerErrorHandling:
    """Tests for error handling in process runner."""

    def test_unauthorized_binary_raises(self) -> None:
        """Should raise ValueError for unauthorized binary."""
        runner = SafeProcessRunner()
        with pytest.raises(ValueError, match="not authorized"):
            runner.run(["/nonexistent/binary/path", "arg"])

    def test_permission_denied_handling(self) -> None:
        """Should handle permission denied errors."""
        runner = SafeProcessRunner()
        with (
            patch("subprocess.run", side_effect=PermissionError("Permission denied")),
            pytest.raises(Exception, match="Could not execute process"),
        ):
            runner.run(["git", "status"])


class TestTelemetryAuthContract:
    """Telemetry contract tests related to authorization."""

    def test_telemetry_status_is_blocked_on_auth_error(self) -> None:
        mock_sink = MagicMock()
        runner = SafeProcessRunner(
            telemetry_sink=mock_sink, authorized_binaries={"git"}
        )

        with pytest.raises(ValueError, match="not authorized"):
            runner.run(["bash", "-lc", "echo hi"])

        status_values = [
            call.args[0].status for call in mock_sink.emit.call_args_list if call.args
        ]
        assert "blocked" in status_values
