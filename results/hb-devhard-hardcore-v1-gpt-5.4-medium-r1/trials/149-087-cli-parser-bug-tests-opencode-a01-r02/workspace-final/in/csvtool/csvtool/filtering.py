from __future__ import annotations


def parse_where(expressions, headers):
    predicates = []
    known_fields = set(headers)

    for expr in expressions or []:
        if "=" not in expr:
            raise ValueError(f"invalid --where expression: {expr!r}; expected FIELD=VALUE")

        field, value = expr.split("=", 1)
        if not field:
            raise ValueError(f"invalid --where expression: {expr!r}; field name is required")
        if field not in known_fields:
            raise ValueError(f"unknown field in --where: {field}")

        predicates.append((field, value))

    return lambda row: all(row[field] == value for field, value in predicates)


def select_fields(rows, fields, headers):
    if not fields:
        return rows, list(headers)

    names = fields.split(",")
    known_fields = set(headers)
    missing = [name for name in names if name not in known_fields]
    if missing:
        raise ValueError(f"unknown field in --select: {missing[0]}")

    return [{name: row[name] for name in names} for row in rows], names
