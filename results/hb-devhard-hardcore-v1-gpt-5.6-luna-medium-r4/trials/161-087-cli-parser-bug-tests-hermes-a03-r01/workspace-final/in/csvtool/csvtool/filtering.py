from __future__ import annotations

from collections.abc import Callable, Iterable


Predicate = Callable[[dict[str, str]], bool]


def parse_where(expr: str | None) -> Predicate:
    """Parse one FIELD=VALUE expression into a row predicate."""
    if expr is None or expr == "":
        return lambda row: True
    if expr.count("=") != 1:
        raise ValueError(
            f"invalid --where expression {expr!r}; expected FIELD=VALUE"
        )
    field, value = expr.split("=", 1)
    if not field:
        raise ValueError(
            f"invalid --where expression {expr!r}; field name cannot be empty"
        )
    return lambda row: row[field] == value


def select_fields(rows: Iterable[dict[str, str]], fields: str | None):
    if not fields:
        return list(rows)
    names = fields.split(",")
    if any(not name for name in names):
        raise ValueError("invalid --select: field names cannot be empty")
    return [{name: row[name] for name in names} for row in rows]
