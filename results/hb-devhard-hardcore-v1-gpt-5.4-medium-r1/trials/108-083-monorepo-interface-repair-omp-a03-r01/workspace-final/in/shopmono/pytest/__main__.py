from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path

PACKAGE_PATHS = ["packages/catalog", "packages/orders", "packages/reports"]


def iter_test_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw_path in paths or ["tests"]:
        path = Path(raw_path)
        if path.is_dir():
            files.extend(sorted(path.rglob("test_*.py")))
        elif path.is_file() and path.name.startswith("test_") and path.suffix == ".py":
            files.append(path)
    return files


def load_module(path: Path, index: int):
    spec = importlib.util.spec_from_file_location(f"_pytest_{index}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv: list[str]) -> int:
    for package_path in reversed(PACKAGE_PATHS):
        resolved = str(Path(package_path).resolve())
        if resolved not in sys.path:
            sys.path.insert(0, resolved)

    test_files = iter_test_files(argv[1:])
    total = 0
    failed = 0
    for index, path in enumerate(test_files):
        module = load_module(path, index)
        for name, fn in sorted(inspect.getmembers(module, inspect.isfunction)):
            if not name.startswith("test_"):
                continue
            total += 1
            try:
                fn()
                sys.stdout.write('.')
                sys.stdout.flush()
            except Exception as exc:
                failed += 1
                sys.stdout.write('F')
                sys.stdout.flush()
                sys.stdout.write(f"\n\nFAIL {path}::{name}\n{type(exc).__name__}: {exc}\n")
    sys.stdout.write(f"\n{total - failed} passed, {failed} failed\n")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
