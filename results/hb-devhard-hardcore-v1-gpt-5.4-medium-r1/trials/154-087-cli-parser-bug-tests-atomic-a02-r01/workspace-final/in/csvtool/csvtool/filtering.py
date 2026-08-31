from __future__ import annotations

from collections.abc import Iterable


class CliUsageError(ValueError):
    """Raised for invalid CLI field names or filter expressions."""


def require_fields(available_fields, requested_fields, *, context):
    missing = [field for field in requested_fields if field not in available_fields]
    if missing:
        missing_list = ", ".join(missing)
        raise CliUsageError(f"{context} field not found: {missing_list}")


def parse_where(expressions: Iterable[str] | None, available_fields):
    if not expressions:
        return []

    predicates = []
    for expr in expressions:
        if expr.count("=") != 1:
            raise CliUsageError(f"bad --where expression: {expr!r}; expected FIELD=VALUE")
        field, value = expr.split("=", 1)
        if not field:
            raise CliUsageError(f"bad --where expression: {expr!r}; expected FIELD=VALUE")
        require_fields(available_fields, [field], context="filter")
        predicates.append((field, value))
    return predicates


def apply_where(rows, predicates):
    if not predicates:
        return rows
    return [row for row in rows if all(row[field] == value for field, value in predicates)]


def parse_select(fields: str | None, available_fields):
    if not fields:
        return list(available_fields)
    names = fields.split(",")
    require_fields(available_fields, names, context="select")
    return names


def select_fields(rows, field_names):
    return [{name: row[name] for name in field_names} for row in rows]
