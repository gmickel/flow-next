"""Markdown <-> Jira wiki markup for REST v2 text fields (fn-253).

A Jira v2 description or comment is wiki markup; it never interprets
Markdown. The Jira provider converts on every body write
(`markdown_to_wiki`) and decodes once where a read extracts the body
(`wiki_to_markdown`), so everything above the wire compares Markdown.

Both transforms are pure, deterministic, and standard-library only. They
cover the construct subset flow-next specs use: ATX headings, bold, italic,
inline code, links, fenced code, simple pipe tables, blockquotes, and nested
bullet/numbered lists. Anything outside the subset stays literal text:
wiki-special characters in prose are backslash-escaped on write, and wiki
fragments the encoder never emits (macros, mentions, colour, ...) decode
unchanged. HTML comments (sync and chart-rollup markers) pass through both
directions byte-exact.

The decoder yields stable canonical Markdown, not the source spelling:
``**b**`` and ``__b__`` both decode to ``**b**``, list numbering restarts at
1, and nested list indentation is normalized.
"""

from __future__ import annotations

import re

__all__ = ["markdown_to_wiki", "wiki_to_markdown"]

#: Languages Jira's `{code:<lang>}` formatter knows on Cloud and DC. Any other
#: fence (plain, `text`, `markdown`, ...) becomes `{noformat}` - an unknown
#: language renders an error panel and a bare `{code}` highlights as Java.
_CODE_LANGS = frozenset({
    "actionscript", "ada", "applescript", "bash", "c", "c#", "c++", "cpp",
    "css", "erlang", "go", "groovy", "haskell", "html", "java", "javascript",
    "js", "json", "lua", "objc", "perl", "php", "python", "r", "ruby",
    "scala", "sh", "sql", "swift", "visualbasic", "xml", "yaml",
})

#: Characters that open wiki formatting anywhere in a line; always escaped.
_ALWAYS_ESCAPE = frozenset("*_+^~{}[]|!\\")
#: Every character the encoder may backslash-escape; the decoder unescapes
#: exactly this set so an unrelated backslash survives unchanged.
_ESCAPABLE = _ALWAYS_ESCAPE | frozenset("-?#(.")

_EMOTICON_RE = re.compile(
    r"\((?:y|n|i|x|/|!|\?|\+|-|on|off|\*|\*[rgby]|flag|flagoff)\)")

# --- Markdown (encoder input) ------------------------------------------------

