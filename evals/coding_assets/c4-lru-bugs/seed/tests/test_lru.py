from lru import LRU


def test_capacity_evicts_lru():
    c = LRU(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)  # "a" is least-recently-used -> evicted
    assert c.get("a") is None
    assert c.get("b") == 2
    assert c.get("c") == 3


def test_get_refreshes_recency():
    c = LRU(2)
    c.put("a", 1)
    c.put("b", 2)
    assert c.get("a") == 1  # touch "a" -> now "b" is least-recent
    c.put("c", 3)  # evicts "b"
    assert c.get("b") is None
    assert c.get("a") == 1
    assert c.get("c") == 3


def test_overwrite_refreshes_recency():
    c = LRU(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("a", 10)  # overwrite "a" -> now "b" is least-recent, "a" == 10
    c.put("c", 3)  # evicts "b"
    assert c.get("a") == 10
    assert c.get("b") is None
    assert c.get("c") == 3
