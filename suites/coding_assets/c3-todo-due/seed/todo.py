"""A tiny todo list.

An item is a dict: {"text": str, "done": bool, "due": str | None}, where `due` is an ISO date
"YYYY-MM-DD" or None.

filter_items(items, status=None, due_before=None):
    - status "open" keeps not-done items, "done" keeps done items, None keeps all.
    - due_before (an ISO date string) keeps only items whose due date is strictly earlier than
      it. Items with due=None are excluded when due_before is given. When due_before is None, no
      due filtering is applied.
    - Both filters combine (AND). Order is preserved.
"""

import json
import sys


def filter_items(items, status=None, due_before=None):
    out = []
    for it in items:
        if status == "open" and it["done"]:
            continue
        if status == "done" and not it["done"]:
            continue
        # TODO: due_before filtering is not implemented yet.
        out.append(it)
    return out


def format_items(items):
    return "\n".join(
        f"[{'x' if it['done'] else ' '}] {it['text']}"
        + (f" (due {it['due']})" if it.get("due") else "")
        for it in items
    )


def main(argv):
    # usage: todo.py <store.json> [--open|--done] [--due YYYY-MM-DD]
    items = json.load(open(argv[1]))
    status = None
    due_before = None
    rest = argv[2:]
    i = 0
    while i < len(rest):
        if rest[i] == "--open":
            status = "open"
        elif rest[i] == "--done":
            status = "done"
        elif rest[i] == "--due":
            i += 1
            due_before = rest[i]
        i += 1
    print(format_items(filter_items(items, status=status, due_before=due_before)))


if __name__ == "__main__":
    main(sys.argv)
