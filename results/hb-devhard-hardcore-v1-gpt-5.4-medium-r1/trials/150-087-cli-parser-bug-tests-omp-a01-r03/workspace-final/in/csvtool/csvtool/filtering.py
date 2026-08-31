from __future__ import annotations


class CsvToolError(ValueError):
    pass


def _require_field(field: str, headers: list[str], context: str) -> None:
    if field not in headers:
        raise CsvToolError(f"{context}: unknown field '{field}'")


def parse_where(expressions: list[str] | None, headers: list[str]):
    if not expressions:
        return lambda row: True

    predicates = []
    for expr in expressions:
        if "=" not in expr:
            raise CsvToolError(f"invalid --where expression '{expr}'; expected field=value")
        field, value = expr.split("=", 1)
        if not field:
            raise CsvToolError(f"invalid --where expression '{expr}'; field name is empty")
        _require_field(field, headers, "--where")
        predicates.append((field, value))

    return lambda row: all(row[field] == value for field, value in predicates)


def parse_select(fields: str | None, headers: list[str]) -> list[str]:
    if not fields:
        return list(headers)

    names = fields.split(",")
    for name in names:
        _require_field(name, headers, "--select")
    return names


def select_fields(rows, names):
    return [{name: row[name] for name in names} for row in rows]
