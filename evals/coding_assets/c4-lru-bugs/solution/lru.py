from collections import OrderedDict


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
        self.data = OrderedDict()

    def get(self, key):
        if key not in self.data:
            return None
        self.data.move_to_end(key)
        return self.data[key]

    def put(self, key, value):
        self.data[key] = value
        self.data.move_to_end(key)
        while len(self.data) > self.cap:
            self.data.popitem(last=False)
