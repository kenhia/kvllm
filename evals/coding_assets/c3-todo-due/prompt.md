The /workspace directory contains a small todo module `todo.py` and tests in `tests/`. Some
tests fail: the **due-date filter** described in `todo.py`'s docstring (`filter_items` with a
`due_before` argument) is not implemented yet.

Implement it so every test in `tests/` passes, **without changing the tests**. Do not change the
existing `status` filtering behavior. Run: `python -m pytest tests/ -q`.
