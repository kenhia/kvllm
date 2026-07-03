import re

_UNITS = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3}


def parse_size(s: str) -> int:
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([KMGkmg]?)[Bb]?", s.strip())
    if not m:
        raise ValueError(f"bad size: {s!r}")
    return int(float(m.group(1)) * _UNITS[m.group(2).upper()])
