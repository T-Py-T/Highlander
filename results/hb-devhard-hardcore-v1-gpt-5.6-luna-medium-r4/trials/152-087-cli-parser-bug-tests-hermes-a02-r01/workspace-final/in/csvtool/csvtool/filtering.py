from __future__ import annotations

from collections.abc import Iterable, Mapping


def parse_where(expr: str | None, fields: Iterable[str] | None = None):
    """Build a predicate for a single ``field=value`` expression."""
    if not expr:
        return lambda row: True

    if expr.count("=") != 1:
        raise ValueError(f"invalid --where expression {expr!r}; expected field=value")
    field, value = expr.split("=", 1)
    field = field.strip()
    if not field:
        raise ValueError(f"invalid --where expression {expr!r}; field is missing")
    if fields is not None and field not in fields:
        raise ValueError(f"unknown field {field!r} in --where expression")

    return lambda row: row[field] == value


def select_fields(rows: list[Mapping[str, str]], fields: str | None, available_fields: Iterable[str] | None = None):
    if not fields:
        return rows
    names = [name.strip() for name in fields.split(",")]
    if any(not name for name in names):
        raise ValueError("--select contains an empty field name")
    if available_fields is not None:
        available = set(available_fields)
        missing = [name for name in names if name not in available]
        if missing:
            raise ValueError(f"unknown field(s) in --select: {', '.join(missing)}")
    return [{name: row[name] for name in names} for row in rows]
