from __future__ import annotations


def parse_where(expr: str):
    if "=" not in expr:
        raise ValueError("Invalid --where expression: expected field=value")
    field, value = expr.split("=", 1)
    if not field:
        raise ValueError("Invalid --where expression: expected field=value")
    return field, value


def compile_predicates(expressions):
    predicates = [parse_where(expr) for expr in expressions]

    def matches(row):
        return all(row[field] == value for field, value in predicates)

    return matches


def select_fields(rows, fields):
    if not fields:
        return rows
    names = fields.split(",")
    return [{name: row[name] for name in names} for row in rows]
