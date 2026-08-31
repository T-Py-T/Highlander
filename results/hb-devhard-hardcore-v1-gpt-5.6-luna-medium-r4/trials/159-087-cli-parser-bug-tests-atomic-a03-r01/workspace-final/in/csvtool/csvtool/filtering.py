from __future__ import annotations


def parse_where(expr: str | None):
    if expr is None:
        return lambda row: True
    if "=" not in expr:
        raise ValueError(f"malformed --where expression (expected FIELD=VALUE): {expr}")
    field, value = expr.split("=", 1)
    return lambda row: row.get(field) == value


def select_fields(rows, fields):
    if not fields:
        return rows
    names = fields.split(",")
    return [{name: row.get(name, "") for name in names} for row in rows]
