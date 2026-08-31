from __future__ import annotations


def parse_where(expr: str | None):
    if not expr:
        return None, None
    if expr.count("=") != 1:
        raise ValueError(f"Invalid --where expression: {expr!r}. Expected field=value")
    field, value = expr.split("=", 1)
    if not field:
        raise ValueError(f"Invalid --where expression: {expr!r}. Expected field=value")
    return field, value


def compile_predicates(exprs, headers):
    predicates = []
    for expr in exprs or []:
        field, value = parse_where(expr)
        if field not in headers:
            raise ValueError(f"Unknown field in --where: {field}")
        predicates.append((field, value))
    return predicates


def row_matches(row, predicates):
    return all(row[field] == value for field, value in predicates)


def parse_select(fields, headers):
    if not fields:
        return list(headers)
    names = fields.split(",")
    missing = [name for name in names if name not in headers]
    if missing:
        raise ValueError(f"Unknown field in --select: {missing[0]}")
    return names


def select_fields(rows, names):
    return [{name: row[name] for name in names} for row in rows]
