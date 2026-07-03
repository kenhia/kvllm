Write a file `merge_intervals.py` in /workspace exposing
`merge_intervals(pairs) -> list`.

`pairs` is an iterable of `(low, high)` intervals (low <= high). Return the merged set of
intervals as a list of `(low, high)` tuples, sorted ascending. Intervals that overlap OR
merely touch (share an endpoint) merge into one.

Examples:
- `merge_intervals([(1, 3), (2, 6), (8, 10)])` -> `[(1, 6), (8, 10)]`
- `merge_intervals([(1, 2), (2, 3)])` -> `[(1, 3)]`   (touching merges)
- `merge_intervals([])` -> `[]`
- `merge_intervals([(5, 9), (1, 2)])` -> `[(1, 2), (5, 9)]`   (unsorted input ok)
