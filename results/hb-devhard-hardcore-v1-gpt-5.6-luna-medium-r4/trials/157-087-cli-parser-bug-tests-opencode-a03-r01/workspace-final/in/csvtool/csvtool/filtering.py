from __future__ import annotations


def parse_where(expr: str | None):
    if not expr:
        return lambda row: True
    if "=" not in expr:
        raise ValueError("invalid --where expression; expected field=value")
    field, value = expr.split("=", 1)
    field = field.strip()
    if not field:
        raise ValueError("invalid --where expression; field is required")
    return lambda row: row[field] == value


def select_fields(rows, fields):
    if not fields:
        return rows
    names = fields.split(",")
    return [{name: row.get(name, "") for name in names} for row in rows]
