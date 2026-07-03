from collections import deque


class RollingAverage:
    def __init__(self, window):
        if window < 1:
            raise ValueError("window must be >= 1")
        self._buf = deque(maxlen=window)

    def add(self, x):
        self._buf.append(x)

    def value(self):
        return sum(self._buf) / len(self._buf) if self._buf else 0.0

    def reset(self):
        old = self.value()
        self._buf.clear()
        return old
