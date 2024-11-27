import itertools


class peekable:
    """A wrapper around iterators to make the peekable"""

    def __init__(self, iterator):
        self._iterator = iterator

    def peek(self):
        value = next(self._iterator)
        self._iterator = itertools.chain([value], self._iterator)
        return value

    def next(self):
        return next(self._iterator)

    def prepend(self, value):
        self._iterator = itertools.chain([value], self._iterator)

    def append(self, value):
        self._iterator = itertools.chain(self._iterator, [value])

    def __iter__(self):
        yield from self._iterator
