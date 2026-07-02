Write a file `dedupe.py` in /workspace exposing `dedupe(seq, key=None) -> list`.

Return the items of `seq` with duplicates removed, preserving first-occurrence order.
- With no `key`, two items are duplicates if they are equal.
- With a `key` callable, two items are duplicates if `key(item)` values are equal (keep the
  first item seen for each key).

Examples:
- `dedupe([3, 1, 3, 2, 1])` -> `[3, 1, 2]`
- `dedupe([])` -> `[]`
- `dedupe(["A", "a", "B"], key=str.lower)` -> `["A", "B"]`
