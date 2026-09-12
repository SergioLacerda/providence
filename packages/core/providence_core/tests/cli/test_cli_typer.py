"""Tests for SDD CLI (Phase 6)."""

import builtins
import importlib
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

_agent_seeds_mod = importlib.import_module("providence_cli.generators.agent_seeds")
generate_agent_seeds = _agent_seeds_mod.generate_agent_seeds
generate_agent_instruction_files = _agent_seeds_mod.generate_agent_instruction_files

_main_mod = importlib.import_module("providence_cli.main")
app = _main_mod.app

runner = CliRunner()


class TestCLIMain:
    """Test main CLI entry point."""

    def test_help_command(self) -> None:
        """Test that --help displays usage information."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "SDD" in result.stdout or "governance" in result.stdout

    def test_version_command(self) -> None:
        """Test version command displays version."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        # Resolved dynamically via importlib.metadata (see
        # providence_cli/commands/version.py) — assert the label and a non-empty
        # value rather than a specific version, which would go stale exactly
        # like the hardcoded "1.0.0" this replaced.
        assert result.stdout.startswith("SDD Version: ")
        assert result.stdout.strip() != "SDD Version:"

    def test_version_flag(self) -> None:
        """Test --version flag on the root command prints a version and exits."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert result.stdout.strip() != ""

    def test_version_help(self) -> None:
        """Test version command help."""
        result = runner.invoke(app, ["version", "--help"])
        assert result.exit_code == 0

    def test_governance_help_without_workspace(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Governance help should work even if no workspace profile can be resolved."""
        from providence_core.utils.environment import WorkspaceNotInitializedError

        monkeypatch.setattr(
            "providence_core.utils.environment.resolve_profile",
            lambda override=None: (_ for _ in ()).throw(
                WorkspaceNotInitializedError(Path("."))
            ),
        )
        result = runner.invoke(app, ["governance", "--help"])
        assert result.exit_code == 0

    def test_test_help_without_workspace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test command help should work even if no workspace profile can be resolved."""
        from providence_core.utils.environment import WorkspaceNotInitializedError

        monkeypatch.setattr(
            "providence_core.utils.environment.resolve_profile",
            lambda override=None: (_ for _ in ()).throw(
                WorkspaceNotInitializedError(Path("."))
            ),
        )
        result = runner.invoke(app, ["test", "--help"])
        assert result.exit_code == 0

    def test_init_runs_without_existing_workspace(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Init must bootstrap clean directories without requiring .providence/profile."""
        # A real ancestor of the isolated cwd (e.g. a cached ~/.providence/bin
        # compiler download) could otherwise trip the nested-workspace guard,
        # since it walks all the way up to the filesystem root.
        monkeypatch.setattr(Path, "parents", property(lambda self: ()))
        with runner.isolated_filesystem():
            result = runner.invoke(app, ["init", "--type", "master", "--force"])
            assert result.exit_code == 0, result.output
            assert "Workspace initialized" in result.output


