from __future__ import annotations


def parse_where(expr: str | None):
    if expr is None or expr == "":
        predicate = lambda row: True
        predicate.field = None
        return predicate
    if expr.count("=") != 1:
        raise ValueError(f"invalid --where expression {expr!r}; expected field=value")
    field, value = expr.split("=", 1)
    if not field:
        raise ValueError(f"invalid --where expression {expr!r}; field is required")
    predicate = lambda row: row.get(field) == value
    predicate.field = field
    return predicate

def select_fields(rows, fields):
    if not fields:
        return rows
    names = fields.split(",")
    return [{name: row.get(name, "") for name in names} for row in rows]
