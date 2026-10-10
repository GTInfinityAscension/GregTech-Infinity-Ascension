"""Read and write FTB Quests SNBT, keeping key order and bare tokens (1.5d, 64, 1L, true) exactly as they were.

`Raw` marks a bare token so a number never turns into a string and a string never loses its quotes. The writer
follows what FTB Quests itself writes: tab indents, `key: value` per line, one list item per line.
"""

from __future__ import annotations

import re


class Raw(str):
    """A bare SNBT token such as `1.5d`, `64`, `1L`, `true` or `false`."""


def double(value: float) -> Raw:
    return Raw(f"{float(value)}d")


def long(value: int) -> Raw:
    return Raw(f"{int(value)}L")


def boolean(value: bool) -> Raw:
    return Raw("true" if value else "false")


def number(raw: str) -> float:
    """The numeric value of a Raw like `1.5d` or `64`."""
    return float(re.sub(r"[dDfFbBsSlL]$", "", str(raw)))


def loads(text: str):
    if not text.lstrip().startswith("{"):
        text = "{" + text + "}"
    pos = 0
    n = len(text)

    def skip():
        nonlocal pos
        while pos < n and (text[pos].isspace() or text[pos] == ","):
            pos += 1

    def value():
        nonlocal pos
        skip()
        c = text[pos]
        if c == "{":
            pos += 1
            out = {}
            while True:
                skip()
                if text[pos] == "}":
                    pos += 1
                    return out
                key = read_key()
                skip()
                if text[pos] != ":":
                    raise ValueError(f"expected ':' at {pos}")
                pos += 1
                out[key] = value()
        if c == "[":
            pos += 1
            items = []
            while True:
                skip()
                if text[pos] == "]":
                    pos += 1
                    return items
                items.append(value())
        if c in "\"'":
            return read_string(c)
        m = re.match(r"[^\s,\]\}]+", text[pos:])
        token = m.group(0)
        pos += len(token)
        return Raw(token)

    def read_key():
        nonlocal pos
        if text[pos] in "\"'":
            return read_string(text[pos])
        m = re.match(r"[^\s:]+", text[pos:])
        pos += len(m.group(0))
        return m.group(0)

    def read_string(quote):
        nonlocal pos
        pos += 1
        out = []
        while text[pos] != quote:
            if text[pos] == "\\":
                pos += 1
                out.append({"n": "\n", "t": "\t"}.get(text[pos], text[pos]))
            else:
                out.append(text[pos])
            pos += 1
        pos += 1
        return "".join(out)

    return value()


def _quote(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def _write(value, depth: int) -> str:
    pad = "\t" * depth
    inner = "\t" * (depth + 1)
    if isinstance(value, Raw):
        return str(value)
    if isinstance(value, str):
        return _quote(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, dict):
        if not value:
            return "{ }"
        lines = [f"{inner}{key}: {_write(item, depth + 1)}" for key, item in value.items()]
        return "{\n" + "\n".join(lines) + "\n" + pad + "}"
    if isinstance(value, list):
        if not value:
            return "[ ]"
        lines = [f"{inner}{_write(item, depth + 1)}" for item in value]
        return "[\n" + "\n".join(lines) + "\n" + pad + "]"
    raise TypeError(f"cannot write {type(value).__name__}")


def dumps(value) -> str:
    return _write(value, 0) + "\n"
