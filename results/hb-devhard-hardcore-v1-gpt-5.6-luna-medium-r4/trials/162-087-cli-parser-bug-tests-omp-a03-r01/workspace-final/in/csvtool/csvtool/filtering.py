from __future__ import annotations


class FieldError(ValueError):
    """Raised when a requested CSV field does not exist."""


def parse_where(expr: str | None):
    if expr is None:
        return lambda row: True
    if expr.count("=") != 1:
        raise ValueError(f"invalid --where expression {expr!r}; expected FIELD=VALUE")
    field, value = expr.split("=", 1)
    if not field:
        raise ValueError(f"invalid --where expression {expr!r}; field is required")
    return lambda row: row[field] == value




def select_fields(rows, fields):
    if not fields:
        return rows
    names = fields.split(",")
    if any(not name for name in names):
        raise ValueError("invalid --select value; expected comma-separated field names")
    if rows:
        missing = next((name for name in names if name not in rows[0]), None)
        if missing is not None:
            raise FieldError(f"--select field {missing!r} not found in CSV")
    return [{name: row[name] for name in names} for row in rows]
