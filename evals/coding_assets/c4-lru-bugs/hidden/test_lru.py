from lru import LRU


def test_capacity_evicts_lru():
    c = LRU(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)
    assert c.get("a") is None
    assert c.get("b") == 2
    assert c.get("c") == 3


def test_get_refreshes_recency():
    c = LRU(2)
    c.put("a", 1)
    c.put("b", 2)
    assert c.get("a") == 1
    c.put("c", 3)
    assert c.get("b") is None
    assert c.get("a") == 1
    assert c.get("c") == 3


def test_overwrite_refreshes_recency():
    c = LRU(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("a", 10)
    c.put("c", 3)
    assert c.get("a") == 10
    assert c.get("b") is None
    assert c.get("c") == 3


# --- deeper interleavings ---


def test_get_missing_returns_none():
    c = LRU(2)
    assert c.get("nope") is None


def test_repeated_get_keeps_key_alive():
    c = LRU(2)
    c.put("a", 1)
    c.put("b", 2)
    c.get("a")
    c.get("a")
    c.put("c", 3)  # b is LRU -> evicted
    assert c.get("b") is None
    assert c.get("a") == 1


def test_capacity_one():
    c = LRU(1)
    c.put("a", 1)
    c.put("b", 2)
    assert c.get("a") is None
    assert c.get("b") == 2


def test_get_then_put_eviction_order():
    c = LRU(3)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)
    assert c.get("a") == 1  # order now b, c, a
    c.put("d", 4)  # evict b (LRU)
    assert c.get("b") is None
    assert c.get("a") == 1
    assert c.get("c") == 3
    assert c.get("d") == 4


def test_overwrite_does_not_grow_size():
    c = LRU(2)
    c.put("a", 1)
    c.put("a", 2)
    c.put("a", 3)
    c.put("b", 5)
    assert c.get("a") == 3
    assert c.get("b") == 5
