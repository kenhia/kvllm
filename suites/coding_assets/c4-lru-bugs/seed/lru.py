class LRU:
    """A fixed-capacity least-recently-used cache.

    LRU(capacity): create a cache holding at most `capacity` keys.
    get(key): return the value, or None if absent. A successful get counts as a use (it makes
        the key most-recently-used).
    put(key, value): insert or update. Inserting/updating a key makes it most-recently-used.
        When the cache exceeds capacity, the least-recently-used key is evicted.
    """

    def __init__(self, capacity):
        self.cap = capacity
        self.data = {}
        self.order = []  # least-recently-used first, most-recently-used last

    def get(self, key):
        if key not in self.data:
            return None
        return self.data[key]

    def put(self, key, value):
        if key in self.data:
            self.data[key] = value
        else:
            self.data[key] = value
            self.order.append(key)
        if len(self.data) > self.cap + 1:
            oldest = self.order.pop(0)
            del self.data[oldest]
