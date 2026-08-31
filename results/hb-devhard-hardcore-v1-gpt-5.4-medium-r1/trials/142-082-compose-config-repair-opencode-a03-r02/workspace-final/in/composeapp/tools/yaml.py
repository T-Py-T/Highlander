from __future__ import annotations


def safe_load(text: str):
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if line:
            lines.append(line)
    value, _ = _parse_block(lines, 0, 0)
    return value


def _parse_block(lines: list[str], index: int, indent: int):
    if index >= len(lines):
        return {}, index
    stripped = lines[index].lstrip()
    if stripped.startswith("- "):
        return _parse_list(lines, index, indent)
    return _parse_dict(lines, index, indent)


def _parse_dict(lines: list[str], index: int, indent: int):
    result = {}
    while index < len(lines):
        line = lines[index]
        current_indent = _indent(line)
        if current_indent < indent:
            break
        if current_indent > indent:
            raise ValueError(f"unexpected indentation: {line}")

        content = line.strip()
        if content.startswith("- "):
            break

        key, sep, remainder = content.partition(":")
        if not sep:
            raise ValueError(f"invalid mapping entry: {line}")

        remainder = remainder.strip()
        index += 1
        if remainder:
            result[key] = _parse_scalar(remainder)
            continue

        if index < len(lines) and _indent(lines[index]) > indent:
            result[key], index = _parse_block(lines, index, indent + 2)
        else:
            result[key] = None
    return result, index


def _parse_list(lines: list[str], index: int, indent: int):
    result = []
    while index < len(lines):
        line = lines[index]
        current_indent = _indent(line)
        if current_indent < indent:
            break
        if current_indent != indent:
            raise ValueError(f"unexpected indentation: {line}")

        content = line.strip()
        if not content.startswith("- "):
            break

        remainder = content[2:].strip()
        if remainder:
            result.append(_parse_scalar(remainder))
            index += 1
            continue

        index += 1
        item, index = _parse_block(lines, index, indent + 2)
        result.append(item)
    return result, index


def _parse_scalar(value: str):
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part.strip()) for part in inner.split(",")]
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    if value in {"null", "~"}:
        return None
    return value


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))
