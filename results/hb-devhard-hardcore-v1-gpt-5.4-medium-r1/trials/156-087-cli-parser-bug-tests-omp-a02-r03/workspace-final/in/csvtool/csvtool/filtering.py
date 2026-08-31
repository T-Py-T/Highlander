from __future__ import annotations

from typing import Iterable


class FilterError(ValueError):
    pass


def parse_where(expr: str) -> tuple[str, str]:
    if "=" not in expr:
        raise FilterError(f"Invalid --where expression: {expr!r}. Expected field=value.")
    field, value = expr.split("=", 1)
    if not field:
        raise FilterError(f"Invalid --where expression: {expr!r}. Field name is required.")
    return field, value


def build_predicates(expressions: Iterable[str] | None, headers: list[str]) -> list[tuple[str, str]]:
    predicates = []
    for expr in expressions or []:
        field, value = parse_where(expr)
        if field not in headers:
            raise FilterError(f"Unknown field for --where: {field}")
        predicates.append((field, value))
    return predicates


def apply_predicates(rows, predicates):
    if not predicates:
        return list(rows)
    return [row for row in rows if all(row[field] == value for field, value in predicates)]


def select_fields(rows, fields, headers):
    if not fields:
        return list(rows), list(headers)
    names = fields.split(",")
    missing = [name for name in names if name not in headers]
    if missing:
        raise FilterError(f"Unknown field for --select: {missing[0]}")
    return [{name: row[name] for name in names} for row in rows], names
