"""Tests for skill context delta computation."""

from __future__ import annotations

import time

from providence_core.skill_context import (
    ContextCache,
    ContextSignature,
    compute_context_signature,
    compute_input_signature,
    compute_scope_hash,
    is_delta_context,
)


class TestComputeScopeHash:
    def test_deterministic_same_order(self) -> None:
        h1 = compute_scope_hash(["a", "b", "c"])
        h2 = compute_scope_hash(["a", "b", "c"])
        assert h1 == h2

    def test_order_independent(self) -> None:
        h1 = compute_scope_hash(["c", "a", "b"])
        h2 = compute_scope_hash(["a", "b", "c"])
        assert h1 == h2

    def test_different_paths_differ(self) -> None:
        assert compute_scope_hash(["x"]) != compute_scope_hash(["y"])

    def test_empty_list(self) -> None:
        h = compute_scope_hash([])
        assert isinstance(h, str)
        assert len(h) == 64  # sha256 hex

    def test_returns_hex_string(self) -> None:
        h = compute_scope_hash(["packages/core"])
        assert all(c in "0123456789abcdef" for c in h)


class TestComputeContextSignature:
    def test_returns_context_signature(self) -> None:
        sig = compute_context_signature(
            scope_paths=["src/"],
            registry_fingerprint="abc123",
            active_rule_ids=["scope_lock@1.0.0"],
        )
        assert isinstance(sig, ContextSignature)

    def test_active_rules_sorted(self) -> None:
        sig = compute_context_signature(
            scope_paths=["src/"],
            registry_fingerprint="fp",
            active_rule_ids=["z@1.0", "a@1.0"],
        )
        assert sig.active_rules == ("a@1.0", "z@1.0")

    def test_computed_at_is_recent(self) -> None:
        before = time.time()
        sig = compute_context_signature(["src/"], "fp", [])
        after = time.time()
        assert before <= sig.computed_at <= after


class TestContextSignature:
    def _make_sig(self, scope: list[str] | None = None) -> ContextSignature:
        return ContextSignature(
            scope_hash=compute_scope_hash(scope or ["src/"]),
            registry_fingerprint="fp",
            active_rules=("rule@1.0",),
            computed_at=time.time(),
        )

    def test_is_expired_false_when_recent(self) -> None:
        sig = self._make_sig()
        assert sig.is_expired(ttl_seconds=9999) is False

    def test_is_expired_true_when_old(self) -> None:
        sig = ContextSignature(
            scope_hash="h",
            registry_fingerprint="fp",
            active_rules=(),
            computed_at=time.time() - 9999,
        )
        assert sig.is_expired(ttl_seconds=1) is True

    def test_matches_identical_structural_fields(self) -> None:
        s1 = ContextSignature("h", "fp", ("r@1",), computed_at=1.0)
        s2 = ContextSignature("h", "fp", ("r@1",), computed_at=9999.0)
        assert s1.matches(s2) is True

    def test_matches_different_scope_hash(self) -> None:
        s1 = ContextSignature("h1", "fp", (), computed_at=1.0)
        s2 = ContextSignature("h2", "fp", (), computed_at=1.0)
        assert s1.matches(s2) is False

    def test_matches_different_fingerprint(self) -> None:
        s1 = ContextSignature("h", "fp1", (), computed_at=1.0)
        s2 = ContextSignature("h", "fp2", (), computed_at=1.0)
        assert s1.matches(s2) is False

    def test_matches_different_rules(self) -> None:
        s1 = ContextSignature("h", "fp", ("r@1",), computed_at=1.0)
        s2 = ContextSignature("h", "fp", ("r@2",), computed_at=1.0)
        assert s1.matches(s2) is False


class TestContextCache:
    def test_get_returns_none_for_missing(self) -> None:
        cache = ContextCache()
        assert cache.get("missing") is None

    def test_set_and_get(self) -> None:
        cache = ContextCache()
        sig = ContextSignature("h", "fp", (), computed_at=1.0)
        cache.set("k", sig)
        assert cache.get("k") is sig

    def test_invalidate_removes_entry(self) -> None:
        cache = ContextCache()
        sig = ContextSignature("h", "fp", (), computed_at=1.0)
        cache.set("k", sig)
        cache.invalidate("k")
        assert cache.get("k") is None

    def test_invalidate_missing_key_is_safe(self) -> None:
        cache = ContextCache()
        cache.invalidate("nonexistent")  # must not raise


class TestComputeInputSignature:
    def test_returns_hex_string(self) -> None:
        sig = compute_input_signature("diagnose", ["src/"], "fp")
        assert all(c in "0123456789abcdef" for c in sig)
        assert len(sig) == 64

    def test_deterministic(self) -> None:
        s1 = compute_input_signature("diagnose", ["src/"], "fp")
        s2 = compute_input_signature("diagnose", ["src/"], "fp")
        assert s1 == s2

    def test_different_intent_differs(self) -> None:
        s1 = compute_input_signature("diagnose", ["src/"], "fp")
        s2 = compute_input_signature("correct", ["src/"], "fp")
        assert s1 != s2

    def test_scope_order_independent(self) -> None:
        s1 = compute_input_signature("x", ["a", "b"], "fp")
        s2 = compute_input_signature("x", ["b", "a"], "fp")
        assert s1 == s2


class TestIsDeltaContext:
    def _fresh_sig(self, scope: str = "src/") -> ContextSignature:
        return ContextSignature(
            scope_hash=compute_scope_hash([scope]),
            registry_fingerprint="fp",
            active_rules=("r@1",),
            computed_at=time.time(),
        )

    def test_returns_false_when_cached_is_none(self) -> None:
        current = self._fresh_sig()
        assert is_delta_context(current, None) is False

    def test_returns_false_when_cached_expired(self) -> None:
        current = self._fresh_sig()
        expired = ContextSignature(
            scope_hash=current.scope_hash,
            registry_fingerprint=current.registry_fingerprint,
            active_rules=current.active_rules,
            computed_at=time.time() - 9999,
        )
        assert is_delta_context(current, expired, ttl_seconds=1) is False

    def test_returns_true_when_cached_matches_and_fresh(self) -> None:
        sig = self._fresh_sig()
        cached = ContextSignature(
            scope_hash=sig.scope_hash,
            registry_fingerprint=sig.registry_fingerprint,
            active_rules=sig.active_rules,
            computed_at=time.time(),
        )
        assert is_delta_context(sig, cached, ttl_seconds=9999) is True

    def test_returns_false_when_scope_differs(self) -> None:
        current = self._fresh_sig("src/")
        cached = ContextSignature(
            scope_hash=compute_scope_hash(["other/"]),
            registry_fingerprint="fp",
            active_rules=("r@1",),
            computed_at=time.time(),
        )
        assert is_delta_context(current, cached, ttl_seconds=9999) is False
