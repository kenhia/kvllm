Write a script `jsonmerge.py` in /workspace. Run as:
`python jsonmerge.py a.json b.json [c.json ...]`

Deep-merge the JSON files left to right (later files win). Merge rule:
- If both sides are objects (dicts), merge them key by key, recursing.
- Otherwise (arrays, scalars, or a type mismatch), the later value replaces the earlier one.

Print the merged result as `json.dumps(result, indent=2, sort_keys=True)`.

Example: merging `{"a": 1, "nested": {"x": 1}}` then `{"nested": {"y": 2}, "a": 5}` gives
`{"a": 5, "nested": {"x": 1, "y": 2}}`.
