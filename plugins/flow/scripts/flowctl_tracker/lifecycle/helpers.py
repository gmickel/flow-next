"""Shared plumbing for lifecycle verbs (fn-140.2). Never raises across the boundary."""

from __future__ import annotations

import json
from contextlib import contextmanager
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
SPEC_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def validate_spec_id(spec_id) -> Optional[TrackerError]:
    if not isinstance(spec_id, str) or ".." in spec_id or not SPEC_ID_RE.fullmatch(spec_id):
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
        base_dir.resolve()
    except OSError:
        return TrackerError(ErrorClass.INVALID_INPUT,
                            f"unresolvable path {leaf}", subtype="path")
    # Containment is derived from ONE resolve, not two. Resolving base and leaf
    # INDEPENDENTLY was a Windows flake source (fn-120.4): non-strict
    # `Path.resolve()` stops expanding on a transient error (ntpath's
    # allowed-winerror list covers SHARING_VIOLATION / ACCESS_DENIED), so under
    # concurrent writers one side could keep the 8.3 `RUNNER~1` prefix while the
    # other expanded it - two spellings of the SAME path comparing unequal and
    # producing a false "escapes" INVALID_INPUT (~50% on windows-latest: run
    # 30921678923 RED, identical re-run 30923544649 GREEN). Normalize the leaf
    # LEXICALLY against base_dir instead; `..` is the only way out, and the
    # no-follow walk below is what keeps a symlink from redirecting the write.
    try:
        rel = os.path.relpath(os.path.abspath(str(leaf)),
                              os.path.abspath(str(base_dir)))
    except (OSError, ValueError):
        # Windows raises ValueError across drives - a different drive is an escape.
        return TrackerError(ErrorClass.INVALID_INPUT,
                            f"{leaf} escapes {base_dir}", subtype="path")
    if ".." in Path(rel).parts:
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
            # Windows NTFS junctions/mount points are reparse points, NOT
            # symlinks: lstat flags them via st_reparse_tag while S_ISLNK
            # stays false, yet a write through them follows the redirect out
            # of tree. Reject ANY nonzero tag fail-closed instead of adding a
            # second resolve() - re-resolving the leaf is exactly the
            # divergent-resolve flake this walk replaced. st_reparse_tag is
            # Windows-only (getattr -> 0 elsewhere), so this is a POSIX no-op.
            if getattr(st, "st_reparse_tag", 0):
                return TrackerError(ErrorClass.INVALID_INPUT,
                                    f"{probe} is a reparse point; refusing to "
                                    "write through it", subtype="path")
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
    from ..config_io import load_raw_config  # noqa: PLC0415

    return load_raw_config(Path(flow_dir) / "config.json") or {}


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


def derive_link_state(tracker_block: Any) -> str:
    """LEGACY MIGRATION read. Explicit linkState wins; else migrate."""
    block = dict_(tracker_block)
    explicit = block.get("linkState")
    if isinstance(explicit, str) and explicit in LINK_STATES:
        return explicit
    durable = block.get("id")
    ident = block.get("identifier")
    if durable is not None and str(durable).strip() != "":
        return "linked"
    if ident is not None and str(ident).strip() != "":
        return "identifier_only"
    return "unlinked"


def merged_tracker(spec_data: Any) -> dict:
    """Spec tracker block with schema defaults filled in.

    linkState is derived from the RAW block, not defaulted: a legacy record
    that predates the field ({"id": ..., "identifier": ...}) must migrate to
    linked/identifier_only, and merging the explicit "unlinked" default first
    would defeat derive_link_state's migration read (reproduced by review:
    create duplicated the issue; status/relate/sync-body rejected the link)."""
    raw = dict_(dict_(spec_data).get("tracker"))
    merged = {**default_tracker(), **raw}
    merged["linkState"] = derive_link_state(raw)
    return merged


