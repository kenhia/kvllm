"""Running statistics as a class; each instance is independent."""


class Stats:
    def __init__(self):
        self._values = []

    def add(self, x):
        self._values.append(x)

    def count(self):
        return len(self._values)

    def mean(self):
        return sum(self._values) / len(self._values) if self._values else 0.0

    def reset(self):
        self._values.clear()
