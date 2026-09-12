"""Unit tests for ProcessAuthorizer security validation and SafeProcessRunner integration."""

from __future__ import annotations

import contextlib
from unittest.mock import MagicMock, patch

import pytest

from providence_core.utils._process_auth import ProcessAuthorizer
from providence_core.utils.process import SafeProcessRunner

pytestmark = pytest.mark.unit


class TestValidatePythonArgs:
    """Tests for ProcessAuthorizer.validate_python_args security validation."""

    def test_allows_script_file_execution(self) -> None:
        """Script files should be allowed."""
        auth = ProcessAuthorizer()
        auth.validate_python_args("python3", ["python3", "script.py"])

    def test_allows_python_with_regular_arguments(self) -> None:
        """Regular Python arguments should be allowed."""
        auth = ProcessAuthorizer()
        auth.validate_python_args("python3", ["python3", "-u", "script.py"])

    def test_blocks_c_flag(self) -> None:
        """The -c flag (inline code execution) should be blocked."""
        auth = ProcessAuthorizer()
        with pytest.raises(ValueError, match="not permitted"):
            auth.validate_python_args("python3", ["python3", "-c", "print('test')"])

    def test_allows_m_flag(self) -> None:
        """The -m flag (module execution) is allowed by policy."""
        auth = ProcessAuthorizer()
        auth.validate_python_args("python3", ["python3", "-m", "http.server"])

    def test_skips_validation_for_non_python(self) -> None:
        """Non-Python binaries should skip validation."""
        auth = ProcessAuthorizer()
        auth.validate_python_args("git", ["git", "-c", "user.name=test"])

    def test_ignores_python_in_script_path(self) -> None:
        """Python in script paths should be ignored."""
        auth = ProcessAuthorizer()
        auth.validate_python_args("python3", ["python3", "/path/to/python-script.py"])

    def test_detects_c_flag_at_any_position(self) -> None:
        """Should detect -c flag even with other arguments."""
        auth = ProcessAuthorizer()
        with pytest.raises(ValueError, match="not permitted"):
            auth.validate_python_args("python3", ["python3", "-u", "-c", "code"])

    def test_allows_m_flag_at_any_position(self) -> None:
        """Should allow -m flag even with other arguments."""
        auth = ProcessAuthorizer()
        auth.validate_python_args("python3", ["python3", "-u", "-m", "module"])

    def test_error_message_mentions_script_files(self) -> None:
        """Error message should guide users to use script files."""
        auth = ProcessAuthorizer()
        with pytest.raises(ValueError, match="approved module execution pattern"):
            auth.validate_python_args("python3", ["python3", "-c", "pass"])

    def test_allows_bandit_config_flag_with_module_execution(self) -> None:
        """Bandit config via -c should be allowed only with python -m bandit."""
        auth = ProcessAuthorizer()
        auth.validate_python_args(
            "python3", ["python3", "-m", "bandit", "-r", "packages/", "-c", ".bandit"]
        )

    def test_blocks_bandit_c_without_value(self) -> None:
        """Bandit -c requires a non-empty config file argument."""
        auth = ProcessAuthorizer()
        with pytest.raises(ValueError, match="non-empty config file"):
            auth.validate_python_args("python3", ["python3", "-m", "bandit", "-c"])

    def test_blocks_c_for_non_bandit_module(self) -> None:
        """-c remains blocked for other python -m modules."""
        auth = ProcessAuthorizer()
        with pytest.raises(ValueError, match="not permitted"):
            auth.validate_python_args(
                "python3", ["python3", "-m", "http.server", "-c", "cfg.toml"]
            )


class TestSafeProcessRunnerIntegration:
    """Integration tests for SafeProcessRunner with validation."""

    def test_run_method_calls_validation(self) -> None:
        """The run() method should validate Python args."""
        runner = SafeProcessRunner()
        with pytest.raises(ValueError, match="not permitted"):
            runner.run(["python3", "-c", "print('test')"])

    def test_run_interactive_calls_validation(self) -> None:
        """The run_interactive() method should validate Python args."""
        runner = SafeProcessRunner()
        with pytest.raises(ValueError, match="not permitted"):
            runner.run_interactive(["python3", "-c", "print('test')"])

    def test_validates_python_binary(self) -> None:
        """Should validate both python and python3."""
        runner = SafeProcessRunner()
        with pytest.raises(ValueError, match="not permitted"):
            runner.run(["python", "-c", "import os"])

    @patch("subprocess.run")
    def test_authorized_script_execution(self, mock_run: MagicMock) -> None:
        """Authorized script execution should proceed."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="", text=True)
        runner = SafeProcessRunner()

        with contextlib.suppress(FileNotFoundError):
            runner.run(["python3", "/path/to/script.py"])

    @patch("subprocess.run")
    def test_run_allows_bandit_module_with_config_file(
        self, mock_run: MagicMock
    ) -> None:
        """python -m bandit ... -c <file> should pass authorization."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="", text=True)
        runner = SafeProcessRunner()
        with contextlib.suppress(FileNotFoundError):
            runner.run(["python3", "-m", "bandit", "-r", "packages/", "-c", ".bandit"])

    def test_blocks_arbitrary_code_execution_attempts(self) -> None:
        """Should block attempts to execute arbitrary code."""
        runner = SafeProcessRunner()
        malicious_commands = [
            ["python3", "-c", "import os; os.system('bash')"],
            ["python3", "-c", "__import__('os').system('whoami')"],
            ["python", "-c", "eval('malicious')"],
        ]
        for cmd in malicious_commands:
            with pytest.raises(ValueError, match="not permitted"):
                runner.run(cmd)
