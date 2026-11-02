"""A small, strict YAML reader for the catalog files.

The core must not depend on PyYAML, so this reads the subset the catalog uses:
block mappings, block sequences, quoted and plain scalars, true/false/null,
integers, simple flow lists like [a, "b"], empty {} and [], and # comments.
Anything else is refused with the line number, so a catalog file can never be
read in two different ways. The test suite compares results with PyYAML.
"""

from __future__ import annotations

import re


class YamlError(ValueError):
    pass


_INT = re.compile(r"^-?(0|[1-9][0-9]*)$")
_FLOAT = re.compile(r"^-?(0|[1-9][0-9]*)\.[0-9]+$")
_KEY = re.compile(r"^([A-Za-z0-9_][A-Za-z0-9_.-]*)\s*:(\s+(.*))?$")
_SPECIAL_START = set("&*!|>%@`{")


def _strip_comment(text, lineno):
    out = []
    quote = None
    i = 0
    while i < len(text):
        c = text[i]
        if quote:
            out.append(c)
            if quote == '"' and c == "\\" and i + 1 < len(text):
                out.append(text[i + 1])
                i += 2
                continue
            if c == quote:
                if quote == "'" and i + 1 < len(text) and text[i + 1] == "'":
                    out.append("'")
                    i += 2
                    continue
                quote = None
        else:
            if c == "#" and (i == 0 or text[i - 1] in " \t"):
                break
            if c in "\"'" and (i == 0 or text[i - 1] in " \t[,:-"):
                quote = c
            out.append(c)
        i += 1
    if quote:
        raise YamlError("line %d: a quoted string is not closed" % lineno)
    return "".join(out).rstrip()


def _lines(text):
    result = []
    for n, raw in enumerate(text.splitlines(), start=1):
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise YamlError("line %d: use spaces, not tabs, for indentation" % n)
        if raw.strip() in ("---",) and not result:
            continue
        content = _strip_comment(raw, n)
        if not content.strip():
            continue
        indent = len(content) - len(content.lstrip(" "))
        result.append([indent, content.strip(), n])
    return result


def _unquote_double(s, lineno):
    body = s[1:-1]
    out = []
    i = 0
    escapes = {"n": "\n", "t": "\t", '"': '"', "\\": "\\", "/": "/"}
    while i < len(body):
        c = body[i]
        if c == "\\":
            if i + 1 >= len(body):
                raise YamlError("line %d: bad escape" % lineno)
            nxt = body[i + 1]
            if nxt in escapes:
                out.append(escapes[nxt])
                i += 2
                continue
            if nxt == "u" and re.match(r"^[0-9a-fA-F]{4}$", body[i + 2 : i + 6]):
                out.append(chr(int(body[i + 2 : i + 6], 16)))
                i += 6
                continue
            raise YamlError("line %d: unsupported escape \\%s" % (lineno, nxt))
        if c == '"':
            raise YamlError("line %d: unexpected quote inside a string" % lineno)
        out.append(c)
        i += 1
    return "".join(out)


def _scalar(s, lineno):
    s = s.strip()
    if s.startswith('"'):
        if len(s) < 2 or not s.endswith('"'):
            raise YamlError("line %d: text after a quoted string" % lineno)
        return _unquote_double(s, lineno)
    if s.startswith("'"):
        if len(s) < 2 or not s.endswith("'"):
            raise YamlError("line %d: text after a quoted string" % lineno)
        body = s[1:-1]
        if re.search(r"(?<!')'(?!')", body.replace("''", "")):
            raise YamlError("line %d: unexpected quote inside a string" % lineno)
        return body.replace("''", "'")
    if s.startswith("["):
        return _flow_list(s, lineno)
    if s == "{}":
        return {}
    if s in ("null", "~"):
        return None
    if s == "true":
        return True
    if s == "false":
        return False
    if s.lower() in ("yes", "no", "on", "off", "y", "n", "true", "false", "null"):
        raise YamlError("line %d: write %r in quotes (it is ambiguous in YAML)" % (lineno, s))
    if _INT.match(s):
        return int(s)
    if _FLOAT.match(s):
        raise YamlError("line %d: write the number %s in quotes (versions are text)" % (lineno, s))
    if s[0] in _SPECIAL_START or s.startswith("- ") or ": " in s or s.endswith(":") or " #" in s:
        raise YamlError("line %d: put this value in quotes: %s" % (lineno, s))
    return s


