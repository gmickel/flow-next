"""Deterministic projection and private, expiring inputs for agent body folds."""
from __future__ import annotations

import json
import os
import re
import tempfile
import time
from pathlib import Path

from ..lifecycle.helpers import leaf_is_safe, read_config
from ..lifecycle.verbs import _ensure_create_first_ignored
from ..resolve_verb import bound_executor
from ..syncbody import trackerBodyForMerge, _legacy_unconverted, _wire_body
from ..types import TrackerError
from ..wire import dispatch
from .helpers import (load_tracker, local_spec_md, locator_of,
                      live_comments_snapshot, normalize_comment_body)


def render_body(body: str) -> str:
    """Project every section, including legacy layouts, without semantic edits."""
    # Keep fenced examples literal. Remove only the two documented scaffolds.
    out = []
    fence = None
    acceptance = False
    for line in body.splitlines(keepends=True):
        match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if match:
            token = match.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            out.append(line)
            continue
        if fence:
            out.append(line)
            continue
        line = re.sub(r"<!--\s*(?:scope:|[^<>]*\d+%\s*\[)[^<>]*-->", "", line)
        if line.startswith("## "):
            acceptance = line.strip().lower() in {"## acceptance criteria", "## acceptance"}
        if acceptance:
            criterion = re.match(r"^(\s*[-*] )\*\*(R\d+):\*\*\s*(.*?)(\r?\n)?$", line)
            if criterion:
                line = f"{criterion[1]}[ ] {criterion[3]} [{criterion[2]}]{criterion[4] or ''}"
            elif re.match(r"^\s*[-*] (?!\[[ xX]\])", line):
                line = re.sub(r"^(\s*[-*] )", r"\1[ ] ", line)
        out.append(line)
    return "".join(out)


_MARKER = re.compile(r"<!--\s*flow-next:(?:sync|question|status)\b.*?-->", re.S)


def _normalized(body: str) -> str:
    body = re.sub(r"</?a\b[^>]*>", "", normalize_comment_body(body))
    body = _MARKER.sub("", body)
    lines = body.splitlines()
    while lines and not any(ch.isalnum() for ch in lines[-1]):
        lines.pop()
    return " ".join("\n".join(lines).lower().split())


def genuine_comments(comments: list) -> list:
    echoes = {_normalized(c.get("body") or "") for c in comments
              if _MARKER.search(normalize_comment_body(c.get("body") or ""))}
    return [c for c in comments
            if not _MARKER.search(normalize_comment_body(c.get("body") or ""))
            and _normalized(c.get("body") or "") not in echoes]


def cleanup(flow_dir: Path, spec_id: str, *, expired_only: bool = False) -> None:
    """Remove only our private snapshots, after consumption or after one hour."""
    root = flow_dir / "create-first"
    if leaf_is_safe(flow_dir, root):
        return
    for directory in root.glob(f"prepare-{spec_id}-*"):
        if directory.is_symlink() or not directory.is_dir():
            continue
        if expired_only and time.time() - directory.stat().st_mtime < 3600:
            continue
        for path in directory.iterdir():
            if path.is_file() and not path.is_symlink():
                path.unlink()
        try:
            directory.rmdir()
        except OSError:
            pass


def prepare(flow_dir: Path, spec_id: str, *, execute):
    loaded = load_tracker(flow_dir, spec_id)
    if isinstance(loaded, TrackerError):
        return loaded
    tracker = loaded[2]
    locator = locator_of(tracker)
    if isinstance(locator, TrackerError):
        return locator
    flow = local_spec_md(flow_dir, spec_id)
    if isinstance(flow, TrackerError):
        return flow
    config = read_config(flow_dir)
    ex = bound_executor(config, execute)
    issue = dispatch("read", config, locator=locator, execute=ex)
    if isinstance(issue, TrackerError):
        return issue
    comments = dispatch("comment-list", config, locator=locator, execute=ex)
    if isinstance(comments, TrackerError):
        return comments
    snapshot = live_comments_snapshot(comments)
    if isinstance(snapshot, TrackerError):
        return snapshot
    raw_body = issue.get("body") or ""
    stripped = trackerBodyForMerge(raw_body)
    base_flow = tracker.get("mergeBaseFlow")
    base_tracker = tracker.get("mergeBaseTracker")
    provider = (config.get("tracker") or {}).get("type")
    legacy = _legacy_unconverted(provider, tracker, _wire_body(provider, issue.get("raw") or {}))
    remote_same = stripped == base_tracker or legacy
    if base_flow is None or base_tracker is None:
        kind = "no-base"
    elif flow == base_flow and remote_same:
        kind = "noop"
    elif remote_same:
        kind = "flow-only"
    elif flow == base_flow:
        kind = "tracker-only"
    else:
        kind = "both-changed"
    unsafe = leaf_is_safe(flow_dir, flow_dir / "create-first")
    if unsafe:
        return unsafe
    secured = _ensure_create_first_ignored(flow_dir)
    if secured is not None:
        return secured
    (flow_dir / "create-first").mkdir(parents=True, exist_ok=True)
    cleanup(flow_dir, spec_id, expired_only=True)
    directory = Path(tempfile.mkdtemp(prefix=f"prepare-{spec_id}-", dir=flow_dir / "create-first"))
    contents = {"flow_file": flow, "body_file": raw_body,
                "source_body_file": raw_body,
                "comments_file": json.dumps(snapshot),
                "base_file": json.dumps({"flow": base_flow, "tracker": base_tracker})}
    paths = {}
    for key, content in contents.items():
        path = directory / key
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
        paths[key] = str(path.resolve())
    return {"classification": kind, "tracker_body": stripped,
            "base": {"flow": base_flow, "tracker": base_tracker},
            "genuine_comments": genuine_comments(comments["comments"]),
            "files": paths, "expires_at": time.time() + 3600}
