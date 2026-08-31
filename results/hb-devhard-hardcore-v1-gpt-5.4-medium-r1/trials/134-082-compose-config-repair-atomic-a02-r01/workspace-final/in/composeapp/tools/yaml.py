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
    while index < len(lines) and not lines[index].strip():
        index += 1
    return index


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _parse_block(lines: list[str], index: int, indent: int):
    index = _skip_blanks(lines, index)
    if index >= len(lines):
        return {}, index
    line = lines[index]
    if _indent(line) < indent:
        return {}, index
    if line.lstrip().startswith("- "):
        return _parse_list(lines, index, indent)
    return _parse_dict(lines, index, indent)


def _parse_dict(lines: list[str], index: int, indent: int):
    result = {}
    while True:
        index = _skip_blanks(lines, index)
        if index >= len(lines):
            break
        line = lines[index]
        current = _indent(line)
        if current < indent:
            break
        if current != indent:
            raise ValueError(f"bad indent at line {index + 1}")
        stripped = line.strip()
        if stripped.startswith("- "):
            break
        if ":" not in stripped:
            raise ValueError(f"bad mapping entry at line {index + 1}")
        key, rest = stripped.split(":", 1)
        key = key.strip()
        rest = rest.strip()
        index += 1
        if rest:
            result[key] = _parse_scalar(rest)
        else:
            child_index = _skip_blanks(lines, index)
            if child_index >= len(lines) or _indent(lines[child_index]) <= indent:
                result[key] = {}
            else:
                result[key], index = _parse_block(lines, child_index, indent + 2)
    return result, index


def _parse_list(lines: list[str], index: int, indent: int):
    result = []
    while True:
        index = _skip_blanks(lines, index)
        if index >= len(lines):
            break
        line = lines[index]
        current = _indent(line)
        if current < indent:
            break
        if current != indent:
            raise ValueError(f"bad list indent at line {index + 1}")
        stripped = line.strip()
        if not stripped.startswith("- "):
            break
        item = stripped[2:].strip()
        index += 1
        if item:
            result.append(_parse_scalar(item))
        else:
            child_index = _skip_blanks(lines, index)
            if child_index >= len(lines) or _indent(lines[child_index]) <= indent:
                result.append(None)
            else:
                child, index = _parse_block(lines, child_index, indent + 2)
                result.append(child)
    return result, index


def _parse_scalar(value: str):
    if not value:
        return ""
    if value[0] in ('"', "'", "[", "{"):
        return ast.literal_eval(value)
    lowered = value.lower()
    if lowered == "null":
        return None
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    return value