def _flow_list(s, lineno):
    if not s.endswith("]"):
        raise YamlError("line %d: a [list] is not closed" % lineno)
    inner = s[1:-1].strip()
    if not inner:
        return []
    items, buf, quote = [], [], None
    for c in inner:
        if quote:
            buf.append(c)
            if c == quote:
                quote = None
            continue
        if c in "\"'":
            quote = c
            buf.append(c)
        elif c == ",":
            items.append("".join(buf))
            buf = []
        elif c in "[]{}":
            raise YamlError("line %d: nested lists are not supported here" % lineno)
        else:
            buf.append(c)
    items.append("".join(buf))
    out = []
    for item in items:
        if not item.strip():
            raise YamlError("line %d: empty item in a [list]" % lineno)
        out.append(_scalar(item, lineno))
    return out


class _Parser:
    def __init__(self, lines):
        self.lines = lines
        self.i = 0

    def peek(self):
        return self.lines[self.i] if self.i < len(self.lines) else None

    def parse_node(self, indent):
        line = self.peek()
        if line is None:
            return None
        if line[1] == "-" or line[1].startswith("- "):
            return self.parse_seq(line[0])
        return self.parse_map(line[0])

    def parse_seq(self, indent):
        out = []
        while True:
            line = self.peek()
            if line is None or line[0] < indent:
                break
            if line[0] > indent:
                raise YamlError("line %d: unexpected indentation" % line[2])
            if not (line[1] == "-" or line[1].startswith("- ")):
                break
            rest = line[1][1:].strip()
            if not rest:
                self.i += 1
                nxt = self.peek()
                if nxt is None or nxt[0] <= indent:
                    out.append(None)
                else:
                    out.append(self.parse_node(nxt[0]))
                continue
            if _KEY.match(rest) and not rest.startswith(('"', "'")):
                # "- key: value" starts a mapping indented by two more spaces
                line[0] = indent + 2
                line[1] = rest
                out.append(self.parse_map(indent + 2))
                continue
            out.append(_scalar(rest, line[2]))
            self.i += 1
        return out

    def parse_map(self, indent):
        out = {}
        while True:
            line = self.peek()
            if line is None or line[0] < indent:
                break
            if line[0] > indent:
                raise YamlError("line %d: unexpected indentation" % line[2])
            if line[1] == "-" or line[1].startswith("- "):
                break
            m = _KEY.match(line[1])
            if not m:
                raise YamlError("line %d: expected 'key: value'" % line[2])
            key, value = m.group(1), m.group(3)
            if key in out:
                raise YamlError("line %d: the key %r appears twice" % (line[2], key))
            self.i += 1
            if value is None or value == "":
                nxt = self.peek()
                if nxt is not None and nxt[0] > indent:
                    out[key] = self.parse_node(nxt[0])
                elif nxt is not None and nxt[0] == indent and (nxt[1] == "-" or nxt[1].startswith("- ")):
                    out[key] = self.parse_seq(indent)
                else:
                    out[key] = None
            else:
                out[key] = _scalar(value, line[2])
                nxt = self.peek()
                if nxt is not None and nxt[0] > indent:
                    raise YamlError("line %d: unexpected indentation (multi-line text must be quoted on one line)" % nxt[2])
        return out


def loads(text):
    lines = _lines(text)
    if not lines:
        return None
    parser = _Parser(lines)
    result = parser.parse_node(lines[0][0])
    if parser.peek() is not None:
        raise YamlError("line %d: unexpected content" % parser.peek()[2])
    return result


def load_file(path):
    with open(path, "r", encoding="utf-8") as fh:
        try:
            return loads(fh.read())
        except YamlError as exc:
            raise YamlError("%s: %s" % (path, exc))
