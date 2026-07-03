"""Running statistics.

BUG: state lives in module-level globals, so every caller shares the same data. This should be
a `Stats` class where each instance is independent. The tests import `Stats`.

Target API:
    s = Stats()
    s.add(x)      # record a value
    s.count()     # number of values recorded
    s.mean()      # arithmetic mean, 0.0 when empty
    s.reset()     # clear this instance's values
"""

_values = []


def add(x):
    _values.append(x)


def count():
    return len(_values)


def mean():
    return sum(_values) / len(_values) if _values else 0.0


def reset():
    _values.clear()
