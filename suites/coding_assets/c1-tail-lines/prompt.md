Write a file `tail_lines.py` in /workspace exposing `tail_lines(path: str, n: int) -> list[str]`.

Return the last `n` lines of the text file at `path`, as a list of strings with no trailing
newline characters.
- If `n <= 0`, return `[]`.
- If `n` is larger than the number of lines, return all lines.
- An empty file returns `[]`.
- A file whose last line has no trailing newline still yields that line.

Example: for a file containing `a\nb\nc\n`, `tail_lines(path, 2)` -> `["b", "c"]`.
