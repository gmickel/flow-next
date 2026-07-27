"""Shared plumbing for lifecycle verbs (fn-140.2). Never raises across the boundary."""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional, Union

from ..types import ErrorClass, Request, Response, TrackerError

Result = Union[dict, TrackerError]
Execute = Callable[[Request], Union[Response, TrackerError]]

ACTIVE = frozenset({"github", "gitlab", "linear", "jira"})
LINK_STATES = frozenset({"unlinked", "identifier_only", "linked"})
CREATE_FIRST_KEY_RE = re.compile(r"[0-9a-f]{16}")

#: Spec ids are lowercase slug tokens (fn-12, fn-12-add-auth, wor-17-slug).
#: The shape gate is the FIRST containment defence: "../../victim" reproduced
#: an arbitrary-file overwrite before this existed.
SPEC_ID_RE = re.compile(r"^[a-z][a-z0-9]*-[0-9]+(?:-[a-z0-9][a-z0-9-]*)?$")


def validate_spec_id(spec_id) -> Optional[TrackerError]:
    if not isinstance(spec_id, str) or not SPEC_ID_RE.fullmatch(spec_id):
        return TrackerError(ErrorClass.INVALID_INPUT,
                            f"invalid spec id {spec_id!r}",
                            subtype="spec_id")
    return None


def leaf_is_safe(base_dir: Path, leaf: Path) -> Optional[TrackerError]:
    """Containment + no-follow, mirroring flowctl's _flow_leaf_is_safe policy:
    the leaf must resolve INSIDE base_dir and no component below base_dir may
    be a symlink (a committed symlink at `.flow/create-first` or a spec leaf
    redirected the write out of tree - reproduced)."""
    import stat as stat_mod
    try:
        base_real = base_dir.resolve()
        target_real = leaf.resolve()
    except OSError:
        return TrackerError(ErrorClass.INVALID_INPUT,
                            f"unresolvable path {leaf}", subtype="path")
    if base_real != target_real and base_real not in target_real.parents:
        return TrackerError(ErrorClass.INVALID_INPUT,
                            f"{leaf} escapes {base_dir}", subtype="path")
    probe = leaf
    while True:
        try:
            st = os.lstat(probe)
            if stat_mod.S_ISLNK(st.st_mode):
                return TrackerError(ErrorClass.INVALID_INPUT,
                                    f"{probe} is a symlink; refusing to write "
                                    "through it", subtype="path")
        except FileNotFoundError:
            pass
        except OSError:
            pass
        if probe == base_dir or probe.parent == probe:
            break
        probe = probe.parent
    return None


def dict_(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def tracker_type(config: dict) -> Optional[str]:
    t = dict_(config.get("tracker")).get("type")
    return t if t in ACTIVE else None


def destination(config: dict) -> Union[dict, TrackerError]:
    dest = dict_(dict_(dict_(config.get("tracker")).get("resolved")).get("destination"))
    if not dest:
        return TrackerError(ErrorClass.UNRESOLVED,
                            "no resolved destination; run `flowctl tracker resolve` first",
                            subtype="destination")
    return dest


def read_config(flow_dir: Path) -> dict:
    try:
        data = json.loads((Path(flow_dir) / "config.json").read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def atomic_write_json(path: Path, data: dict) -> Optional[TrackerError]:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
                f.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
            os.replace(tmp, path)
        except Exception:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
        return None
    except OSError as exc:
        return TrackerError(ErrorClass.TRANSPORT, f"atomic write failed: {exc}",
                            subtype="write")


def default_tracker() -> dict:
    return {
        "id": None, "identifier": None, "url": None, "lastSyncedAt": None,
        "baseHashFlow": None, "baseHashTracker": None,
        "mergeBaseFlow": None, "mergeBaseTracker": None,
        "depRelations": [], "linkState": "unlinked",
    }


def spec_path(flow_dir: Path, spec_id: str) -> Path:
    return Path(flow_dir) / "specs" / f"{spec_id}.json"


def load_spec(flow_dir: Path, spec_id: str) -> Union[tuple[Path, dict], TrackerError]:
    bad = validate_spec_id(spec_id)
    if bad:
        return bad
    path = spec_path(flow_dir, spec_id)
    unsafe = leaf_is_safe(Path(flow_dir) / "specs", path)
    if unsafe:
        return unsafe
    if not path.is_file():
        return TrackerError(ErrorClass.NOT_FOUND, f"spec {spec_id!r} not found",
                            subtype="spec")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return TrackerError(ErrorClass.TRANSPORT, f"unreadable spec: {exc}",
                            subtype="spec")
    if not isinstance(data, dict):
        return TrackerError(ErrorClass.INVALID_INPUT, "spec json is not an object",
                            subtype="spec")
    return path, data


def iter_tracker_states(flow_dir: Path):
    specs = Path(flow_dir) / "specs"
    if not specs.is_dir():
        return
    for path in sorted(specs.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        yield data.get("id", path.stem), dict_(data.get("tracker"))


def collision(flow_dir: Path, durable_id: str, *, except_spec: Optional[str] = None
              ) -> Optional[TrackerError]:
    for owner_id, state in iter_tracker_states(flow_dir):
        if except_spec is not None and owner_id == except_spec:
            continue
        if state.get("id") and str(state["id"]) == str(durable_id):
            return TrackerError(
                ErrorClass.CONFLICT,
                f"Tracker id {durable_id} already linked to spec {owner_id}",
                subtype="durable_collision",
                details={"owner": owner_id, "durable": durable_id},
            )
    return None


def write_tracker_block(path: Path, spec_data: dict, tracker: dict
                        ) -> Optional[TrackerError]:
    spec_data = dict(spec_data)
    spec_data["tracker"] = tracker
    spec_data["updated_at"] = now_iso()
    return atomic_write_json(path, spec_data)


def write_sync_receipt(flow_dir: Path, *, spec_id: str, status: str,
                       tracker_id: Optional[str] = None,
                       event: Optional[str] = None,
                       transport: Optional[str] = None,
                       note: Optional[str] = None,
                       degraded: Optional[dict] = None) -> Optional[TrackerError]:
    receipt = {
        "type": "sync",
        "id": spec_id,
        "tracker_id": tracker_id,
        "status": status,
        "event": event,
        "transport": transport,
        "merges": [],
        "note": note,
        # Degradation is STRUCTURED, never a sentence in `note` (epic contract).
        "degraded": degraded,
        "timestamp": now_iso(),
    }
    runs = Path(flow_dir) / "sync-runs"
    ts_slug = receipt["timestamp"].replace(":", "").replace("-", "").replace(".", "")
    return atomic_write_json(runs / f"sync-{spec_id}-{ts_slug}.json", receipt)
