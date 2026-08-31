from __future__ import annotations

import importlib.util
import inspect
import pathlib
import sys
import traceback


def _load_module(path: pathlib.Path, index: int):
    name = f"_pytest_shim_{index}_{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _iter_test_files(args: list[str]):
    roots = [pathlib.Path(arg) for arg in args] or [pathlib.Path("tests")]
    for root in roots:
        if root.is_file() and root.name.startswith("test") and root.suffix == ".py":
            yield root
            continue
        if root.is_dir():
            for path in sorted(root.rglob("test*.py")):
                if path.is_file():
                    yield path


def main(argv: list[str]) -> int:
    failures = 0
    total = 0
    for index, path in enumerate(_iter_test_files(argv[1:]), start=1):
        module = _load_module(path, index)
        for name, func in sorted(inspect.getmembers(module, inspect.isfunction)):
            if not name.startswith("test_"):
                continue
            total += 1
            try:
                func()
                sys.stdout.write(".")
                sys.stdout.flush()
            except Exception:
                failures += 1
                sys.stdout.write("F")
                sys.stdout.flush()
                sys.stdout.write(f"\n\nFAIL: {path}::{name}\n")
                traceback.print_exc()
    sys.stdout.write(f"\n{total} tests collected\n")
    if failures:
        sys.stdout.write(f"{failures} failed, {total - failures} passed\n")
        return 1
    sys.stdout.write(f"{total} passed\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
