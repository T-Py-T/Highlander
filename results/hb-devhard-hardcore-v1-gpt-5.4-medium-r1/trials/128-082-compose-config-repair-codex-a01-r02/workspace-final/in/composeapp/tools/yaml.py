from __future__ import annotations

import ast


def safe_load(text: str):
    lines = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append((len(raw) - len(raw.lstrip(" ")), raw.rstrip()))
    if not lines:
        return None
    value, _ = _parse_block(lines, 0, lines[0][0])
    return value


def _parse_block(lines, index, indent):
    if lines[index][1].lstrip().startswith("- "):
        return _parse_list(lines, index, indent)
    return _parse_dict(lines, index, indent)


def _parse_dict(lines, index, indent):
    result = {}
    while index < len(lines):
      line_indent, raw = lines[index]
      if line_indent < indent:
          break
      if line_indent != indent:
          raise ValueError(f"unexpected indent: {raw}")
      content = raw[indent:]
      if content.startswith("- "):
          break
      key, sep, rest = content.partition(":")
      if not sep:
          raise ValueError(f"invalid mapping entry: {raw}")
      key = key.strip()
      rest = rest.strip()
      index += 1
      if rest:
          result[key] = _parse_scalar(rest)
          continue
      if index < len(lines) and lines[index][0] > indent:
          result[key], index = _parse_block(lines, index, lines[index][0])
      else:
          result[key] = {}
    return result, index


def _parse_list(lines, index, indent):
    result = []
    while index < len(lines):
        line_indent, raw = lines[index]
        if line_indent < indent:
            break
        if line_indent != indent:
            raise ValueError(f"unexpected indent: {raw}")
        content = raw[indent:]
        if not content.startswith("- "):
            break
        item = content[2:].strip()
        index += 1
        if item:
            result.append(_parse_scalar(item))
            continue
        if index < len(lines) and lines[index][0] > indent:
            parsed, index = _parse_block(lines, index, lines[index][0])
            result.append(parsed)
        else:
            result.append(None)
    return result, index


def _parse_scalar(value: str):
    if value.startswith("[") and value.endswith("]"):
        return ast.literal_eval(value)
    if value.startswith(("'", '"')) and value.endswith(("'", '"')):
        return ast.literal_eval(value)
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "Null", "none", "None", "~"}:
        return None
    try:
        return int(value)
    except ValueError:
        return value
