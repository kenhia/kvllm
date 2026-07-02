Write a file `parse_size.py` in /workspace exposing `parse_size(s: str) -> int`.

Parse a human size string into a number of bytes:
- Suffix `K`, `M`, `G` are powers of 1024 (K = 1024, M = 1024², G = 1024³).
- The suffix is case-insensitive and an optional trailing `B` is allowed (`"1.5GB"` == `"1.5G"`).
- No suffix means bytes.
- The numeric part may be an integer or a float; the result is always an `int` (truncated).
- Surrounding whitespace is ignored.
- Anything that doesn't match raises `ValueError`.

Examples:
- `parse_size("1.5G")` -> `1610612736`
- `parse_size("512M")` -> `536870912`
- `parse_size("3K")` -> `3072`
- `parse_size("42")` -> `42`
- `parse_size("nonsense")` raises `ValueError`
