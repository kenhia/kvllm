The /workspace directory contains `stats.py` and tests in `tests/`. The module currently keeps
its state in module-level globals, so all callers share one dataset — a bug. The tests import a
`Stats` **class** and expect each instance to have independent state.

Refactor `stats.py` to expose a `Stats` class with `add(x)`, `count()`, `mean()` (0.0 when
empty), and `reset()`, so every test in `tests/` passes **without changing the tests**. Remove
the shared module-level state. Run: `python -m pytest tests/ -q`.
