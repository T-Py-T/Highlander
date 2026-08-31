from __future__ import annotations

import re
from contextlib import ContextDecorator


class raises(ContextDecorator):
    def __init__(self, expected_exception, match: str | None = None):
        self.expected_exception = expected_exception
        self.match = match

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            raise AssertionError(f"DID NOT RAISE {self.expected_exception.__name__}")
        if not issubclass(exc_type, self.expected_exception):
            return False
        if self.match is not None and re.search(self.match, str(exc)) is None:
            raise AssertionError(
                f"Exception message {str(exc)!r} does not match pattern {self.match!r}"
            )
        return True