_MD_FENCE_RE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})[ \t]*([^`\s]*)[^`]*$")
_MD_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$")
_MD_LIST_RE = re.compile(r"^([ \t]*)([-*+]|\d{1,9}[.)])[ \t]+(.*)$")
_MD_QUOTE_RE = re.compile(r"^>[ \t]?(.*)$")
_MD_TABLE_SEP_RE = re.compile(
    r"^[ \t]*\|?[ \t]*:?-+:?[ \t]*(?:\|[ \t]*:?-+:?[ \t]*)*\|?[ \t]*$")

_MD_INLINE_RE = re.compile(
    r"(?P<comment><!--.*?-->)"
    r"|(?P<code>(?<!`)(?P<ticks>`+)(?!`)(?P<ctext>.+?)(?<!`)(?P=ticks)(?!`))"
    r"|(?P<esc>\\[!-/:-@\[-`{-~])"
    r"|(?P<auto><(?P<aurl>https?://[^\s<>]+)>)"
    r"|(?P<link>\[(?P<ltext>(?:\\.|[^\]\\\n])+)\]\((?P<lurl>[^)\s]+)\))"
    r"|(?P<url>https?://[^\s<>\[\]|]*[^\s<>\[\]|.,;:!?'\")*_])"
    r"|(?P<bold>\*\*(?=\S)(?P<btext>.+?)(?<=\S)\*\*|__(?=\S)(?P<btext2>.+?)(?<=\S)__(?!\w))"
    r"|(?P<em>\*(?=[^\s*])(?P<etext>.+?)(?<=[^\s*])\*(?!\*)"
    r"|(?<!\w)_(?=\S)(?P<etext2>.+?)(?<=\S)_(?!\w))"
)

# --- Wiki (decoder input) -----------------------------------------------------

_WIKI_CODE_OPEN_RE = re.compile(r"^\{code(?::([\w+#.-]+))?\}$")
_WIKI_HEADING_RE = re.compile(r"^h([1-6])\.(?:[ \t]+(.*))?$")
_WIKI_QUOTE_RE = re.compile(r"^bq\.(?:[ \t]+(.*))?$")
_WIKI_LIST_RE = re.compile(r"^([*#]+)[ \t]+(.*)$")
_WIKI_BLOCK_WORD_RE = re.compile(r"h[1-6]|bq")
#: A link or monospace span inside a table cell keeps its own `|`.
_WIKI_CELL_SPAN_RE = re.compile(r"\{\{(?:\\.|[^\\])+?\}\}|\[(?:\\.|[^\]\\\n])+\]")

_WIKI_INLINE_RE = re.compile(
    r"(?P<comment><!--.*?-->)"
    r"|(?P<code>\{\{(?P<ctext>(?:\\.|[^\\])+?)\}\})"
    r"|(?P<bbold>\{\*\}(?P<bbtext>(?:\\.|[^\\\n])+?)\{\*\})"
    r"|(?P<bem>\{_\}(?P<betext>(?:\\.|[^\\\n])+?)\{_\})"
    r"|(?P<esc>\\[^\sA-Za-z0-9])"
    r"|(?P<link>\[(?P<ltext>(?:\\.|[^\]|\\\n])+)\|(?P<lurl>[^\]\s|]+)\])"
    r"|(?P<blink>\[(?P<burl>https?://[^\]\s|]+)\])"
    r"|(?P<url>https?://[^\s<>\[\]|]*[^\s<>\[\]|.,;:!?'\")*_])"
    r"|(?P<bold>(?<![\w*])\*(?=[^\s*])(?P<btext>(?:\\.|[^\\\n])+?)(?<=[^\s\\])\*(?![\w*]))"
    r"|(?P<em>(?<![\w_])_(?=[^\s_])(?P<etext>(?:\\.|[^\\\n])+?)(?<=[^\s\\])_(?![\w_]))"
)


# =============================================================================
# Markdown -> wiki
# =============================================================================

def _escape_char(text: str, idx: int, *, line_start: bool) -> str:
    ch = text[idx]
    prev = text[idx - 1] if idx > 0 else ""
    nxt = text[idx + 1] if idx + 1 < len(text) else ""
    if ch in _ALWAYS_ESCAPE:
        return "\\" + ch
    if ch == "-" and not (prev.isalnum() and nxt.isalnum()):
        return "\\-"  # dash lists, en/em dashes, -strike-
    if ch == "?" and "?" in (prev, nxt):
        return "\\?"  # ??citation??
    if ch == "#" and idx == 0 and line_start:
        return "\\#"  # numbered list
    if ch == "." and line_start and _WIKI_BLOCK_WORD_RE.fullmatch(text[:idx]):
        return "\\."  # literal `h1.` / `bq.` prose, not a block
    if ch == "("and _EMOTICON_RE.match(text, idx):
        return "\\("  # (y) (x) (i) ... emoticons
    return ch


def _escape_span(text: str, start: int, end: int, *, line_start: bool) -> str:
    return "".join(_escape_char(text, i, line_start=line_start)
                   for i in range(start, end))


def _encode_inline(text: str, *, line_start: bool = False) -> str:
    out: list[str] = []
    pos = 0
    while True:
        m = _MD_INLINE_RE.search(text, pos)
        stop = m.start() if m else len(text)
        out.append(_escape_span(text, pos, stop,
                                line_start=line_start and pos == 0))
        if m is None:
            return "".join(out)
        kind = m.lastgroup
        if kind == "comment" or kind == "url":
            out.append(m.group(0))
        elif m.group("code") is not None:
            code = m.group("ctext")
            if len(code) > 2 and code[0] == code[-1] == " " and code.strip():
                code = code[1:-1]
            out.append("{{" + _escape_span(code, 0, len(code),
                                           line_start=False) + "}}")
        elif kind == "esc":
            ch = m.group(0)[1]
            out.append("\\" + ch if ch in _ESCAPABLE else ch)
        elif kind == "auto":
            out.append("[" + m.group("aurl") + "]")
        elif kind == "link":
            out.append("[" + _encode_inline(m.group("ltext")) + "|"
                       + m.group("lurl") + "]")
        elif kind in ("bold", "em"):
            if kind == "bold":
                inner, mark = m.group("btext") or m.group("btext2"), "*"
            else:
                inner, mark = m.group("etext") or m.group("etext2"), "_"
            # Wiki emphasis needs a non-word boundary on both sides; an
            # intraword span takes the braced `{*}...{*}` form instead.
            if (text[m.start() - 1:m.start()].isalnum()
                    or text[m.end():m.end() + 1].isalnum()):
                mark = "{" + mark + "}"
            out.append(mark + _encode_inline(inner) + mark)
        pos = m.end()


def _split_cells(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    cells: list[str] = []
    cur: list[str] = []
    i = 0
    while i < len(body):
        ch = body[i]
        if ch == "\\" and i + 1 < len(body):
            cur.append(body[i:i + 2])
            i += 2
            continue
        if ch == "|":
            cells.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
        i += 1
    cells.append("".join(cur).strip())
    return cells


def _shield_closer(line: str, closer: str, step: int) -> str:
    """Add (+1) or remove (-1) one backslash before each `closer` inside a
    code block, so literal `{code}` / `{noformat}` content cannot end the
    block early and still decodes to the original text."""
    pattern = re.compile(r"(\\*)" + re.escape(closer))
    if step > 0:
        return pattern.sub(lambda m: m.group(1) + "\\" + closer, line)
    return pattern.sub(lambda m: m.group(1)[:-1] + closer, line)


def _indent_width(ws: str) -> int:
    return len(ws.expandtabs(4))


def markdown_to_wiki(text: str) -> str:
    """Render a Markdown body as Jira wiki markup."""
    lines = text.split("\n")
    out: list[str] = []
    stack: list[tuple[int, str]] = []  # (indent, "ul"|"ol") per open level
    in_comment = False
    i = 0
    while i < len(lines):
        line = lines[i]
        if in_comment:
            out.append(line)
            in_comment = "-->" not in line
            i += 1
            continue
        stripped = line.lstrip()
        if stripped.startswith("<!--") and "-->" not in stripped[4:]:
            out.append(line)
            in_comment = True
            stack = []
            i += 1
            continue
        fence = _MD_FENCE_RE.match(line)
        if fence:
            marker, lang = fence.group(1), fence.group(2).lower()
            content: list[str] = []
            i += 1
            while i < len(lines):
                body = lines[i].strip()
                if (body and set(body) == {marker[0]}
                        and len(body) >= len(marker)):
                    i += 1
                    break
                content.append(lines[i])
                i += 1
            # Pick the block whose terminator the content does not hold:
            # Jira renders an escaping backslash inside a block literally.
            joined = "\n".join(content)
            if "{code}" in joined and "{noformat}" not in joined:
                opener, closer = "{noformat}", "{noformat}"
            elif lang in _CODE_LANGS or "{noformat}" in joined:
                opener = f"{{code:{lang}}}" if lang in _CODE_LANGS else "{code}"
                closer = "{code}"
            else:
                opener, closer = "{noformat}", "{noformat}"
            out.append(opener)
            # Both terminators present: only a visible escape is left.
            out.extend(_shield_closer(ln, closer, +1) for ln in content)
            out.append(closer)
            stack = []
            continue
        if (stripped.startswith("|") and i + 1 < len(lines)
                and _MD_TABLE_SEP_RE.match(lines[i + 1])):
            out.append("||" + "||".join(
                _encode_inline(c) or " " for c in _split_cells(line)) + "||")
            i += 2
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                out.append("|" + "|".join(
                    _encode_inline(c) or " " for c in _split_cells(lines[i]))
                    + "|")
                i += 1
            stack = []
            continue
        heading = _MD_HEADING_RE.match(line)
        if heading:
            out.append(f"h{len(heading.group(1))}. "
                       + _encode_inline(heading.group(2)))
            stack = []
            i += 1
            continue
        quote = _MD_QUOTE_RE.match(line)
        if quote:
            inner = quote.group(1)
            out.append("bq. " + _encode_inline(inner) if inner else "bq.")
            stack = []
            i += 1
            continue
        item = _MD_LIST_RE.match(line)
        if item:
            indent = _indent_width(item.group(1))
            kind = "ol" if item.group(2)[0].isdigit() else "ul"
            while stack and stack[-1][0] > indent:
                stack.pop()
            if stack and stack[-1][0] == indent:
                stack[-1] = (indent, kind)
            else:
                stack.append((indent, kind))
            prefix = "".join("#" if k == "ol" else "*" for _, k in stack)
            out.append(prefix + " " + _encode_inline(item.group(3)))
            i += 1
            continue
        if not stripped:
            out.append(line)
            i += 1
            continue
        stack = []
        lead = line[:len(line) - len(stripped)]
        out.append(lead + _encode_inline(stripped, line_start=True))
        i += 1
    return "\n".join(out)


# =============================================================================
# Wiki -> Markdown
# =============================================================================

def _md_literal(ch: str, *, prev: str, nxt: str, at_start: bool,
                in_table: bool) -> str:
    """Spell one literal character so Markdown reads it as text."""
    if ch in "*`\\":
        return "\\" + ch
    if ch == "_":
        return "_" if prev.isalnum() and nxt.isalnum() else "\\_"
    if ch == "]":
        return "\\]" if nxt == "(" else "]"
    if ch == "|" and in_table:
        return "\\|"
    if at_start and ch in "#-+" and nxt in ("", " ", "\t", "#"):
        return "\\" + ch
    if at_start and ch == ">":
        return "\\>"
    return ch


def _backtick_span(code: str) -> str:
    runs = [len(r) for r in re.findall(r"`+", code)]
    ticks = "`" * ((max(runs) + 1) if runs else 1)
    if code.startswith("`") or code.endswith("`") or (
            code.startswith(" ") and code.endswith(" ") and code.strip()):
        code = f" {code} "
    return ticks + code + ticks


def _unescape(text: str) -> str:
    return re.sub(r"\\(.)",
                  lambda m: m.group(1) if m.group(1) in _ESCAPABLE
                  else m.group(0), text)


def _decode_inline(text: str, *, line_start: bool = False,
                   in_table: bool = False) -> str:
    out: list[str] = []
    pos = 0

    def at_start() -> bool:
        return line_start and not "".join(out).strip()

    while True:
        m = _WIKI_INLINE_RE.search(text, pos)
        stop = m.start() if m else len(text)
        out.append(text[pos:stop])
        if m is None:
            return "".join(out)
        kind = m.lastgroup
        if kind == "comment" or kind == "url":
            out.append(m.group(0))
        elif m.group("code") is not None:
            out.append(_backtick_span(_unescape(m.group("ctext"))))
        elif kind == "esc":
            ch = m.group(0)[1]
            if ch == "." and line_start and re.fullmatch(
                    r"[ \t]*\d+", "".join(out)):
                out.append("\\.")  # `1\.` must not start an ordered list
            elif ch in _ESCAPABLE:
                prev = out[-1][-1:] if out and out[-1] else ""
                nxt = text[m.end():m.end() + 1]
                out.append(_md_literal(ch, prev=prev, nxt=nxt,
                                       at_start=at_start(),
                                       in_table=in_table))
            else:
                out.append(m.group(0))
        elif kind == "link":
            out.append("[" + _decode_inline(m.group("ltext"),
                                            in_table=in_table)
                       + "](" + m.group("lurl") + ")")
        elif kind == "blink":
            out.append("<" + m.group("burl") + ">")
        elif kind == "bbold":
            out.append("**" + _decode_inline(m.group("bbtext"),
                                             in_table=in_table) + "**")
        elif kind == "bem":
            out.append("*" + _decode_inline(m.group("betext"),
                                            in_table=in_table) + "*")
        elif kind == "bold":
            out.append("**" + _decode_inline(m.group("btext"),
                                             in_table=in_table) + "**")
        elif kind == "em":
            out.append("*" + _decode_inline(m.group("etext"),
                                            in_table=in_table) + "*")
        pos = m.end()


def _split_wiki_cells(line: str, sep: str) -> list[str]:
    body = line.strip()
    if body.startswith(sep):
        body = body[len(sep):]
    if body.endswith(sep) and not body.endswith("\\" + sep):
        body = body[:-len(sep)]
    cells: list[str] = []
    cur: list[str] = []
    i = 0
    while i < len(body):
        if body[i] == "\\" and i + 1 < len(body):
            cur.append(body[i:i + 2])
            i += 2
            continue
        span = _WIKI_CELL_SPAN_RE.match(body, i)
        if span:
            cur.append(span.group(0))
            i = span.end()
            continue
        if body.startswith(sep, i):
            cells.append("".join(cur).strip())
            cur = []
            i += len(sep)
            continue
        cur.append(body[i])
        i += 1
    cells.append("".join(cur).strip())
    return cells


def wiki_to_markdown(text: str) -> str:
    """Decode a Jira wiki body into canonical Markdown."""
    lines = text.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    counts: dict[str, int] = {}
    in_comment = False
    i = 0
    while i < len(lines):
        line = lines[i]
        if in_comment:
            out.append(line)
            in_comment = "-->" not in line
            i += 1
            continue
        stripped = line.strip()
        if stripped.startswith("<!--") and "-->" not in stripped[4:]:
            out.append(line)
            in_comment = True
            counts = {}
            i += 1
            continue
        code = _WIKI_CODE_OPEN_RE.match(stripped)
        if code or stripped == "{noformat}":
            closer = "{noformat}" if not code else "{code}"
            lang = (code.group(1) or "") if code else ""
            body: list[str] = []
            j = i + 1
            while j < len(lines) and lines[j].strip() != closer:
                body.append(lines[j])
                j += 1
            if j < len(lines):
                body = [_shield_closer(ln, closer, -1) for ln in body]
                runs = [len(r) for ln in body
                        for r in re.findall(r"^[ \t]*(`{3,})", ln)]
                fence = "`" * max([3] + [r + 1 for r in runs])
                out.append(fence + lang)
                out.extend(body)
                out.append(fence)
                counts = {}
                i = j + 1
                continue
        if stripped.startswith("||"):
            cells = _split_wiki_cells(stripped, "||")
            out.append("| " + " | ".join(
                _decode_inline(c, in_table=True) for c in cells) + " |")
            out.append("| " + " | ".join("---" for _ in cells) + " |")
            i += 1
            while (i < len(lines) and lines[i].strip().startswith("|")
                   and not lines[i].strip().startswith("||")):
                cells = _split_wiki_cells(lines[i], "|")
                out.append("| " + " | ".join(
                    _decode_inline(c, in_table=True) for c in cells) + " |")
                i += 1
            counts = {}
            continue
        heading = _WIKI_HEADING_RE.match(line)
        if heading:
            text_md = _decode_inline(heading.group(2) or "")
            level = "#" * int(heading.group(1))
            out.append(f"{level} {text_md}" if text_md else level)
            counts = {}
            i += 1
            continue
        quote = _WIKI_QUOTE_RE.match(line)
        if quote:
            inner = _decode_inline(quote.group(1) or "")
            out.append(f"> {inner}" if inner else ">")
            counts = {}
            i += 1
            continue
        item = _WIKI_LIST_RE.match(line)
        if item:
            prefix = item.group(1)
            for key in [k for k in counts if len(k) > len(prefix)
                        and k.startswith(prefix)]:
                del counts[key]
            indent = "".join("   " if c == "#" else "  " for c in prefix[:-1])
            if prefix[-1] == "#":
                counts[prefix] = counts.get(prefix, 0) + 1
                marker = f"{counts[prefix]}."
            else:
                marker = "-"
            out.append(f"{indent}{marker} " + _decode_inline(item.group(2)))
            i += 1
            continue
        if not stripped:
            out.append(line)
            i += 1
            continue
        counts = {}
        out.append(_decode_inline(line, line_start=True))
        i += 1
    return "\n".join(out)
