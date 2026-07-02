from todo import filter_items

ITEMS = [
    {"text": "a", "done": False, "due": "2026-07-01"},
    {"text": "b", "done": True, "due": "2026-07-10"},
    {"text": "c", "done": False, "due": None},
    {"text": "d", "done": False, "due": "2026-07-03"},
]


def _texts(items):
    return [it["text"] for it in items]


def test_status_open():
    assert _texts(filter_items(ITEMS, status="open")) == ["a", "c", "d"]


def test_status_done():
    assert _texts(filter_items(ITEMS, status="done")) == ["b"]


def test_no_filters_keeps_all():
    assert _texts(filter_items(ITEMS)) == ["a", "b", "c", "d"]


def test_due_before_keeps_earlier():
    assert _texts(filter_items(ITEMS, due_before="2026-07-04")) == ["a", "d"]


def test_due_before_excludes_none_due():
    result = filter_items(ITEMS, due_before="2027-01-01")
    assert "c" not in _texts(result)


def test_status_and_due_combine():
    assert _texts(filter_items(ITEMS, status="open", due_before="2026-07-04")) == [
        "a",
        "d",
    ]
