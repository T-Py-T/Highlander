from __future__ import annotations

import ast
from typing import Any


def safe_load(text: str) -> Any:
    lines = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        lines.append((indent, raw[indent:]))
    value, index = _parse_block(lines, 0, 0)
    if index != len(lines):
        raise ValueError("trailing content")
    return value


def _parse_block(lines: list[tuple[int, str]], index: int, indent: int):
    if index >= len(lines):
        return {}, index
    current_indent, current_text = lines[index]
    if current_indent != indent:
        raise ValueError(f"bad indentation at line: {current_text!r}")
    if current_text.startswith("- "):
        return _parse_list(lines, index, indent)
    return _parse_dict(lines, index, indent)


def _parse_dict(lines: list[tuple[int, str]], index: int, indent: int):
    data = {}
    while index < len(lines):
        current_indent, text = lines[index]
        if current_indent < indent:
            break
        if current_indent != indent:
            raise ValueError(f"bad indentation at line: {text!r}")
        if text.startswith("- "):
            break
        if ":" not in text:
            raise ValueError(f"expected key/value pair: {text!r}")
        key, remainder = text.split(":", 1)
        key = key.strip()
        remainder = remainder.strip()
        index += 1
        if remainder:
            data[key] = _parse_scalar(remainder)
            continue
        if index < len(lines) and lines[index][0] > indent:
            data[key], index = _parse_block(lines, index, lines[index][0])
        else:
            data[key] = {}
    return data, index


def _parse_list(lines: list[tuple[int, str]], index: int, indent: int):
    items = []
    while index < len(lines):
        current_indent, text = lines[index]
        if current_indent < indent:
            break
        if current_indent != indent:
            raise ValueError(f"bad indentation at line: {text!r}")
        if not text.startswith("- "):
            break
        remainder = text[2:].strip()
        index += 1
        if remainder:
            items.append(_parse_scalar(remainder))
            continue
        if index < len(lines) and lines[index][0] > indent:
            item, index = _parse_block(lines, index, lines[index][0])
            items.append(item)
        else:
            items.append(None)
    return items, index


def _parse_scalar(value: str):
    if value.startswith(("'", '"', "[", "{")):
        return ast.literal_eval(value)
    lowered = value.lower()
    if lowered == "null":
        return None
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value
