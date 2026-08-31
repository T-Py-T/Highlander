"""Minimal YAML subset loader for local validation.

This supports the mapping/list/scalar structures used by this workspace's
compose and policy files so `tools/validate_compose.py` can run offline
without an external PyYAML install.
"""

from __future__ import annotations

import ast


def safe_load(text: str):
    lines = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        lines.append((indent, raw.strip()))
    value, index = _parse_block(lines, 0, 0)
    if index != len(lines):
        raise ValueError("unexpected trailing YAML content")
    return value


def _parse_block(lines, index, indent):
    if index >= len(lines):
        return {}, index
    current_indent, content = lines[index]
    if current_indent != indent:
        raise ValueError("invalid indentation")
    if content.startswith("- "):
        return _parse_list(lines, index, indent)
    return _parse_dict(lines, index, indent)


def _parse_dict(lines, index, indent):
    result = {}
    while index < len(lines):
        current_indent, content = lines[index]
        if current_indent < indent:
            break
        if current_indent != indent:
            raise ValueError("invalid nested mapping indentation")
        if content.startswith("- ") or ":" not in content:
            raise ValueError("expected mapping entry")
        key, rest = content.split(":", 1)
        key = key.strip()
        rest = rest.strip()
        index += 1
        if rest:
            result[key] = _parse_scalar(rest)
            continue
        if index >= len(lines) or lines[index][0] <= indent:
            result[key] = {}
            continue
        result[key], index = _parse_block(lines, index, lines[index][0])
    return result, index


def _parse_list(lines, index, indent):
    result = []
    while index < len(lines):
        current_indent, content = lines[index]
        if current_indent < indent:
            break
        if current_indent != indent or not content.startswith("- "):
            raise ValueError("expected list entry")
        result.append(_parse_scalar(content[2:].strip()))
        index += 1
    return result, index


def _parse_scalar(value: str):
    if value.startswith("[") and value.endswith("]"):
        return ast.literal_eval(value)
    if value.startswith(("'", '"')):
        return ast.literal_eval(value)
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "~"}:
        return None
    try:
        return int(value)
    except ValueError:
        return value
