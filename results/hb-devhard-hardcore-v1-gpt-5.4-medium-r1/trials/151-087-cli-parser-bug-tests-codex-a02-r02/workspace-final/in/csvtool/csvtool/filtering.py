from __future__ import annotations


def parse_where(expr: str | None):
    if not expr:
        return None
    if "=" not in expr:
        raise ValueError(f"Invalid --where expression: {expr!r}. Expected FIELD=VALUE.")
    field, value = expr.split("=", 1)
    if not field:
        raise ValueError(f"Invalid --where expression: {expr!r}. Field name is required.")
    return field, value


def select_fields(rows, fields, available_fields):
    if not fields:
        return list(rows), list(available_fields)
    names = fields.split(",")
    missing = [name for name in names if name not in available_fields]
    if missing:
        raise ValueError(f"Unknown field(s): {', '.join(missing)}")
    return [{name: row[name] for name in names} for row in rows], names
