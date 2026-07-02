Write `rolling.py` in /workspace implementing a class `RollingAverage`.

The tests in `tests/test_rolling.py` are the complete and only specification — they pin down the
exact semantics (constructor validation, the sliding window size, eviction order, what `.value()`
returns when empty, and what `.reset()` returns). Read them, implement `RollingAverage`, run
`python -m pytest tests/ -q`, and iterate until all tests pass.
