from __future__ import annotations


def parse_where(expr: str | None):
    if not expr:
        return None
    if "=" not in expr:
        raise ValueError(f"invalid --where expression {expr!r}; expected FIELD=VALUE")
    field, value = expr.split("=", 1)
    if not field:
        raise ValueError(f"invalid --where expression {expr!r}; field name is required")
    return field, value


def build_predicate(filters):
    if not filters:
        return lambda row: True
    return lambda row: all(row[field] == value for field, value in filters)


def select_fields(rows, fields):
    if not fields:
        return rows
    names = fields.split(",")
    return [{name: row[name] for name in names} for row in rows]
