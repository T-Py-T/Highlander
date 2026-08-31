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
    current = lines[index]
    if _indent_of(current) < indent:
        return {}, index
    if current.lstrip().startswith("- "):
        return _parse_list(lines, index, indent)
    return _parse_dict(lines, index, indent)


def _parse_dict(lines: list[str], index: int, indent: int) -> tuple[dict[str, Any], int]:
    data: dict[str, Any] = {}
    while True:
        index = _skip_blanks(lines, index)
        if index >= len(lines):
            return data, index
        line = lines[index]
        line_indent = _indent_of(line)
        if line_indent < indent:
            return data, index
        if line_indent != indent:
            raise ValueError(f"invalid indentation at line {index + 1}")
        stripped = line.strip()
        if stripped.startswith("- "):
            return data, index
        if ":" not in stripped:
            raise ValueError(f"expected key/value at line {index + 1}")
        key, rest = stripped.split(":", 1)
        rest = rest.strip()
        index += 1
        if rest:
            data[key] = _parse_scalar(rest)
            continue
        child_index = _skip_blanks(lines, index)
        if child_index >= len(lines) or _indent_of(lines[child_index]) <= indent:
            data[key] = {}
            index = child_index
            continue
        data[key], index = _parse_block(lines, child_index, indent + 2)


def _parse_list(lines: list[str], index: int, indent: int) -> tuple[list[Any], int]:
    data: list[Any] = []
    while True:
        index = _skip_blanks(lines, index)
        if index >= len(lines):
            return data, index
        line = lines[index]
        line_indent = _indent_of(line)
        if line_indent < indent:
            return data, index
        if line_indent != indent:
            raise ValueError(f"invalid list indentation at line {index + 1}")
        stripped = line.strip()
        if not stripped.startswith("- "):
            return data, index
        item = stripped[2:].strip()
        index += 1
        if item:
            data.append(_parse_scalar(item))
            continue
        child_index = _skip_blanks(lines, index)
        if child_index >= len(lines) or _indent_of(lines[child_index]) <= indent:
            data.append(None)
            index = child_index
            continue
        child, index = _parse_block(lines, child_index, indent + 2)
        data.append(child)


def _parse_scalar(value: str) -> Any:
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "Null", "~"}:
        return None
    if value.startswith("[") or value.startswith("{") or value.startswith(("'", '"')):
        return ast.literal_eval(value)
    return value
