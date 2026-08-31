from __future__ import annotations

from collections.abc import Callable, Iterable


def parse_where(expr: str | None) -> Callable[[dict[str, str]], bool]:
    """Build a predicate for a single ``field=value`` expression."""
    if expr is None or expr == "":
        return lambda row: True
    if expr.count("=") != 1:
        raise ValueError("bad --where expression; expected field=value")
    field, value = expr.split("=", 1)
    field = field.strip()
    if not field:
        raise ValueError("bad --where expression; field must not be empty")
    return lambda row: row[field] == value


def select_fields(rows: Iterable[dict[str, str]], fields: str | None):
    if not fields:
        return list(rows)
    names = [name.strip() for name in fields.split(",")]
    if any(not name for name in names):
        raise ValueError("bad --select expression; expected comma-separated field names")
    return [{name: row[name] for name in names} for row in rows]
