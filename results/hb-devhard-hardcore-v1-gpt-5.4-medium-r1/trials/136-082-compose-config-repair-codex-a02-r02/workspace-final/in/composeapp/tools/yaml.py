from __future__ import annotations

import ast
from typing import Any


def safe_load(text: str) -> Any:
    lines = [_strip_comment(line.rstrip("\n")) for line in text.splitlines()]
    lines = [line.rstrip() for line in lines if line.strip()]
    if not lines:
        return None
    value, index = _parse_block(lines, 0, 0)
    if index != len(lines):
        raise ValueError("unexpected trailing content")
    return value


def _strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    result: list[str] = []
    for char in line:
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            break
        result.append(char)
    return "".join(result)


def _parse_block(lines: list[str], index: int, indent: int) -> tuple[Any, int]:
    if lines[index].lstrip().startswith("- "):
        return _parse_list(lines, index, indent)
    return _parse_dict(lines, index, indent)


def _parse_dict(lines: list[str], index: int, indent: int) -> tuple[dict[str, Any], int]:
    data: dict[str, Any] = {}
    while index < len(lines):
        line = lines[index]
        current_indent = _indent_of(line)
        if current_indent < indent:
            break
        if current_indent != indent:
            raise ValueError(f"invalid indentation: {line!r}")
        stripped = line.strip()
        if stripped.startswith("- "):
            break
        key, _, rest = stripped.partition(":")
        if not _:
            raise ValueError(f"invalid mapping entry: {line!r}")
        rest = rest.strip()
        if rest:
            data[key] = _parse_scalar(rest)
            index += 1
            continue
        index += 1
        if index >= len(lines) or _indent_of(lines[index]) <= indent:
            data[key] = {}
            continue
        data[key], index = _parse_block(lines, index, indent + 2)
    return data, index


def _parse_list(lines: list[str], index: int, indent: int) -> tuple[list[Any], int]:
    items: list[Any] = []
    while index < len(lines):
        line = lines[index]
        current_indent = _indent_of(line)
        if current_indent < indent:
            break
        if current_indent != indent:
            raise ValueError(f"invalid indentation: {line!r}")
        stripped = line.strip()
        if not stripped.startswith("- "):
            break
        rest = stripped[2:].strip()
        if rest:
            items.append(_parse_scalar(rest))
            index += 1
            continue
        index += 1
        if index >= len(lines) or _indent_of(lines[index]) <= indent:
            items.append(None)
            continue
        value, index = _parse_block(lines, index, indent + 2)
        items.append(value)
    return items, index


def _parse_scalar(value: str) -> Any:
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "Null", "none", "None", "~"}:
        return None
    if value.startswith("[") or value.startswith("{"):
        return ast.literal_eval(value)
    if value.startswith(("'", '"')):
        return ast.literal_eval(value)
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))
