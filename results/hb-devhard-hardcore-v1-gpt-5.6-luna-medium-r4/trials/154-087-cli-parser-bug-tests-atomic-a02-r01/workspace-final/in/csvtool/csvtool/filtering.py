from __future__ import annotations


def parse_where(expr: str | None):
    if not expr:
        return lambda row: True
    if expr.count("=") != 1:
        raise ValueError(f"invalid --where expression: {expr!r} (expected field=value)")
    field, value = (part.strip() for part in expr.split("=", 1))
    if not field:
        raise ValueError(f"invalid --where expression: {expr!r} (missing field)")
    return lambda row: row.get(field) == value


def select_fields(rows, fields, headers=None):
    available = headers if headers is not None else (list(rows[0]) if rows else [])
    if not fields:
        if headers is None:
            return rows
        return rows, list(available)
    names = [name.strip() for name in fields.split(",")]
    missing = [name for name in names if name not in available]
    if missing:
        raise ValueError(f"select field not found: {', '.join(missing)}")
    selected = [{name: row[name] for name in names} for row in rows]
    return (selected, names) if headers is not None else selected
