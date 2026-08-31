from __future__ import annotations


def parse_where(expr: str) -> tuple[str, str]:
    if expr.count("=") != 1:
        raise ValueError(f"bad --where expression: {expr!r}; expected field=value")

    field, value = expr.split("=", 1)
    if not field:
        raise ValueError(f"bad --where expression: {expr!r}; expected field=value")
    return field, value


def select_fields(rows, fields, headers):
    if not fields:
        return headers, rows

    names = fields.split(",")
    missing = [name for name in names if name not in headers]
    if missing:
        raise ValueError(f"missing field: {missing[0]}")
    return names, [{name: row[name] for name in names} for row in rows]
