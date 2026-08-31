from __future__ import annotations

import ast


def safe_load(text: str):
    parser = _Parser(text)
    return parser.parse()


class _Parser:
    def __init__(self, text: str) -> None:
        self.lines = []
        for raw_line in text.splitlines():
            if not raw_line.strip():
                continue
            stripped = raw_line.lstrip()
            if stripped.startswith("#"):
                continue
            indent = len(raw_line) - len(stripped)
            self.lines.append((indent, stripped))
        self.index = 0

    def parse(self):
        if not self.lines:
            return None
        return self._parse_block(self.lines[0][0])

    def _parse_block(self, indent: int):
        if self.index >= len(self.lines):
            return None
        _, current = self.lines[self.index]
        if current.startswith("- "):
            return self._parse_list(indent)
        return self._parse_dict(indent)

    def _parse_dict(self, indent: int):
        result = {}
        while self.index < len(self.lines):
            line_indent, text = self.lines[self.index]
            if line_indent < indent:
                break
            if line_indent > indent:
                raise ValueError(f"unexpected indentation: {text}")
            if text.startswith("- "):
                break
            key, has_value, value = text.partition(":")
            if not has_value:
                raise ValueError(f"invalid mapping entry: {text}")
            self.index += 1
            if value.strip():
                result[key.strip()] = _parse_scalar(value.strip())
                continue
            if self.index >= len(self.lines) or self.lines[self.index][0] <= indent:
                result[key.strip()] = None
                continue
            result[key.strip()] = self._parse_block(self.lines[self.index][0])
        return result

    def _parse_list(self, indent: int):
        result = []
        while self.index < len(self.lines):
            line_indent, text = self.lines[self.index]
            if line_indent < indent:
                break
            if line_indent != indent or not text.startswith("- "):
                raise ValueError(f"invalid list entry: {text}")
            item_text = text[2:].strip()
            self.index += 1
            if item_text:
                result.append(_parse_scalar(item_text))
                continue
            if self.index >= len(self.lines) or self.lines[self.index][0] <= indent:
                result.append(None)
                continue
            result.append(self._parse_block(self.lines[self.index][0]))
        return result


def _parse_scalar(value: str):
    if value.startswith(("[", "{", "'", '"')):
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
