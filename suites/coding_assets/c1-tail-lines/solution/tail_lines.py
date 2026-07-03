def tail_lines(path: str, n: int) -> list:
    if n <= 0:
        return []
    with open(path) as f:
        return f.read().splitlines()[-n:]
