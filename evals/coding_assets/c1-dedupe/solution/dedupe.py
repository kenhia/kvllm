def dedupe(seq, key=None) -> list:
    seen = set()
    out = []
    for x in seq:
        k = x if key is None else key(x)
        if k not in seen:
            seen.add(k)
            out.append(x)
    return out
