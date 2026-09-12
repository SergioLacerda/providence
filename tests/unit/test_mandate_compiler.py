"""Unit tests for providence_wizard.orchestration.mandate_compiler.MandateCompiler."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.unit


MANDATE_SPEC_SAMPLE = """
mandate M001 {
  type: HARD
  title: "First Mandate"
  description: "Description of mandate one"
  criticality: OBRIGATÓRIO
}

mandate M002 {
  type: SOFT
  title: "Second Mandate"
  description: "Description of mandate two"
  criticality: RECOMENDADO
}
"""

GUIDELINES_DSL_SAMPLE = """
guideline G001 {
  type: SOFT
  title: "First Guideline"
  description: "Description of guideline one"
  category: quality
}

guideline G002 {
  type: SOFT
  title: "Second Guideline"
  description: "Description of guideline two"
  category: security
}
"""


class TestParseMandateSpec:
    def test_parses_count(self) -> None:
        from providence_wizard.orchestration.mandate_compiler import MandateCompiler

        compiler = MandateCompiler()
        count, mandates = compiler.parse_mandate_spec(MANDATE_SPEC_SAMPLE)
        assert count == 2

    def test_parses_mandate_ids(self) -> None:
        from providence_wizard.orchestration.mandate_compiler import MandateCompiler

        compiler = MandateCompiler()
        _, mandates = compiler.parse_mandate_spec(MANDATE_SPEC_SAMPLE)
        ids = [m["id"] for m in mandates]
        assert "M001" in ids
        assert "M002" in ids

    def test_parses_mandate_fields(self) -> None:
        from providence_wizard.orchestration.mandate_compiler import MandateCompiler

        compiler = MandateCompiler()
        _, mandates = compiler.parse_mandate_spec(MANDATE_SPEC_SAMPLE)
        m1 = next(m for m in mandates if m["id"] == "M001")
        assert m1["type"] == "HARD"
        assert m1["title"] == "First Mandate"
        assert "Description of mandate one" in m1["description"]
        assert m1["criticality"] == "OBRIGATÓRIO"

    def test_parses_id_num(self) -> None:
        from providence_wizard.orchestration.mandate_compiler import MandateCompiler

        compiler = MandateCompiler()
        _, mandates = compiler.parse_mandate_spec(MANDATE_SPEC_SAMPLE)
        m1 = next(m for m in mandates if m["id"] == "M001")
        assert m1["id_num"] == 1

    def test_empty_text_returns_zero_count(self) -> None:
        from providence_wizard.orchestration.mandate_compiler import MandateCompiler

        compiler = MandateCompiler()
        count, mandates = compiler.parse_mandate_spec("")
        assert count == 0
        assert mandates == []

    def test_missing_fields_use_defaults(self) -> None:
        from providence_wizard.orchestration.mandate_compiler import MandateCompiler

        text = "mandate M003 { }"
        compiler = MandateCompiler()
        _, mandates = compiler.parse_mandate_spec(text)
        assert len(mandates) == 1
        m = mandates[0]
        assert m["type"] == "HARD"  # default
        assert m["title"] == "Unknown"  # default


class TestParseGuidelinesDsl:
    def test_parses_count(self) -> None:
        from providence_wizard.orchestration.mandate_compiler import MandateCompiler

        compiler = MandateCompiler()
        count, guidelines = compiler.parse_guidelines_dsl(GUIDELINES_DSL_SAMPLE)
        assert count == 2

    def test_parses_guideline_ids(self) -> None:
        from providence_wizard.orchestration.mandate_compiler import MandateCompiler

        compiler = MandateCompiler()
        _, guidelines = compiler.parse_guidelines_dsl(GUIDELINES_DSL_SAMPLE)
        ids = [g["id"] for g in guidelines]
        assert "G001" in ids
        assert "G002" in ids

    def test_parses_guideline_fields(self) -> None:
        from providence_wizard.orchestration.mandate_compiler import MandateCompiler

        compiler = MandateCompiler()
        _, guidelines = compiler.parse_guidelines_dsl(GUIDELINES_DSL_SAMPLE)
        g1 = next(g for g in guidelines if g["id"] == "G001")
        assert g1["type"] == "SOFT"
        assert g1["title"] == "First Guideline"
        assert g1["category"] == "quality"

    def test_empty_text_returns_zero(self) -> None:
        from providence_wizard.orchestration.mandate_compiler import MandateCompiler

        compiler = MandateCompiler()
        count, guidelines = compiler.parse_guidelines_dsl("")
        assert count == 0
        assert guidelines == []

    def test_missing_category_defaults_to_general(self) -> None:
        from providence_wizard.orchestration.mandate_compiler import MandateCompiler

        text = 'guideline G005 { title: "X" }'
        compiler = MandateCompiler()
        _, guidelines = compiler.parse_guidelines_dsl(text)
        assert guidelines[0]["category"] == "general"


class TestCompileMandateSpec:
    def test_compiles_successfully_to_file(self, tmp_path: Path) -> None:
        from providence_wizard.orchestration.mandate_compiler import MandateCompiler

        input_file = tmp_path / "mandate.spec"
        input_file.write_text(MANDATE_SPEC_SAMPLE, encoding="utf-8")
        output_file = tmp_path / "output" / "mandates.bin"

        compiler = MandateCompiler(verbose=False)
        result = compiler.compile_mandate_spec(
            input_file, output_file, format="json_compressed"
        )
        assert result is True
        assert output_file.exists()

    def test_returns_false_when_input_missing(self, tmp_path: Path) -> None:
        from providence_wizard.orchestration.mandate_compiler import MandateCompiler

        compiler = MandateCompiler()
        result = compiler.compile_mandate_spec(
            tmp_path / "nonexistent.spec",
            tmp_path / "output.bin",
            format="json_compressed",
        )
        assert result is False

    def test_verbose_does_not_crash(self, tmp_path: Path, capsys: Any) -> None:
        from providence_wizard.orchestration.mandate_compiler import MandateCompiler

        input_file = tmp_path / "mandate.spec"
        input_file.write_text(MANDATE_SPEC_SAMPLE, encoding="utf-8")
        output_file = tmp_path / "out.bin"

        compiler = MandateCompiler(verbose=True)
        compiler.compile_mandate_spec(input_file, output_file, format="json_compressed")
        # No assertion needed — just checks no exception is thrown


class TestCompileGuidelinesDsl:
    def test_compiles_successfully(self, tmp_path: Path) -> None:
        from providence_wizard.orchestration.mandate_compiler import MandateCompiler

        input_file = tmp_path / "guidelines.dsl"
        input_file.write_text(GUIDELINES_DSL_SAMPLE, encoding="utf-8")
        output_file = tmp_path / "guidelines.bin"

        compiler = MandateCompiler()
        result = compiler.compile_guidelines_dsl(
            input_file, output_file, format="json_compressed"
        )
        assert result is True
        assert output_file.exists()

    def test_returns_true_when_input_missing(self, tmp_path: Path) -> None:
        # Guidelines are optional — missing source returns True
        from providence_wizard.orchestration.mandate_compiler import MandateCompiler

        compiler = MandateCompiler()
        result = compiler.compile_guidelines_dsl(
            tmp_path / "nonexistent.dsl",
            tmp_path / "output.bin",
            format="json_compressed",
        )
        assert result is True

    def test_verbose_log_is_called(self, tmp_path: Path, capsys: Any) -> None:
        from providence_wizard.orchestration.mandate_compiler import MandateCompiler

        input_file = tmp_path / "guidelines.dsl"
        input_file.write_text(GUIDELINES_DSL_SAMPLE, encoding="utf-8")
        output_file = tmp_path / "out.bin"

        compiler = MandateCompiler(verbose=True)
        compiler.compile_guidelines_dsl(
            input_file, output_file, format="json_compressed"
        )
        # verbose=True should call print internally — no assertion needed, just no crash


class TestCompileToBinary:
    def test_msgpack_format_returns_packed_bytes(self) -> None:
        import msgpack

        from providence_wizard.orchestration.mandate_compiler import compile_to_binary

        mandates = [{"id": "M001", "type": "HARD"}]
        binary_data = compile_to_binary(mandates, format="msgpack")

        assert isinstance(binary_data, bytes)
        decoded = msgpack.unpackb(binary_data, raw=False)
        assert decoded["count"] == 1
        assert decoded["mandates"] == mandates


class TestCompileMandateSpecEdgeCases:
    def test_logs_when_no_mandates_found(self, tmp_path: Path, capsys: Any) -> None:
        from providence_wizard.orchestration.mandate_compiler import MandateCompiler

        input_file = tmp_path / "mandate.spec"
        input_file.write_text("# no mandates here\n", encoding="utf-8")
        output_file = tmp_path / "mandates.bin"

        compiler = MandateCompiler(verbose=True)
        result = compiler.compile_mandate_spec(
            input_file, output_file, format="json_compressed"
        )

        assert result is True
        captured = capsys.readouterr()
        assert "No mandates found" in captured.out

    def test_returns_false_on_compile_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from providence_wizard.orchestration import mandate_compiler
        from providence_wizard.orchestration.mandate_compiler import MandateCompiler

        input_file = tmp_path / "mandate.spec"
        input_file.write_text(MANDATE_SPEC_SAMPLE, encoding="utf-8")
        output_file = tmp_path / "output.bin"

        def _boom(*args: Any, **kwargs: Any) -> bytes:
            raise RuntimeError("boom")

        monkeypatch.setattr(mandate_compiler, "compile_to_binary", _boom)

        compiler = MandateCompiler()
        result = compiler.compile_mandate_spec(
            input_file, output_file, format="json_compressed"
        )

        assert result is False


class TestCompileGuidelinesDslEdgeCases:
    def test_compiles_successfully_with_msgpack_default(self, tmp_path: Path) -> None:
        from providence_wizard.orchestration.mandate_compiler import MandateCompiler

        input_file = tmp_path / "guidelines.dsl"
        input_file.write_text(GUIDELINES_DSL_SAMPLE, encoding="utf-8")
        output_file = tmp_path / "guidelines.bin"

        compiler = MandateCompiler()
        result = compiler.compile_guidelines_dsl(input_file, output_file)

        assert result is True
        assert output_file.exists()

    def test_returns_false_on_compile_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from providence_wizard.orchestration import mandate_compiler
        from providence_wizard.orchestration.mandate_compiler import MandateCompiler

        input_file = tmp_path / "guidelines.dsl"
        input_file.write_text(GUIDELINES_DSL_SAMPLE, encoding="utf-8")
        output_file = tmp_path / "guidelines.bin"

        def _boom(*args: Any, **kwargs: Any) -> bytes:
            raise RuntimeError("boom")

        monkeypatch.setattr(mandate_compiler.msgpack, "packb", _boom)

        compiler = MandateCompiler()
        result = compiler.compile_guidelines_dsl(input_file, output_file)

        assert result is False


class TestMandateCompilerLog:
    def test_log_prints_when_verbose(self, capsys: Any) -> None:
        from providence_wizard.orchestration.mandate_compiler import MandateCompiler

        compiler = MandateCompiler(verbose=True)
        compiler.log("hello world")
        captured = capsys.readouterr()
        assert "hello world" in captured.out

    def test_log_silent_when_not_verbose(self, capsys: Any) -> None:
        from providence_wizard.orchestration.mandate_compiler import MandateCompiler

        compiler = MandateCompiler(verbose=False)
        compiler.log("should not appear")
        captured = capsys.readouterr()
        assert "should not appear" not in captured.out
