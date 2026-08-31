from __future__ import annotations

import ast
from typing import Any


def safe_load(text: str) -> Any:
    lines = text.splitlines()
    value, index = _parse_block(lines, 0, 0)
    index = _skip_blanks(lines, index)
    if index != len(lines):
        raise ValueError(f"unexpected content at line {index + 1}")
    return value


def _skip_blanks(lines: list[str], index: int) -> int:
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped and not stripped.startswith("#"):
            break
        index += 1
    return index


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _parse_block(lines: list[str], index: int, indent: int) -> tuple[Any, int]:
    index = _skip_blanks(lines, index)
    if index >= len(lines):
        return {}, index
    line = lines[index]
    current_indent = _indent_of(line)
    if current_indent < indent:
        return {}, index
    stripped = line.strip()
    if stripped.startswith("- "):
        return _parse_list(lines, index, indent)
    return _parse_dict(lines, index, indent)


def _parse_list(lines: list[str], index: int, indent: int) -> tuple[list[Any], int]:
    items: list[Any] = []
    while True:
        index = _skip_blanks(lines, index)
        if index >= len(lines):
            return items, index
        line = lines[index]
        current_indent = _indent_of(line)
        if current_indent < indent:
            return items, index
        if current_indent != indent:
            raise ValueError(f"invalid list indentation at line {index + 1}")
        stripped = line.strip()
        if not stripped.startswith("- "):
            return items, index
        content = stripped[2:].strip()
        index += 1
        if not content:
            nested, index = _parse_block(lines, index, indent + 2)
            items.append(nested)
            continue
        items.append(_parse_scalar(content))


def _parse_dict(lines: list[str], index: int, indent: int) -> tuple[dict[str, Any], int]:
    mapping: dict[str, Any] = {}
    while True:
        index = _skip_blanks(lines, index)
        if index >= len(lines):
            return mapping, index
        line = lines[index]
        current_indent = _indent_of(line)
        if current_indent < indent:
            return mapping, index
        if current_indent != indent:
            raise ValueError(f"invalid mapping indentation at line {index + 1}")
        stripped = line.strip()
        if stripped.startswith("- "):
            return mapping, index
        if ":" not in stripped:
            raise ValueError(f"expected key/value at line {index + 1}")
        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        index += 1
        if raw_value:
            mapping[key] = _parse_scalar(raw_value)
            continue
        next_index = _skip_blanks(lines, index)
        if next_index >= len(lines) or _indent_of(lines[next_index]) <= indent:
            mapping[key] = None
            index = next_index
            continue
        nested, index = _parse_block(lines, next_index, indent + 2)
        mapping[key] = nested


def _parse_scalar(value: str) -> Any:
    if value in {"null", "Null", "NULL", "~"}:
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    if value.startswith("[") or value.startswith("{") or value.startswith(('"', "'")):
        return ast.literal_eval(value)
    try:
        return int(value)
    except ValueError:
        pass
    return value
