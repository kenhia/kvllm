The /workspace directory contains `inventory.py` and a test suite in `tests/`. Some tests fail.

Make every test in `tests/` pass **without changing the tests**. Read `inventory.py` and its
docstrings carefully — the documented behavior (e.g. `remove` on a missing item is a no-op, and
two separate `Inventory()` objects must not share state) is what the tests check.

Run the tests with `python -m pytest tests/ -q`.
