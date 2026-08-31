from __future__ import annotations


class CliUsageError(ValueError):
    pass


def parse_where(expressions, headers):
    predicates = []
    header_set = set(headers)

    for expr in expressions or []:
        if "=" not in expr:
            raise CliUsageError(f"invalid --where expression: {expr!r}; expected FIELD=VALUE")
        field, value = expr.split("=", 1)
        if not field:
            raise CliUsageError(f"invalid --where expression: {expr!r}; missing field name")
        if field not in header_set:
            raise CliUsageError(f"unknown field in --where: {field}")
        predicates.append((field, value))

    return lambda row: all(row[field] == value for field, value in predicates)


def select_fields(rows, fields, headers):
    if not fields:
        return rows, list(headers)

    names = fields.split(",")
    header_set = set(headers)
    for name in names:
        if name not in header_set:
            raise CliUsageError(f"unknown field in --select: {name}")

    return [{name: row[name] for name in names} for row in rows], names


def parse_sort(field, headers):
    if not field:
        return None, False

    descending = field.startswith("-")
    name = field[1:] if descending else field
    if not name:
        raise CliUsageError("invalid --sort field: empty field name")
    if name not in set(headers):
        raise CliUsageError(f"unknown field in --sort: {name}")
    return name, descending


def sort_value(value):
    try:
        return (0, float(value))
    except (TypeError, ValueError):
        return (1, value)
