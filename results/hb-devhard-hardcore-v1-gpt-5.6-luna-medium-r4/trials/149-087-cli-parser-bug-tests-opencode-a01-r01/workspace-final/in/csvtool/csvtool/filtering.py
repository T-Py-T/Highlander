from __future__ import annotations


def parse_where(expr: str | None):
    if not expr:
        return lambda row: True
    if expr.count("=") != 1:
        raise ValueError("where expression must have the form field=value")
    field, value = expr.split("=", 1)
    if not field:
        raise ValueError("where expression must name a field")
    return lambda row: row.get(field) == value


def select_fields(rows, fields):
    if not fields:
        return rows
    names = fields.split(",")
    return [{name: row[name] for name in names} for row in rows]
