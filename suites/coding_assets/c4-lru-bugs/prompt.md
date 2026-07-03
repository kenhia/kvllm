The /workspace directory contains an LRU cache in `lru.py` and tests in `tests/test_lru.py`.
The implementation has bugs — several tests fail. Fix `lru.py` so all tests pass, **without
changing the tests** and **without rewriting the public API** (`LRU(capacity)`, `.get(key)`,
`.put(key, value)`).

Run `python -m pytest tests/ -q`, read each failure, and iterate until green. The tests probe
distinct behaviors, so fixing one may reveal the next.
