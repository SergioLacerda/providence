"""GuidelineSeeds  prompt command and AI instruction seed generation."""

from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from .base_generator import BaseSeedlingGenerator


class GuidelineSeeds:
    """Generate prompt command files and deprecated AI instruction stubs."""

    def __init__(self, ctx: BaseSeedlingGenerator) -> None:
        self._ctx = ctx
        self.prompt_commands_mode: str = "unknown"
        self.prompt_commands_outputs: list[str] = []

    def generate_prompt_commands(self) -> bool:
        """Generate CLI prompt/command files for all supported AI tools."""
        try:
            module = import_module("providence_cli.generators.agent_seeds")
            module_any = cast(Any, module)
            generator = cast(
                Callable[[Path, dict[str, Any]], dict[str, Path]],
                module_any.generate_agent_prompt_commands,
            )
            results = generator(self._ctx.output_base, self._ctx.config)
            output_paths = self._normalize_prompt_command_outputs(results)

            if not output_paths:
                self._ctx.log(
                    "  Prompt command generator returned no outputs, using fallback"
                )
                return self._generate_minimal_prompt_commands()

            count = len(output_paths)
            self.prompt_commands_mode = "full"
            self.prompt_commands_outputs = sorted(
                str(Path(path).relative_to(self._ctx.output_base))
                for path in output_paths
            )
            self._ctx.log(f" Generated {count} prompt command files")
            return True
        except ImportError:
            self._ctx.log(
                "  providence_cli not available, generating minimal prompt commands"
            )
            return self._generate_minimal_prompt_commands()
        except Exception as e:
            self._ctx.log(
                f"  Failed to generate prompt commands via providence_cli ({e}), using fallback"
            )
            return self._generate_minimal_prompt_commands()

    def _normalize_prompt_command_outputs(self, results: Any) -> list[Path]:
        output_paths: list[Path] = []
        raw_items: list[Any]
        if isinstance(results, dict):
            raw_items = list(results.values())
        elif isinstance(results, list):
            raw_items = list(results)
        else:
            return output_paths
        for item in raw_items:
            path_candidate: Any = item
            if isinstance(item, tuple) and len(item) >= 2:
                path_candidate = item[1]
            if isinstance(path_candidate, Path):
                output_paths.append(path_candidate)
            elif isinstance(path_candidate, str):
                output_paths.append(Path(path_candidate))
        return output_paths

    def _generate_minimal_prompt_commands(self) -> bool:
        """Fallback: generate minimal prompt command files without providence_cli dependency."""
        try:
            _commands_table = (
                "| Task | Command |\n"
                "|------|---------|\n"
                "| Run tests | `providence test run` |\n"
                "| Lint | `providence lint run` |\n"
                "| Validate governance | `providence governance validate` |\n"
                "| Compile governance | `providence governance compile` |\n"
                "| Runtime status | `providence runtime status` |\n"
                '| Query context | `providence ask --full "<question>"` |\n'
                "| Diagnostics | `providence doctor run --mode real` |\n"
                "| Generate seeds | `providence governance generate` |\n"
            )
            cursor_dir = self._ctx.output_base / ".cursor" / "rules"
            cursor_dir.mkdir(parents=True, exist_ok=True)
            (cursor_dir / "sdd-commands.mdc").write_text(
                "---\ndescription: SDD CLI commands\nglobs: ['**/*']\nalwaysApply: false\n---\n\n"
                "# SDD CLI Commands\n\n" + _commands_table,
                encoding="utf-8",
            )
            gemini_dir = self._ctx.output_base / ".gemini"
            gemini_dir.mkdir(parents=True, exist_ok=True)
            (gemini_dir / "commands.md").write_text(
                "# SDD CLI Commands for Gemini\n\n" + _commands_table,
                encoding="utf-8",
            )
            self.prompt_commands_mode = "fallback"
            self.prompt_commands_outputs = [
                ".cursor/rules/sdd-commands.mdc",
                ".gemini/commands.md",
            ]
            return True
        except Exception as e:
            self.prompt_commands_mode = "error"
            self._ctx._emit(f"   Failed to generate minimal prompt commands: {e}")
            return False

    def generate_ai_instructions(self) -> bool:
        """Deprecated hook retained for API stability."""
        self._ctx.log(" Skipping deprecated legacy bootstrap instructions generation.")
        return True

    def generate_openai_instructions(self) -> bool:
        """Deprecated hook retained for API stability."""
        self._ctx.log(" Skipping deprecated legacy OpenAI instructions generation.")
        return True
