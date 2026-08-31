from __future__ import annotations

import importlib.util
import inspect
import sys
import traceback
from pathlib import Path
from types import ModuleType
from typing import Iterable


def _iter_test_files(targets: list[str]) -> list[Path]:
    if not targets:
        targets = ["."]
    files: list[Path] = []
    for target in targets:
        path = Path(target).resolve()
        if path.is_dir():
            files.extend(sorted(path.rglob("test_*.py")))
        elif path.is_file() and path.name.startswith("test_") and path.suffix == ".py":
            files.append(path)
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in files:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


def _load_module(path: Path, index: int) -> ModuleType:
    module_name = f"_pytest_shim_{index}_{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _iter_tests(module: ModuleType) -> Iterable[tuple[str, object]]:
    for name, value in sorted(module.__dict__.items()):
        if name.startswith("test_") and inspect.isfunction(value):
            yield name, value


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    targets = [arg for arg in args if not arg.startswith("-")]
    files = _iter_test_files(targets)
    if not files:
        print("no tests collected", file=sys.stderr)
        return 5

    failures = 0
    total = 0
    for index, path in enumerate(files):
        sys.path.insert(0, str(path.parent))
        sys.path.insert(0, str(path.parent.parent))
        try:
            module = _load_module(path, index)
        except Exception:
            failures += 1
            total += 1
            print(f"ERROR {path}")
            traceback.print_exc()
            continue

        for test_name, test_fn in _iter_tests(module):
            total += 1
            try:
                test_fn()
            except Exception:
                failures += 1
                print(f"FAILED {path.name}::{test_name}")
                traceback.print_exc()
            else:
                print(f"PASSED {path.name}::{test_name}")

    print(f"{total - failures} passed, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
