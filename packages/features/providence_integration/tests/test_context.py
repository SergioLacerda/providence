"""Comprehensive tests for providence_integration.engine.context — ExecutionContext management.

Covers:
- ExecutionContext initialization from spec with various configurations
- Isolation mode: temp directory creation and cleanup
- Working directory handling: configured, temp, default (cwd)
- Data dictionary access and initialization
- Directory expansion with ~ and .
- Multiple cleanup calls (idempotent)
- Edge cases: empty spec, missing context key, path resolution
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest

from providence_integration.engine.context import ExecutionContext

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


def _spec_with_context(**context_opts: Any) -> dict[str, Any]:
    """Create a spec with custom context options."""
    return {"context": context_opts}


# ---------------------------------------------------------------------------
# ExecutionContext — initialization with isolation
# ---------------------------------------------------------------------------


class TestExecutionContextIsolation:
    def test_isolation_true_creates_temp_dir(self) -> None:
        spec = _spec_with_context(isolation=True)
        ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
        try:
            assert ctx.isolation_enabled is True
            assert ctx._temp_dir is not None
            assert ctx._temp_dir.exists()
            assert ctx.working_dir == ctx._temp_dir
        finally:
            ctx.cleanup()

    def test_isolation_true_temp_dir_has_prefix(self) -> None:
        spec = _spec_with_context(isolation=True)
        ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
        try:
            assert "sdd-doctor-" in str(ctx._temp_dir)
        finally:
            ctx.cleanup()

    def test_isolation_false_no_temp_dir(self) -> None:
        spec = _spec_with_context(isolation=False)
        ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
        assert ctx.isolation_enabled is False
        assert ctx._temp_dir is None
        ctx.cleanup()

    def test_isolation_key_missing_defaults_to_false(self) -> None:
        spec = _spec_with_context()
        ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
        assert ctx.isolation_enabled is False
        assert ctx._temp_dir is None
        ctx.cleanup()


# ---------------------------------------------------------------------------
# ExecutionContext — working directory modes
# ---------------------------------------------------------------------------


class TestExecutionContextWorkingDir:
    def test_temp_working_dir_mode(self) -> None:
        spec = _spec_with_context(working_dir="temp")
        ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
        try:
            assert ctx.isolation_enabled is True
            assert ctx._temp_dir is not None
            assert ctx.working_dir == ctx._temp_dir
        finally:
            ctx.cleanup()

    def test_isolation_true_overrides_configured_working_dir(self) -> None:
        spec = _spec_with_context(isolation=True, working_dir="/tmp/custom")
        ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
        try:
            # isolation=True should take precedence
            assert ctx.isolation_enabled is True
            assert ctx._temp_dir is not None
            assert ctx.working_dir == ctx._temp_dir
        finally:
            ctx.cleanup()

    def test_configured_working_dir(self, tmp_path: Path) -> None:
        custom_dir = tmp_path / "myworkdir"
        spec = _spec_with_context(working_dir=str(custom_dir))
        ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
        try:
            assert ctx.working_dir == custom_dir.resolve()
            assert custom_dir.exists()
            assert ctx.isolation_enabled is False
            assert ctx._temp_dir is None
        finally:
            ctx.cleanup()

    def test_working_dir_with_home_expansion(self, tmp_path: Path, monkeypatch):
        # Mock home directory environment variables for all platforms
        # HOME is used on Linux/macOS, USERPROFILE on Windows
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        spec = _spec_with_context(working_dir="~/mywork")
        ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
        try:
            # Should expand ~ to home directory
            expected = (tmp_path / "mywork").resolve()
            assert ctx.working_dir == expected
        finally:
            ctx.cleanup()

    def test_working_dir_created_if_not_exists(self, tmp_path: Path) -> None:
        nested_dir = tmp_path / "a" / "b" / "c"
        assert not nested_dir.exists()
        spec = _spec_with_context(working_dir=str(nested_dir))
        ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
        try:
            assert nested_dir.exists()
        finally:
            ctx.cleanup()

    def test_default_working_dir_is_cwd(self) -> None:
        spec = _spec_with_context()
        ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
        try:
            assert ctx.working_dir == Path.cwd()
            assert ctx.isolation_enabled is False
        finally:
            ctx.cleanup()

    def test_none_working_dir_uses_cwd(self) -> None:
        spec = _spec_with_context(working_dir=None)
        ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
        try:
            assert ctx.working_dir == Path.cwd()
        finally:
            ctx.cleanup()

    def test_empty_string_working_dir_uses_cwd(self) -> None:
        spec = _spec_with_context(working_dir="")
        ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
        try:
            assert ctx.working_dir == Path.cwd()
        finally:
            ctx.cleanup()


# ---------------------------------------------------------------------------
# ExecutionContext — data dictionary
# ---------------------------------------------------------------------------


class TestExecutionContextData:
    def test_data_dict_initialized_empty(self) -> None:
        spec = _spec_with_context()
        ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
        try:
            # Data should have working_dir key
            d = ctx.as_dict()
            assert "working_dir" in d
        finally:
            ctx.cleanup()

    def test_as_dict_returns_data_reference(self) -> None:
        spec = _spec_with_context()
        ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
        try:
            d1 = ctx.as_dict()
            d2 = ctx.as_dict()
            assert d1 is d2
        finally:
            ctx.cleanup()

    def test_data_working_dir_set_from_context(self) -> None:
        spec = _spec_with_context()
        ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
        try:
            assert ctx.data["working_dir"] == ctx.working_dir
        finally:
            ctx.cleanup()

    def test_data_dict_mutable(self) -> None:
        spec = _spec_with_context()
        ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
        try:
            ctx.data["custom_key"] = "custom_value"
            assert ctx.as_dict()["custom_key"] == "custom_value"
        finally:
            ctx.cleanup()


# ---------------------------------------------------------------------------
# ExecutionContext — spec_dir and attributes
# ---------------------------------------------------------------------------


class TestExecutionContextAttributes:
    def test_spec_dir_stored(self) -> None:
        spec_dir = Path("/my/spec/dir")
        spec = _spec_with_context()
        ctx = ExecutionContext.from_spec(spec, spec_dir)
        try:
            assert ctx.spec_dir == spec_dir
        finally:
            ctx.cleanup()

    def test_all_attributes_initialized(self) -> None:
        spec = _spec_with_context()
        ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
        try:
            assert hasattr(ctx, "spec_dir")
            assert hasattr(ctx, "working_dir")
            assert hasattr(ctx, "isolation_enabled")
            assert hasattr(ctx, "data")
            assert hasattr(ctx, "_temp_dir")
        finally:
            ctx.cleanup()


# ---------------------------------------------------------------------------
# ExecutionContext — cleanup
# ---------------------------------------------------------------------------


class TestExecutionContextCleanup:
    def test_cleanup_removes_temp_dir(self) -> None:
        spec = _spec_with_context(isolation=True)
        ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
        temp_dir = ctx._temp_dir
        assert temp_dir is not None
        assert temp_dir.exists()
        ctx.cleanup()
        assert ctx._temp_dir is None
        assert not temp_dir.exists()

    def test_cleanup_idempotent(self) -> None:
        spec = _spec_with_context(isolation=True)
        ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
        ctx.cleanup()
        ctx.cleanup()  # Should not raise
        assert ctx._temp_dir is None

    def test_cleanup_noop_without_temp_dir(self) -> None:
        spec = _spec_with_context()
        ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
        # Should not raise
        ctx.cleanup()
        assert ctx._temp_dir is None

    def test_cleanup_with_ignore_errors(self) -> None:
        spec = _spec_with_context(isolation=True)
        ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
        temp_dir = ctx._temp_dir
        # Manually remove before cleanup
        shutil.rmtree(temp_dir)
        # Cleanup should not raise even though dir is already gone
        ctx.cleanup()
        assert ctx._temp_dir is None


# ---------------------------------------------------------------------------
# ExecutionContext — dataclass properties
# ---------------------------------------------------------------------------


class TestExecutionContextDataclass:
    def test_isolation_enabled_defaults_to_false(self) -> None:
        spec = _spec_with_context()
        ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
        try:
            assert ctx.isolation_enabled is False
        finally:
            ctx.cleanup()

    def test_data_defaults_to_empty_dict(self) -> None:
        # Direct instantiation should have empty data dict
        ctx = ExecutionContext(
            spec_dir=Path("/tmp/spec"),
            working_dir=Path("/tmp"),
            isolation_enabled=False,
        )
        assert ctx.data == {}
        ctx.cleanup()

    def test_temp_dir_defaults_to_none(self) -> None:
        ctx = ExecutionContext(
            spec_dir=Path("/tmp/spec"),
            working_dir=Path("/tmp"),
            isolation_enabled=False,
        )
        assert ctx._temp_dir is None
        ctx.cleanup()


# ---------------------------------------------------------------------------
# ExecutionContext — edge cases and special scenarios
# ---------------------------------------------------------------------------


class TestExecutionContextEdgeCases:
    def test_spec_missing_context_key(self) -> None:
        spec = {}  # No 'context' key
        ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
        try:
            assert ctx.isolation_enabled is False
            assert ctx._temp_dir is None
            assert ctx.working_dir == Path.cwd()
        finally:
            ctx.cleanup()

    def test_context_key_is_none(self) -> None:
        spec = {"context": None}
        # This will raise an error because None is not subscriptable
        # But let's test the actual behavior
        with pytest.raises((AttributeError, TypeError)):
            ExecutionContext.from_spec(spec, Path("/tmp/spec"))

    def test_isolation_is_string_true(self) -> None:
        # "isolation": "true" should be treated as truthy
        spec = _spec_with_context(isolation="true")
        ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
        try:
            # bool("true") is True
            assert ctx.isolation_enabled is True
        finally:
            ctx.cleanup()

    def test_isolation_is_zero(self) -> None:
        spec = _spec_with_context(isolation=0)
        ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
        try:
            assert ctx.isolation_enabled is False
        finally:
            ctx.cleanup()

    def test_isolation_is_empty_string(self) -> None:
        spec = _spec_with_context(isolation="")
        ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
        try:
            assert ctx.isolation_enabled is False
        finally:
            ctx.cleanup()

    def test_dot_path_expansion(self, tmp_path: Path, monkeypatch) -> None:
        # Change to tmp_path directory
        monkeypatch.chdir(tmp_path)
        spec = _spec_with_context(working_dir="./mywork")
        ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
        try:
            expected = (tmp_path / "mywork").resolve()
            assert ctx.working_dir == expected
        finally:
            ctx.cleanup()

    def test_relative_path_resolution(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        spec = _spec_with_context(working_dir="subdir")
        ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
        try:
            expected = (tmp_path / "subdir").resolve()
            assert ctx.working_dir == expected
        finally:
            ctx.cleanup()

    def test_absolute_path_preserved(self, tmp_path: Path) -> None:
        absolute_dir = tmp_path / "absolute"
        spec = _spec_with_context(working_dir=str(absolute_dir))
        ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
        try:
            assert ctx.working_dir == absolute_dir.resolve()
        finally:
            ctx.cleanup()

    def test_spec_dir_not_created(self) -> None:
        nonexistent_spec_dir = Path("/nonexistent/path/to/spec")
        spec = _spec_with_context()
        ctx = ExecutionContext.from_spec(spec, nonexistent_spec_dir)
        try:
            assert ctx.spec_dir == nonexistent_spec_dir
            # spec_dir is not created, only working_dir is
            assert not nonexistent_spec_dir.exists()
        finally:
            ctx.cleanup()

    def test_multiple_contexts_independent_temp_dirs(self) -> None:
        spec1 = _spec_with_context(isolation=True)
        spec2 = _spec_with_context(isolation=True)
        ctx1 = ExecutionContext.from_spec(spec1, Path("/tmp/spec1"))
        ctx2 = ExecutionContext.from_spec(spec2, Path("/tmp/spec2"))
        try:
            # Should have different temp directories
            assert ctx1._temp_dir != ctx2._temp_dir
            assert ctx1._temp_dir.exists()
            assert ctx2._temp_dir.exists()
        finally:
            ctx1.cleanup()
            ctx2.cleanup()

    def test_context_with_existing_working_dir(self, tmp_path: Path) -> None:
        # Pre-create the working directory
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir(parents=True, exist_ok=True)
        spec = _spec_with_context(working_dir=str(existing_dir))
        ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
        try:
            assert ctx.working_dir == existing_dir.resolve()
            assert existing_dir.exists()
        finally:
            ctx.cleanup()
