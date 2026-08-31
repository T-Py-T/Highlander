from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import ast


@dataclass
class _Line:
    indent: int
    text: str


def safe_load(text: str) -> Any:
    lines = _prepare(text)
    if not lines:
        return None
    value, index = _parse_block(lines, 0, lines[0].indent)
    if index != len(lines):
        raise ValueError(f"unexpected trailing content at line {index + 1}")
    return value


def _prepare(text: str) -> list[_Line]:
    prepared: list[_Line] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent % 2:
            raise ValueError("only even indentation is supported")
        prepared.append(_Line(indent, raw[indent:]))
    return prepared


def _parse_block(lines: list[_Line], index: int, indent: int) -> tuple[Any, int]:
    if lines[index].indent != indent:
        raise ValueError(f"unexpected indentation at line {index + 1}")
    if lines[index].text.startswith("- "):
        return _parse_list(lines, index, indent)
    return _parse_dict(lines, index, indent)


def _parse_dict(lines: list[_Line], index: int, indent: int) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}
    while index < len(lines):
        line = lines[index]
        if line.indent < indent:
            break
        if line.indent > indent:
            raise ValueError(f"unexpected indentation at line {index + 1}")
        if line.text.startswith("- "):
            break
        key, sep, remainder = line.text.partition(":")
        if not sep:
            raise ValueError(f"missing ':' in mapping at line {index + 1}")
        key = key.strip()
        remainder = remainder.strip()
        index += 1
        if remainder:
            result[key] = _parse_scalar(remainder)
            continue
        if index >= len(lines) or lines[index].indent <= indent:
            result[key] = {}
            continue
        value, index = _parse_block(lines, index, lines[index].indent)
        result[key] = value
    return result, index


def _parse_list(lines: list[_Line], index: int, indent: int) -> tuple[list[Any], int]:
    result: list[Any] = []
    while index < len(lines):
        line = lines[index]
        if line.indent < indent:
            break
        if line.indent != indent or not line.text.startswith("- "):
            raise ValueError(f"unexpected list item indentation at line {index + 1}")
        remainder = line.text[2:].strip()
        index += 1
        if not remainder:
            if index >= len(lines) or lines[index].indent <= indent:
                result.append(None)
                continue
            value, index = _parse_block(lines, index, lines[index].indent)
            result.append(value)
            continue
        result.append(_parse_scalar(remainder))
    return result, index


def _parse_scalar(value: str) -> Any:
    if value.startswith("[") and value.endswith("]"):
        return ast.literal_eval(value)
    if value.startswith(("\"", "'")):
        return ast.literal_eval(value)
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "~"}:
        return None
    if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
        return int(value)
    return value
