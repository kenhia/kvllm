def merge_intervals(pairs) -> list:
    out = []
    for lo, hi in sorted(tuple(p) for p in pairs):
        if out and lo <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], hi))
        else:
            out.append((lo, hi))
    return out
