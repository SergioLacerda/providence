from providence_telemetry.engine.cache import LRUCache


def test_put_and_get() -> None:
    cache = LRUCache(max_size=10)
    cache.put("k1", {"a": 1})
    assert cache.get("k1") == {"a": 1}


def test_get_missing_returns_none() -> None:
    cache = LRUCache(max_size=10)
    assert cache.get("missing") is None


def test_lru_eviction() -> None:
    cache = LRUCache(max_size=2)
    cache.put("k1", {"v": 1})
    cache.put("k2", {"v": 2})
    cache.put("k3", {"v": 3})
    assert cache.get("k1") is None
    assert cache.get("k2") == {"v": 2}
    assert cache.get("k3") == {"v": 3}


def test_get_promotes_to_recent() -> None:
    cache = LRUCache(max_size=2)
    cache.put("k1", {"v": 1})
    cache.put("k2", {"v": 2})
    cache.get("k1")
    cache.put("k3", {"v": 3})
    assert cache.get("k1") == {"v": 1}
    assert cache.get("k2") is None


def test_disabled_cache_stores_nothing() -> None:
    cache = LRUCache(max_size=0)
    cache.put("k1", {"v": 1})
    assert cache.get("k1") is None
    assert len(cache) == 0


def test_clear() -> None:
    cache = LRUCache(max_size=10)
    cache.put("k1", {"v": 1})
    cache.put("k2", {"v": 2})
    cache.clear()
    assert len(cache) == 0
    assert cache.get("k1") is None


def test_len() -> None:
    cache = LRUCache(max_size=10)
    assert len(cache) == 0
    cache.put("k1", {"v": 1})
    assert len(cache) == 1
    cache.put("k2", {"v": 2})
    assert len(cache) == 2


def test_update_existing_key() -> None:
    cache = LRUCache(max_size=2)
    cache.put("k1", {"v": 1})
    cache.put("k1", {"v": 99})
    assert cache.get("k1") == {"v": 99}
    assert len(cache) == 1


def test_get_returns_independent_copy() -> None:
    cache = LRUCache(max_size=10)
    cache.put("k1", {"a": 1})
    result = cache.get("k1")
    assert result is not None
    result["injected"] = "bad"
    second = cache.get("k1")
    assert "injected" not in second
