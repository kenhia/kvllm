class Inventory:
    """A simple item -> count inventory.

    add(item, qty): increase the count for an item.
    remove(item, qty): decrease the count. Removing more than is present clamps at 0, and
        removing an item that isn't present is a no-op (it never raises).
    report(): return a dict of item -> count, including only items with a positive count.

    Each Inventory() is independent; two instances never share state.
    """

    def __init__(self, items={}):
        self.items = items

    def add(self, item, qty=1):
        self.items[item] = self.items.get(item, 0) + qty

    def remove(self, item, qty=1):
        self.items[item] -= qty

    def report(self):
        return {k: v for k, v in self.items.items() if v > 0}
