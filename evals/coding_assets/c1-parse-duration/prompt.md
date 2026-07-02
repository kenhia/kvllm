Write a file `parse_duration.py` in /workspace exposing `parse_duration(s: str) -> int`.

Parse a compact duration string into a number of seconds. The units are hours `h`, minutes `m`,
seconds `s`, and must appear in that order (any of them may be omitted). A bare integer means
seconds. Surrounding whitespace is ignored. Anything else raises `ValueError`.

Examples:
- `parse_duration("1h30m")` -> `5400`
- `parse_duration("90s")` -> `90`
- `parse_duration("2h")` -> `7200`
- `parse_duration("45")` -> `45`
- `parse_duration("30m15s")` -> `1815`
- `parse_duration("1m30h")` raises `ValueError`   (wrong order)
- `parse_duration("")` raises `ValueError`
