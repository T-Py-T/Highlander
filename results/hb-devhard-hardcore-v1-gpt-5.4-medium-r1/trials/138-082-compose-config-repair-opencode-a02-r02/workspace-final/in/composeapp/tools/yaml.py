from __future__ import annotations

import ast


def safe_load(text: str):
    lines = []
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        lines.append((indent, raw_line.strip()))
    if not lines:
        return None
    value, _ = _parse_block(lines, 0, lines[0][0])
    return value


def _parse_block(lines, index, indent):
    if lines[index][1].startswith("- "):
        items = []
        while index < len(lines):
            line_indent, content = lines[index]
            if line_indent != indent or not content.startswith("- "):
                break
            item_text = content[2:].strip()
            if not item_text:
                item, index = _parse_block(lines, index + 1, indent + 2)
                items.append(item)
                continue
            items.append(_parse_scalar(item_text))
            index += 1
        return items, index

    mapping = {}
    while index < len(lines):
        line_indent, content = lines[index]
        if line_indent < indent:
            break
        if line_indent > indent:
            raise ValueError(f"unexpected indentation: {content}")
        key, _, remainder = content.partition(":")
        key = key.strip()
        remainder = remainder.strip()
        index += 1
        if remainder:
            mapping[key] = _parse_scalar(remainder)
            continue
        if index < len(lines) and lines[index][0] > indent:
            mapping[key], index = _parse_block(lines, index, lines[index][0])
        else:
            mapping[key] = None
    return mapping, index


def _parse_scalar(value: str):
    if value.startswith("[") or value.startswith("{"):
        return ast.literal_eval(value)
    if value.startswith(('"', "'")):
        return ast.literal_eval(value)
    if value in {"true", "false"}:
        return value == "true"
    if value in {"null", "~"}:
        return None
    try:
        return int(value)
    except ValueError:
        return value