class TestCLILazyLoading:
    """Test lazy-loading behavior for command modules."""

    def test_help_works_when_optional_command_is_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Global help should still render when one command module cannot import."""

        real_import_module = importlib.import_module

        def fake_import_module(name: str, package: str | None = None) -> Any:
            if name == "providence_cli.commands.doctor":
                raise ModuleNotFoundError("No module named 'providence_integration'")
            return real_import_module(name, package)

        monkeypatch.setattr(
            "providence_cli._command_group.importlib.import_module", fake_import_module
        )

        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "doctor" in result.stdout

    def test_unavailable_command_fails_with_actionable_message(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Unavailable lazy command should fail with guidance instead of traceback."""

        real_import_module = importlib.import_module

        def fake_import_module(name: str, package: str | None = None) -> Any:
            if name == "providence_cli.commands.doctor":
                raise ModuleNotFoundError("No module named 'providence_integration'")
            return real_import_module(name, package)

        monkeypatch.setattr(
            "providence_cli._command_group.importlib.import_module", fake_import_module
        )

        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 1
        assert "unavailable" in result.output.lower()
        assert "providence setup run" in result.output

    def test_doctor_default_fails_gracefully_when_runtime_dependency_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`providence doctor` should print actionable guidance when runtime dependency is absent."""

        real_import = builtins.__import__

        def fake_import(
            name: str,
            globals_arg: dict[str, Any] | None = None,
            locals_arg: dict[str, Any] | None = None,
            fromlist: tuple[str, ...] = (),
            level: int = 0,
        ) -> Any:
            if name.startswith("providence_integration"):
                raise ModuleNotFoundError("No module named 'providence_integration'")
            return real_import(name, globals_arg, locals_arg, fromlist, level)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        result = runner.invoke(app, ["doctor", "run"])
        assert result.exit_code == 1
        assert "unavailable" in result.output.lower()
        assert "providence setup run" in result.output


class TestGovernanceCommands:
    """Test governance command group."""

    def test_governance_help(self) -> None:
        """Test governance command group help."""
        result = runner.invoke(app, ["governance", "--help"])
        assert result.exit_code == 0
        assert "load" in result.stdout
        assert "validate" in result.stdout
        assert "generate" in result.stdout

    def test_governance_base_lists_commands(self) -> None:
        """Bare governance command should show helper output without traceback."""
        result = runner.invoke(app, ["governance"])
        assert result.exit_code == 0
        assert "Governance commands:" in result.stdout
        assert "validate" in result.stdout
        assert "Traceback" not in result.output

    def test_governance_list_option_lists_commands(self) -> None:
        """Governance --list should show the same helper command list."""
        result = runner.invoke(app, ["governance", "--list"])
        assert result.exit_code == 0
        assert "Governance commands:" in result.stdout
        assert "hook status" in result.stdout
        assert "Traceback" not in result.output

    def test_governance_hook_base_lists_hook_commands(self) -> None:
        """Bare governance hook group should show helper output without traceback."""
        result = runner.invoke(app, ["governance", "hook"])
        assert result.exit_code == 0
        assert "Governance hook commands:" in result.stdout
        assert "status" in result.stdout
        assert "Traceback" not in result.output

    def test_load_help(self) -> None:
        """Test load command help."""
        result = runner.invoke(app, ["governance", "load", "--help"])
        assert result.exit_code == 0
        assert "governance" in result.stdout.lower()

    def test_validate_help(self) -> None:
        """Test validate command help."""
        result = runner.invoke(app, ["governance", "validate", "--help"])
        assert result.exit_code == 0

    def test_generate_help(self) -> None:
        """Test generate command help."""
        result = runner.invoke(app, ["governance", "generate", "--help"])
        assert result.exit_code == 0


class TestCommandBaseHelpers:
    """Regression coverage for command groups invoked without subcommands."""

    @pytest.mark.parametrize(
        ("command", "title", "expected_child"),
        [
            ("bootstrap", "Bootstrap commands:", "run"),
            ("docs", "Documentation commands:", "deploy"),
            ("lint", "Lint commands:", "spec"),
            ("metrics", "Metrics commands:", "summary"),
            ("plugin", "Plugin commands:", "validate"),
            ("release", "Release commands:", "build"),
            ("runtime", "Runtime commands:", "status"),
            ("scaffold", "Scaffold commands:", "skill"),
            ("setup", "Setup commands:", "run"),
            ("skills", "Skills commands:", "describe"),
            ("test", "Test commands:", "ci-validate"),
            ("tools", "Tools commands:", "run"),
            ("doctor", "Doctor commands:", "run"),
            ("audit", "Audit commands:", "summary"),
            ("telemetry", "Telemetry commands:", "status"),
            ("analysis", "Analysis commands:", "list"),
        ],
    )
    def test_base_command_lists_children(
        self, command: str, title: str, expected_child: str
    ) -> None:
        """Bare command groups should show helper output without traceback."""
        result = runner.invoke(app, [command])
        assert result.exit_code == 0, result.output
        assert title in result.stdout
        assert expected_child in result.stdout
        assert "Traceback" not in result.output

    @pytest.mark.parametrize(
        ("command", "title", "expected_child"),
        [
            ("bootstrap", "Bootstrap commands:", "run"),
            ("docs", "Documentation commands:", "deploy"),
            ("lint", "Lint commands:", "run"),
            ("metrics", "Metrics commands:", "serve"),
            ("plugin", "Plugin commands:", "list"),
            ("release", "Release commands:", "build"),
            ("runtime", "Runtime commands:", "status"),
            ("scaffold", "Scaffold commands:", "command"),
            ("setup", "Setup commands:", "run"),
            ("skills", "Skills commands:", "export"),
            ("test", "Test commands:", "review-golden"),
            ("tools", "Tools commands:", "list"),
            ("doctor", "Doctor commands:", "run"),
            ("audit", "Audit commands:", "compliance-pack"),
            ("telemetry", "Telemetry commands:", "query"),
            ("analysis", "Analysis commands:", "clean"),
            ("init", "Init commands:", "--default"),
            ("install", "Install commands:", "--wizard"),
            ("version", "Version commands:", "show"),
            ("ask", "Ask commands:", "<query>"),
            ("organize", "Organize commands:", "<query>"),
        ],
    )
    def test_list_option_lists_children(
        self, command: str, title: str, expected_child: str
    ) -> None:
        """--list should expose the same helper contract for protected groups."""
        result = runner.invoke(app, [command, "--list"])
        assert result.exit_code == 0, result.output
        assert title in result.stdout
        assert expected_child in result.stdout
        assert "Traceback" not in result.output

    @pytest.mark.parametrize("command", ["ask", "organize"])
    def test_argument_required_commands_fail_without_traceback(
        self, command: str
    ) -> None:
        """Argument-required commands should fail as usage errors, not tracebacks."""
        result = runner.invoke(app, [command])
        assert result.exit_code != 0
        assert "Traceback" not in result.output

    def test_wizard_list_shows_usage(self) -> None:
        """`wizard --list` uses the standalone usage helper, not the group listing."""
        result = runner.invoke(app, ["wizard", "--list"])
        assert result.exit_code == 0, result.output
        assert "Wizard usage:" in result.stdout
        assert "--from-file" in result.stdout
        assert "Traceback" not in result.output

    def test_wizard_bare_invocation_runs_installer(self) -> None:
        """`wizard` with no args installs directly instead of listing children.

        Without an interactive terminal or `--from-file`, the run aborts with a
        clear error rather than a traceback — the new single-command contract.
        """
        result = runner.invoke(app, ["wizard"])
        assert result.exit_code != 0
        assert "Traceback" not in result.output


class TestLoadCommand:
    """Test load command functionality."""

    def test_load_with_valid_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test load with valid wizard path."""
        monkeypatch.setattr(
            "providence_cli.utils.loader.validate_governance_path", lambda x: True
        )
        monkeypatch.setattr(
            "providence_cli.utils.loader.load_governance_config",
            lambda x: {"items": []},
        )
        monkeypatch.setattr(
            "providence_cli.utils.loader.get_governance_summary",
            lambda x, config=None: {},
        )
        result = runner.invoke(app, ["governance", "load", "--path", "runtime"])
        assert result.exit_code == 0

    def test_load_with_invalid_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test load with invalid path."""
        monkeypatch.setattr(
            "providence_cli.utils.loader.validate_governance_path", lambda x: False
        )
        result = runner.invoke(
            app, ["governance", "load", "--path", "/nonexistent/path"]
        )
        assert result.exit_code == 1
        assert "Invalid" in result.stdout or "not found" in result.stdout.lower()


class TestValidateCommand:
    """Test validate command functionality."""

    def test_validate_with_valid_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test validate with valid wizard path."""
        monkeypatch.setattr(
            "providence_cli.utils.loader.validate_governance_path", lambda x: True
        )
        monkeypatch.setattr(
            "providence_cli.utils.loader.load_governance_config",
            lambda x: {"items": []},
        )
        monkeypatch.setattr(
            "providence_cli.services.governance_config_reader.check_files_accessible",
            lambda x: True,
        )
        monkeypatch.setattr(
            "providence_cli.services.governance_config_reader.check_fingerprints_valid",
            lambda x: True,
        )
        monkeypatch.setattr(
            "providence_cli.services.governance_config_reader.check_no_conflicts",
            lambda x: True,
        )
        monkeypatch.setattr(
            "providence_cli.services.governance_config_reader.check_root_seed_drift",
            lambda x: (True, "no root-seed drift detected"),
        )
        monkeypatch.setattr(
            "providence_cli.services.governance_artifact_handlers.check_artifact_consistency",
            lambda x: (True, ""),
        )
        monkeypatch.setattr(
            "providence_core.governance.handshake.AgentHandshakeProtocol",
            type("MockAHP", (), {"is_handshake_valid": lambda self: True}),
        )
        monkeypatch.setattr(
            "providence_cli.services.runtime_preflight.run_runtime_preflight",
            lambda x: type(
                "MockPreflight", (), {"passed": True, "reason": "", "details": {}}
            )(),
        )
        result = runner.invoke(
            app,
            [
                "governance",
                "validate",
                "--path",
                ".providence/compiled",
                "--signature-mode",
                "off",
            ],
        )
        assert result.exit_code == 0

    def test_validate_with_invalid_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test validate with invalid path."""
        monkeypatch.setattr(
            "providence_cli.utils.loader.validate_governance_path", lambda x: False
        )
        result = runner.invoke(
            app,
            [
                "governance",
                "validate",
                "--path",
                "/nonexistent/path",
                "--signature-mode",
                "off",
            ],
        )
        assert result.exit_code == 1


class TestGenerateCommand:
    """Test generate command functionality."""

    def test_generate_with_valid_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test generate with valid wizard path."""
        monkeypatch.setattr(
            "providence_cli.services.governance_generate_handlers.validate_governance_path",
            lambda x: True,
        )
        monkeypatch.setattr(
            "providence_cli.services.governance_generate_handlers.load_governance_config",
            lambda x: {"items": [{"id": "M001", "type": "MANDATE", "title": "Test"}]},
        )
        monkeypatch.setattr(
            "providence_cli.services.governance_generate_handlers.generate_seeds",
            lambda output_dir, config: (
                [],
                __import__("pathlib").Path(output_dir) / ".vscode" / "agents",
            ),
        )
        monkeypatch.setattr(
            "providence_cli.services.governance_generate_handlers.run_generate_phases",
            lambda output_base, config: (False, False, False),
        )
        monkeypatch.setattr(
            "providence_cli.services.governance_generate_handlers.write_instruction_files_safe",
            lambda *a, **k: None,
        )
        monkeypatch.setattr(
            "providence_cli.services.governance_generate_handlers.write_prompt_commands_safe",
            lambda *a, **k: None,
        )
        monkeypatch.setattr(
            "providence_cli.services.governance_generate_handlers.generate_adapters_safe",
            lambda *a, **k: None,
        )
        result = runner.invoke(app, ["governance", "generate", "--path", "runtime"])
        assert result.exit_code == 0

    def test_generate_with_invalid_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test generate with invalid path."""
        monkeypatch.setattr(
            "providence_cli.services.governance_generate_handlers.validate_governance_path",
            lambda x: False,
        )
        result = runner.invoke(
            app, ["governance", "generate", "--path", "/nonexistent/path"]
        )
        assert result.exit_code == 1


class TestLoaderIntegration:
    """Test loader integration with governance."""

    def test_loader_module_exists(self) -> None:
        """Test that loader module imports correctly."""
        loader = importlib.import_module("providence_cli.utils.loader")

        assert hasattr(loader, "load_governance_config")
        assert hasattr(loader, "validate_governance_path")
        assert hasattr(loader, "get_governance_summary")

    @pytest.mark.skip(
        reason="runtime is not a valid governance path without actual artifacts"
    )
    def test_loader_imports_runtime(self) -> None:
        """Test that runtime governance path is valid for loader."""
        validate_governance_path = importlib.import_module(
            "providence_cli.utils.loader"
        ).validate_governance_path

        assert validate_governance_path("runtime")

    def test_loader_accepts_final_template_providence_compiled_layout(
        self, tmp_path: Path
    ) -> None:
        """Test that final-template/.providence/compiled resolves as valid governance path."""
        validate_governance_path = importlib.import_module(
            "providence_cli.utils.loader"
        ).validate_governance_path

        final_template = tmp_path / "final-template"
        compiled_dir = final_template / ".providence" / "compiled"
        compiled_dir.mkdir(parents=True)

        (compiled_dir / "governance-core.compiled.msgpack").write_bytes(b"core")
        (compiled_dir / "governance-client-template.compiled.msgpack").write_bytes(
            b"client"
        )
        (compiled_dir / "metadata-core.json").write_text("{}", encoding="utf-8")
        (compiled_dir / "metadata-client-template.json").write_text(
            "{}", encoding="utf-8"
        )

        assert validate_governance_path(str(final_template))


class TestAgentSeedsGenerator:
    """Test agent seeds generation."""

    def test_generate_agent_seeds_structure(self) -> None:
        """Test that agent seeds generator creates correct structure."""

        # Create mock config
        mock_config = {
            "core_fingerprint": "abc123",
            "client_fingerprint": "def456",
            "items": [],
        }

        # Test with temporary directory
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            results = generate_agent_seeds(Path(tmpdir), mock_config)
            assert len(results) == 6
            assert all(r[2] == "Generated" for r in results)
            generated_names = {r[0] for r in results}
            assert generated_names == {
                "Cursor IDE",
                "GitHub Copilot",
                "Generic AI",
                "Claude",
                "Gemini",
                "Antigravity",
            }

    def test_agent_seeds_content_cursor(self) -> None:
        """Test that Cursor seed contains required content."""
        _generate_cursor_seed = _agent_seeds_mod._generate_cursor_seed

        mock_config = {"core_fingerprint": "test123", "items": []}
        content = _generate_cursor_seed(mock_config, [], [])
        assert "Cursor" in content or "cursor" in content.lower()

    def test_agent_seeds_content_copilot(self) -> None:
        """Test that Copilot seed contains required content."""
        _generate_copilot_seed = _agent_seeds_mod._generate_copilot_seed

        mock_config = {"core_fingerprint": "test123", "items": []}
        content = _generate_copilot_seed(mock_config, [], [])
        assert "Copilot" in content or "copilot" in content.lower()

    def test_agent_seeds_content_generic(self) -> None:
        """Test that Generic seed contains required content."""
        _generate_generic_seed = _agent_seeds_mod._generate_generic_seed

        mock_config = {"core_fingerprint": "test123", "items": []}
        content = _generate_generic_seed(mock_config, [], [])
        assert "Architecture" in content or "Governance" in content

    def test_agent_seeds_content_claude(self) -> None:
        """Test that Claude seed contains required content."""
        _generate_claude_seed = _agent_seeds_mod._generate_claude_seed

        mock_config = {"core_fingerprint": "test123", "items": []}
        content = _generate_claude_seed(mock_config, [], [])
        assert "Claude" in content

    def test_instruction_files_written_for_all_supported_targets(
        self, tmp_path: Path
    ) -> None:
        """Instruction files are emitted for Copilot, VS Code, Claude, Gemini, and Antigravity."""
        mock_config = {
            "core_fingerprint": "abc123def456",
            "client_fingerprint": "fed654cba321",
            "items": [
                {
                    "id": "D1",
                    "type": "MANDATE",
                    "title": "Rule",
                    "description": "Must follow",
                }
            ],
        }

        results = generate_agent_instruction_files(tmp_path, mock_config)
        assert [label for label, _ in results] == [
            "GitHub Copilot",
            "VS Code",
            "Claude",
            "Gemini",
            "Cursor",
            "Antigravity",
        ]
        for _, path in results:
            assert path.exists()
            assert "Validation" in path.read_text(encoding="utf-8")


class TestCommandExecutions:
    """Test command execution scenarios."""

    def test_load_execution(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test load command execution."""
        monkeypatch.setattr(
            "providence_cli.utils.loader.validate_governance_path", lambda x: True
        )
        monkeypatch.setattr(
            "providence_cli.utils.loader.load_governance_config",
            lambda x: {"items": []},
        )
        monkeypatch.setattr(
            "providence_cli.utils.loader.get_governance_summary",
            lambda x, config=None: {},
        )
        result = runner.invoke(app, ["governance", "load"])
        assert result.exit_code == 0

    def test_validate_execution(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test validate command execution."""
        monkeypatch.setattr(
            "providence_cli.utils.loader.validate_governance_path", lambda x: True
        )
        monkeypatch.setattr(
            "providence_cli.utils.loader.load_governance_config",
            lambda x: {"items": []},
        )
        monkeypatch.setattr(
            "providence_cli.services.governance_config_reader.check_files_accessible",
            lambda x: True,
        )
        monkeypatch.setattr(
            "providence_cli.services.governance_config_reader.check_fingerprints_valid",
            lambda x: True,
        )
        monkeypatch.setattr(
            "providence_cli.services.governance_config_reader.check_no_conflicts",
            lambda x: True,
        )
        monkeypatch.setattr(
            "providence_cli.services.governance_config_reader.check_root_seed_drift",
            lambda x: (True, "no root-seed drift detected"),
        )
        monkeypatch.setattr(
            "providence_cli.services.governance_artifact_handlers.check_artifact_consistency",
            lambda x: (True, ""),
        )
        monkeypatch.setattr(
            "providence_core.governance.handshake.AgentHandshakeProtocol",
            type("MockAHP", (), {"is_handshake_valid": lambda self: True}),
        )
        monkeypatch.setattr(
            "providence_cli.services.runtime_preflight.run_runtime_preflight",
            lambda x: type(
                "MockPreflight", (), {"passed": True, "reason": "", "details": {}}
            )(),
        )
        result = runner.invoke(
            app, ["governance", "validate", "--signature-mode", "off"]
        )
        assert result.exit_code == 0

    def test_generate_execution(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test generate command execution."""
        monkeypatch.setattr(
            "providence_cli.services.governance_generate_handlers.validate_governance_path",
            lambda x: True,
        )
        monkeypatch.setattr(
            "providence_cli.services.governance_generate_handlers.load_governance_config",
            lambda x: {"items": [{"id": "D1", "type": "MANDATE", "title": "Rule"}]},
        )
        monkeypatch.setattr(
            "providence_cli.services.governance_generate_handlers.generate_seeds",
            lambda output_dir, config: (
                [],
                __import__("pathlib").Path(output_dir) / ".vscode" / "agents",
            ),
        )
        monkeypatch.setattr(
            "providence_cli.services.governance_generate_handlers.run_generate_phases",
            lambda output_base, config: (False, False, False),
        )
        monkeypatch.setattr(
            "providence_cli.services.governance_generate_handlers.write_instruction_files_safe",
            lambda *a, **k: None,
        )
        monkeypatch.setattr(
            "providence_cli.services.governance_generate_handlers.write_prompt_commands_safe",
            lambda *a, **k: None,
        )
        monkeypatch.setattr(
            "providence_cli.services.governance_generate_handlers.generate_adapters_safe",
            lambda *a, **k: None,
        )
        result = runner.invoke(app, ["governance", "generate"])
        assert result.exit_code == 0

    def test_generate_fails_when_items_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """generate must fail when compiled governance has no items."""
        monkeypatch.setattr(
            "providence_cli.services.governance_generate_handlers.validate_governance_path",
            lambda x: True,
        )
        monkeypatch.setattr(
            "providence_cli.services.governance_generate_handlers.load_governance_config",
            lambda x: {"items": []},
        )
        result = runner.invoke(app, ["governance", "generate"])
        assert result.exit_code == 1
        assert "No governance items loaded" in result.output

    def test_invalid_subcommand(self) -> None:
        """Test invalid subcommand."""
        result = runner.invoke(app, ["governance", "invalid"])
        assert result.exit_code != 0


class TestPathErrorHandling:
    """Test error handling for path-related issues."""

    def test_missing_governance_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test handling of missing governance path."""
        monkeypatch.setattr(
            "providence_cli.utils.loader.validate_governance_path", lambda x: False
        )
        result = runner.invoke(
            app, ["governance", "load", "--path", "path/that/does/not/exist"]
        )
        assert result.exit_code == 1


class TestCiValidateCommand:
    """Tests for `providence test ci-validate` command."""

    def test_ci_validate_help(self) -> None:
        """ci-validate exposes --help without error."""
        result = runner.invoke(app, ["test", "ci-validate", "--help"])
        assert result.exit_code == 0
        assert (
            "ci-validate" in result.output
            or "Import checks" in result.output
            or "Preflight" in result.output
            or "temporarily unavailable" in result.output
        )

    def test_ci_validate_import_checks_pass(self) -> None:
        """ci-validate runs import checks and exits 0 when core modules present."""
        result = runner.invoke(
            app, ["test", "ci-validate", "--no-health", "--no-governance", "--no-tests"]
        )
        # yaml, typer, rich are always present in the test environment
        assert "PASS: yaml" in result.output
        assert "PASS: typer" in result.output
        assert "PASS: rich" in result.output

    def test_ci_validate_exit_0_on_success(self) -> None:
        """ci-validate exits 0 when all available modules are importable."""
        result = runner.invoke(
            app, ["test", "ci-validate", "--no-health", "--no-governance", "--no-tests"]
        )
        # May fail on msgpack/sdd_* in minimal env, but exit code reflects actual state
        if "FAIL:" not in result.output:
            assert result.exit_code == 0

    def test_ci_validate_exit_1_on_failure(
        self, monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """ci-validate exits 1 when an import check fails."""
        real_import = builtins.__import__

        def patched_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "msgpack":
                raise ImportError("mocked")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", patched_import)
        result = runner.invoke(
            app, ["test", "ci-validate", "--no-health", "--no-governance", "--no-tests"]
        )
        assert result.exit_code == 1
        assert "FAIL: msgpack" in result.output
