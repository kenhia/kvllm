import csv
import sys


def main(argv):
    path = argv[1]
    conds = [a.split("=", 1) for a in argv[2:]]
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        return
    header = rows[0]
    idx = {name: i for i, name in enumerate(header)}
    w = csv.writer(sys.stdout)
    w.writerow(header)
    for row in rows[1:]:
        if all(c in idx and row[idx[c]] == v for c, v in conds):
            w.writerow(row)


if __name__ == "__main__":
    main(sys.argv)
