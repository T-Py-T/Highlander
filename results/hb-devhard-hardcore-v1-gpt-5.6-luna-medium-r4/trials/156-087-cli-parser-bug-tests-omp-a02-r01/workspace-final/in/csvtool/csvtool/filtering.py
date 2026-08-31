from __future__ import annotations


def parse_where(expr: str | None, headers=None):
    if expr is None:
        return lambda row: True
    if expr.count("=") != 1:
        raise ValueError(f"invalid --where expression {expr!r}; expected FIELD=VALUE")
    field, value = expr.split("=", 1)
    field = field.strip()
    if not field:
        raise ValueError(f"invalid --where expression {expr!r}; field is empty")
    if headers is not None and field not in headers:
        raise ValueError(f"unknown field {field!r} in --where")
    return lambda row: row[field] == value


def select_fields(rows, fields, headers=None):
    if not fields:
        return rows
    names = [name.strip() for name in fields.split(",")]
    if any(not name for name in names):
        raise ValueError("invalid --select; fields must be non-empty")
    available = headers if headers is not None else (rows[0].keys() if rows else ())
    missing = [name for name in names if name not in available]
    if missing:
        raise ValueError(f"unknown field(s) in --select: {', '.join(missing)}")
    return [{name: row[name] for name in names} for row in rows]