#: Linear-only spec sidecar fields placing the projected issue in a Project
#: (fn-182 / #315 option 1). They are NOT in default_tracker(): an absent field
#: means UNMANAGED, never "none". Absent keys are omitted from every payload, so
#: today's create/update bytes are unchanged and a Project set tracker-side is
#: never cleared by flow-next (R4). flow-next carries the id it is given; it
#: never creates or manages Projects.
PROJECT_SIDECAR_FIELDS = ("projectId", "projectMilestoneId")


def spec_project_fields(tracker_block: Any) -> Result:
    """Present, non-empty sidecar project ids in Linear input-key form.

    Returns {} when unmanaged. A present-but-unusable value (empty string,
    non-string) is an INVALID_INPUT error rather than a dropped key - a silent
    drop would project the issue with no Project and no complaint."""
    block = dict_(tracker_block)
    fields: dict = {}
    for key in PROJECT_SIDECAR_FIELDS:
        if key not in block:
            continue
        value = block[key]
        if value is None:
            continue
        if not isinstance(value, str) or not value.strip():
            return TrackerError(
                ErrorClass.INVALID_INPUT,
                f"tracker.{key} must be a non-empty string id or absent; "
                f"got {value!r}",
                subtype="project")
        fields[key] = value.strip()
    return fields


def parent_value(value: Any, *, source: str) -> Result:
    """A parent issue identifier, trimmed; None when absent.

    The spec's `tracker.parent` is a creation input only: it is read when an
    issue is created for the spec and never sent again. Like the Project
    fields, a present-but-unusable value errors instead of being dropped."""
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        return TrackerError(
            ErrorClass.INVALID_INPUT,
            f"{source} must be a non-empty parent issue identifier or absent; "
            f"got {value!r}",
            subtype="parent")
    return value.strip()


def spec_parent_field(tracker_block: Any) -> Result:
    return parent_value(dict_(tracker_block).get("parent"),
                        source="tracker.parent")


def spec_path(flow_dir: Path, spec_id: str) -> Path:
    from ..spec_store import spec_path as _spec_path  # noqa: PLC0415
    return _spec_path(flow_dir, spec_id)


def load_spec(flow_dir: Path, spec_id: str) -> Union[tuple[Path, dict], TrackerError]:
    from ..spec_store import load_spec_doc  # noqa: PLC0415
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
    loaded = load_spec_doc(path, spec_id=spec_id)
    if isinstance(loaded, TrackerError):
        return loaded
    data, _body = loaded
    return path, data


def iter_tracker_states(flow_dir: Path):
    from ..spec_store import iter_spec_trackers  # noqa: PLC0415
    yield from iter_spec_trackers(flow_dir)


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
    from ..spec_store import write_spec_tracker  # noqa: PLC0415
    return write_spec_tracker(path, tracker, spec_id=spec_data.get("id"))


def locked_tracker_write(flow_dir: Path, spec_id: str, mutate, *,
                         collision_id: Optional[str] = None) -> Result:
    from ..config_lock import ConfigLockTimeout, config_lock  # noqa: PLC0415
    try:
        with config_lock(flow_dir):
            reloaded = load_spec(flow_dir, spec_id)
            if isinstance(reloaded, TrackerError):
                return reloaded
            path, spec = reloaded
            if collision_id is not None:
                hit = collision(flow_dir, collision_id, except_spec=spec_id)
                if hit:
                    return hit
            tracker = merged_tracker(spec)
            tracker = mutate(tracker)
            if isinstance(tracker, TrackerError):
                return tracker
            werr = write_tracker_block(path, spec, tracker)
            if werr:
                return werr
            return tracker
    except ConfigLockTimeout as exc:
        return TrackerError(ErrorClass.CONFLICT, str(exc), subtype="lock_timeout")


def write_sync_receipt(flow_dir: Path, *, spec_id: str, status: str,
                       tracker_id: Optional[str] = None,
                       event: Optional[str] = None,
                       transport: Optional[str] = None,
                       note: Optional[str] = None,
                       degraded: Optional[dict] = None,
                       details: Optional[dict] = None) -> Optional[TrackerError]:
    return None
