from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path


class raises:
    def __init__(self, exc_type, match=None):
        self.exc_type = exc_type
        self.match = match

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            raise AssertionError(f"Expected {self.exc_type.__name__} to be raised")
        if not issubclass(exc_type, self.exc_type):
            return False
        if self.match is not None and re.search(self.match, str(exc)) is None:
            raise AssertionError(f"Pattern {self.match!r} not found in {exc!r}")
        return True


def _load_module(path: Path):
    module_name = path.stem
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _run_path(path: Path) -> int:
    failures = 0
    files = [path] if path.is_file() else sorted(path.glob('test_*.py'))
    for file in files:
        module = _load_module(file)
        for name in sorted(n for n in dir(module) if n.startswith('test_')):
            try:
                getattr(module, name)()
                print(f"PASS {file.name}::{name}")
            except Exception as exc:
                failures += 1
                print(f"FAIL {file.name}::{name}: {exc}", file=sys.stderr)
    return failures


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    targets = [Path(arg) for arg in argv if not arg.startswith('-')] or [Path('tests')]
    failures = 0
    for target in targets:
        failures += _run_path(target)
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
