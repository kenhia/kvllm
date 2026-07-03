import json
import sys


def deep_merge(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for k, v in b.items():
            out[k] = deep_merge(out[k], v) if k in out else v
        return out
    return b


def main(argv):
    result = {}
    for path in argv[1:]:
        with open(path) as f:
            result = deep_merge(result, json.load(f))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv)
