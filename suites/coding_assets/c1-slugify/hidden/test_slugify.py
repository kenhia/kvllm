from slugify import slugify


def test_basic():
    assert slugify("Hello, World!") == "hello-world"


def test_empty():
    assert slugify("") == ""


def test_all_symbols():
    assert slugify("___") == ""
    assert slugify("!!! @@@ ###") == ""


def test_collapse_separators():
    assert slugify("  a--b__c  ") == "a-b-c"


def test_unicode_dropped():
    assert slugify("Café au lait") == "caf-au-lait"


def test_digits_kept():
    assert slugify("MixedCASE123") == "mixedcase123"


def test_already_slug():
    assert slugify("already-a-slug") == "already-a-slug"


def test_leading_trailing_stripped():
    assert slugify("--hi--") == "hi"
