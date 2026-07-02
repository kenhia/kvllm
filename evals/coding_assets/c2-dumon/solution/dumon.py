import sys


def main(argv):
    threshold = float(argv[1])
    rows = []
    for line in sys.stdin:
        line = line.rstrip("\n")
        if not line.strip():
            continue
        kib_s, path = line.split("\t", 1)
        kib = int(kib_s)
        if kib / 1024 > threshold:
            rows.append((kib, path))
    rows.sort(key=lambda kp: (-kp[0], kp[1]))
    for kib, path in rows:
        print(f"{round(kib / 1024)} MB  {path}")


if __name__ == "__main__":
    main(sys.argv)
