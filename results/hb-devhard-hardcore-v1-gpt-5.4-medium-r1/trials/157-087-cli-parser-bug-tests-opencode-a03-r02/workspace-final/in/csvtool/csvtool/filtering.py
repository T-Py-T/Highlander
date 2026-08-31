from __future__ import annotations


def parse_where(expr: str) -> tuple[str, str]:
    if "=" not in expr:
        raise ValueError(f"invalid --where expression: {expr!r}; expected field=value")

    field, value = expr.split("=", 1)
    if not field:
        raise ValueError(f"invalid --where expression: {expr!r}; field name is required")
    return field, value


def parse_select(fields: str | None) -> list[str] | None:
    if not fields:
        return None

    names = fields.split(",")
    if any(not name for name in names):
        raise ValueError("invalid --select value: field names must be non-empty")
    return names
