"""Frontmatter seam for Flow's markdown spec files (.flow/specs/<id>.md).

Stdlib only. Reads and writes identity + snapshot metadata in YAML frontmatter,
preserving unknown top-level frontmatter keys and every byte of the markdown
body, and writes atomically via temp file + os.replace.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Optional, Union

from .types import ErrorClass, TrackerError

TRACKER_PERSISTED_KEYS = ("id", "identifier", "url", "snapshot")

_HEADING_RE = re.compile(r"^#\s+(.+?)\s*$", re.M)
_YAML_SPECIAL_RE = re.compile(r'[:#"\'\n\r\t]|^[\s\-\[\]\{\}\*&!%@`|>?]|[\s]$')
_YAML_RESERVED = frozenset({"null", "Null", "NULL", "~", "true", "True", "TRUE",
                            "false", "False", "FALSE"})


def body_snapshot_hash(body: Optional[str]) -> str:
    """SHA-256 of an issue body with line endings normalized to LF."""
    norm = (body or "").replace("\r\n", "\n").replace("\r", "\n")
    return "sha256:" + hashlib.sha256(norm.encode("utf-8")).hexdigest()


def spec_path(flow_dir: Path, spec_id: str) -> Path:
    specs = Path(flow_dir) / "specs"
    root = specs / f"{spec_id}.md"
    if root.is_file() or root.is_symlink():
        return root
    opened = specs / "open" / f"{spec_id}.md"
    if opened.is_file() or opened.is_symlink():
        return opened
    parked = specs / "parked" / f"{spec_id}.md"
    if parked.is_file() or parked.is_symlink():
        return parked
    return root


def _unquote(raw: str) -> Optional[str]:
    s = raw.strip()
    if not s or s in ("null", "Null", "NULL", "~"):
        return None
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        try:
            val = json.loads(s)
            return str(val) if val is not None else None
        except ValueError:
            return s[1:-1]
    if len(s) >= 2 and s[0] == "'" and s[-1] == "'":
        return s[1:-1].replace("''", "'")
    return s


def _quote(val: str, *, always: bool = False) -> str:
    if always or not val or val in _YAML_RESERVED or _YAML_SPECIAL_RE.search(val):
        return json.dumps(val, ensure_ascii=False)
    return val


def split_frontmatter(text: str) -> tuple[Optional[str], str, str]:
    """Return (yaml_text_or_None, eol, body) preserving body bytes verbatim."""
    if text.startswith("---\r\n"):
        eol = "\r\n"
        rest = text[5:]
    elif text.startswith("---\n"):
        eol = "\n"
        rest = text[4:]
    else:
        return None, "\n", text

    # Empty frontmatter block: ---\n---\n
    if rest.startswith("---\r\n"):
        return "", eol, rest[5:]
    if rest.startswith("---\n"):
        return "", eol, rest[4:]
    if rest == "---":
        return "", eol, ""

    m = re.search(r"\r?\n---(?:\r?\n|\Z)", rest)
    if not m:
        return None, "\n", text
    return rest[:m.start()], eol, rest[m.end():]


def _parse_blocks(yaml_text: str) -> list[tuple[str, Any, list[str]]]:
    """Parse top-level YAML entries, keeping raw lines for unknown keys."""
    entries: list[tuple[str, Any, list[str]]] = []
    lines = yaml_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            entries.append(("", None, [line]))
            i += 1
            continue
        m = re.match(r"^([A-Za-z0-9_.-]+)\s*:(.*)$", line)
        if not m:
            entries.append(("", None, [line]))
            i += 1
            continue
        key, rest = m.group(1), m.group(2)
        raw_lines = [line]
        i += 1
        while i < len(lines) and (lines[i].startswith((" ", "\t")) or not lines[i].strip()):
            raw_lines.append(lines[i])
            i += 1
        # Trim trailing blank lines off the block and re-emit as raw spacing
        trailing_blanks: list[str] = []
        while len(raw_lines) > 1 and not raw_lines[-1].strip():
            trailing_blanks.insert(0, raw_lines.pop())

        if key == "tracker":
            mapping: dict[str, Any] = {}
            for sub in raw_lines[1:]:
                sm = re.match(r"^\s+([A-Za-z0-9_.-]+)\s*:(.*)$", sub)
                if sm:
                    mapping[sm.group(1)] = _unquote(sm.group(2))
            entries.append((key, mapping, raw_lines))
        elif key == "repos":
            items: list[str] = []
            for sub in raw_lines[1:]:
                lm = re.match(r"^\s*-\s*(.+?)\s*$", sub)
                if lm:
                    val = _unquote(lm.group(1))
                    if val is not None:
                        items.append(val)
            entries.append((key, items, raw_lines))
        elif key in ("id", "title"):
            entries.append((key, _unquote(rest), raw_lines))
        else:
            entries.append((key, _unquote(rest) if len(raw_lines) == 1 else raw_lines, raw_lines))

        for blank in trailing_blanks:
            entries.append(("", None, [blank]))
    return entries


def _render_tracker_lines(tracker: dict[str, Any]) -> list[str]:
    lines = ["tracker:"]
    for k in TRACKER_PERSISTED_KEYS:
        val = tracker.get(k)
        if val is not None and str(val).strip() != "":
            lines.append(f"  {k}: {_quote(str(val), always=True)}")
    return lines if len(lines) > 1 else []


def load_spec_doc(path: Path, *, spec_id: Optional[str] = None
                  ) -> Union[tuple[dict, str], TrackerError]:
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError) as exc:
        return TrackerError(ErrorClass.TRANSPORT, f"unreadable spec: {exc}",
                            subtype="spec")
    yaml_text, _eol, body = split_frontmatter(text)
    data: dict[str, Any] = {}
    if yaml_text is not None:
        for key, value, _raw in _parse_blocks(yaml_text):
            if key:
                data[key] = value
    if not data.get("id"):
        data["id"] = spec_id or path.stem
    if not data.get("title"):
        m = _HEADING_RE.search(body)
        data["title"] = m.group(1).strip() if m else data["id"]
    if "tracker" in data and not isinstance(data["tracker"], dict):
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "spec tracker frontmatter is not a mapping",
                            subtype="spec")
    return data, body


def write_spec_tracker(path: Path, tracker: dict[str, Any],
                       *, spec_id: Optional[str] = None) -> Optional[TrackerError]:
    """Update only tracker identity+snapshot keys in frontmatter, atomically."""
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            original = f.read()
    except (OSError, UnicodeDecodeError) as exc:
        return TrackerError(ErrorClass.TRANSPORT, f"unreadable spec: {exc}",
                            subtype="spec")
    yaml_text, eol, body = split_frontmatter(original)
    tracker_lines = _render_tracker_lines(tracker)

    if yaml_text is None:
        eol = "\r\n" if "\r\n" in original else "\n"
        out_lines = [f"id: {_quote(spec_id or path.stem)}"]
        m = _HEADING_RE.search(body)
        if m:
            out_lines.append(f"title: {_quote(m.group(1).strip())}")
        out_lines.extend(tracker_lines)
        new_text = f"---{eol}{eol.join(out_lines)}{eol}---{eol}{body}"
    else:
        entries = _parse_blocks(yaml_text)
        out_lines = []
        replaced = False
        for key, _value, raw_lines in entries:
            if key == "tracker":
                if not replaced:
                    out_lines.extend(tracker_lines)
                    replaced = True
            else:
                out_lines.extend(raw_lines)
        if not replaced and tracker_lines:
            out_lines.extend(tracker_lines)
        fm_body = eol.join(out_lines)
        new_text = (f"---{eol}{fm_body}{eol}---{eol}{body}"
                    if fm_body else f"---{eol}---{eol}{body}")

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
                f.write(new_text)
            os.replace(tmp, path)
        except Exception:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
        return None
    except OSError as exc:
        return TrackerError(ErrorClass.TRANSPORT, f"atomic write failed: {exc}",
                            subtype="write")


def iter_spec_trackers(flow_dir: Path):
    """Yield (spec_id, tracker_dict) across `.flow/specs/`, `.flow/specs/open/`, and `.flow/specs/parked/`."""
    specs = Path(flow_dir) / "specs"
    if not specs.is_dir():
        return
    seen: set[str] = set()
    for folder in (specs, specs / "open", specs / "parked"):
        if folder.is_symlink() or not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.md")):
            loaded = load_spec_doc(path)
            if isinstance(loaded, TrackerError):
                continue
            data, _body = loaded
            sid = str(data.get("id") or path.stem)
            if sid in seen:
                continue
            seen.add(sid)
            tracker = data.get("tracker")
            yield sid, (tracker if isinstance(tracker, dict) else {})
