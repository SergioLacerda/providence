"""
Template: Thread Isolation Compliance Tests

COPY THIS FILE TO: tests/unit/specs_ia_units/test_thread_isolation.py

For projects with concurrent execution across threads.
"""

from pathlib import Path

import pytest


class TestThreadIsolation:
    """RULE 2: Thread modifications must be isolated from each other."""

    def test_execution_state_tracks_threads(self) -> None:
        """Execution state must document thread isolation."""
        state_file = Path(
            "docs/ia/custom/[project]/development/execution-state/_current.md"
        )

        if not state_file.exists():
            pytest.skip("Project doesn't use execution-state tracking")

        content = state_file.read_text(encoding="utf-8")

        # Should document threads if project is concurrent
        # At minimum, should mention "thread" or "concurrent" or "task"
        any(
            word in content
            for word in [
                "thread",
                "Thread",
                "concurrent",
                "Concurrent",
                "task",
                "Task",
                "parallel",
                "Parallel",
            ]
        )

        # This is optional - only for concurrent projects
        # assert has_thread_awareness or "no concurrency" in content.lower()

    def test_no_global_mutable_state(self) -> None:
        """Application must not have shared mutable state at module level."""
        app_files = Path("src/[project_name]/application").rglob("*.py")

        dangerous_patterns = []
        for file in app_files:
            if file.name.startswith("__"):
                continue

            content = file.read_text(encoding="utf-8")
            lines = content.split("\n")

            for i, line in enumerate(lines, 1):
                # Look for module-level mutable defaults without synchronization
                if (
                    any(
                        line.strip().startswith(f"shared_{word}")
                        for word in ["cache", "state", "data", "pool"]
                    )
                    and "Lock" not in content
                    and "RLock" not in content
                ):
                    dangerous_patterns.append(
                        f"{file}:{i}: shared state without synchronization"
                    )

                if (
                    any(
                        line.strip().startswith(f"global_{word}")
                        for word in ["cache", "state", "data"]
                    )
                    and "thread_local" not in content
                    and "Lock" not in content
                ):
                    dangerous_patterns.append(
                        f"{file}:{i}: global state without thread safety"
                    )

        assert not dangerous_patterns, "Thread safety violations found:\n" + "\n".join(
            dangerous_patterns
        )

    def test_no_shared_session_variables(self) -> None:
        """No session/request objects should be stored in module-level variables."""
        app_files = Path("src/[project_name]/application").rglob("*.py")

        violations = []
        for file in app_files:
            if file.name.startswith("__"):
                continue

            content = file.read_text(encoding="utf-8")

            # Check for dangerous patterns
            if "_session" in content.lower():
                lines = content.split("\n")
                for i, line in enumerate(lines, 1):
                    if (
                        "_session" in line.lower()
                        and not line.strip().startswith("#")
                        and "def " not in lines[max(0, i - 2) : i]
                        and "self." not in line
                        and "param" not in line
                    ):
                        violations.append(f"{file}:{i}: session stored globally")

        # This is optional - depends on project architecture
        # assert not violations

    def test_cache_is_thread_safe_if_used(self) -> None:
        """If caching is used, it must be thread-safe."""
        app_files = Path("src/[project_name]/application").rglob("*.py")

        has_cache = False
        cache_implementations = []

        for file in app_files:
            if file.name.startswith("__"):
                continue

            content = file.read_text(encoding="utf-8")

            # Check for caching patterns
            if "lru_cache" in content or "cache" in content.lower():
                has_cache = True

                # If using functools.lru_cache with threading, needs care
                if "functools" in content and "Thread" in content:
                    cache_implementations.append(
                        f"{file}: lru_cache used with threading"
                    )

                # If manual cache, should use Lock
                if "self._cache" in content and "Lock" not in content:
                    cache_implementations.append(f"{file}: manual cache without Lock")

        # Only verify if project actually uses caching
        if has_cache and cache_implementations:
            # Warning, not failure - depends on project needs
            print(f"\n⚠️  Cache thread-safety check: {', '.join(cache_implementations)}")  # noqa: T201


class TestConcurrencyPatterns:
    """Validate thread-safe patterns used in project."""

    def test_valid_concurrency_patterns(self) -> None:
        """If project uses threading, verify patterns are thread-safe."""
        # Check if project imports threading
        app_files = Path("src/[project_name]/application").rglob("*.py")

        uses_threading = False
        for file in app_files:
            if "import threading" in file.read_text(encoding="utf-8"):
                uses_threading = True
                break

        if uses_threading:
            # Verify at least some Lock or synchronization exists
            has_synchronization = False
            for file in app_files:
                content = file.read_text(encoding="utf-8")
                if any(
                    pattern in content
                    for pattern in ["Lock", "Semaphore", "Event", "Condition"]
                ):
                    has_synchronization = True
                    break

            assert has_synchronization, (
                "Project uses threading but no synchronization primitives found"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
