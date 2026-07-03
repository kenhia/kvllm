import collections
import sys


def main(argv):
    levels = collections.Counter()
    errors = collections.Counter()
    with open(argv[1]) as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            parts = line.split(None, 3)
            if len(parts) < 3:
                continue
            level = parts[2]
            levels[level] += 1
            if level == "ERROR":
                errors[parts[3] if len(parts) > 3 else ""] += 1

    out = []
    for level, c in sorted(levels.items(), key=lambda kv: (-kv[1], kv[0])):
        out.append(f"{level} {c}")
    out.append("top errors:")
    for msg, c in sorted(errors.items(), key=lambda kv: (-kv[1], kv[0]))[:3]:
        out.append(f"{c}× {msg}")
    print("\n".join(out))


if __name__ == "__main__":
    main(sys.argv)
