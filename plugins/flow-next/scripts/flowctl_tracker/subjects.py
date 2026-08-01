"""Typed tracker subjects (spec | chart | decision) for the lifecycle facade.

fn-135.5 / R42: chart projection reuses the facade through subject-aware
load/write/collision paths. Spec remains the default kind; chart and decision
subjects store locator + provenance on their own sidecars without mutating
spec metadata or treating tracker ids as chart identity.
"""

from __future__ import annotations

import contextlib
import errno
import os
import re
import stat as stat_mod
import time
from pathlib import Path
from typing import Iterator, Optional, Union

from .lifecycle.helpers import (Result, atomic_write_json, default_tracker,
                                derive_link_state, dict_, leaf_is_safe,
                                merged_tracker, now_iso)
from .types import ErrorClass, TrackerError

SUBJECT_KINDS = frozenset({"spec", "chart", "decision"})

# Canonical decision id: fn-N.D<n> (chart-qualified).
_DECISION_ID_RE = re.compile(r"^(?P<chart>fn-\d+)\.D(?P<n>[1-9]\d*)$", re.I)
_CHART_ID_RE = re.compile(r"^fn-\d+$", re.I)


def parse_decision_id(raw: str) -> Optional[tuple[str, int]]:
    m = _DECISION_ID_RE.fullmatch((raw or "").strip())
    if not m:
        return None
    return m.group("chart").lower(), int(m.group("n"))


def validate_subject_id(kind: str, subject_id: str) -> Optional[TrackerError]:
    kind = (kind or "").strip().lower()
    sid = (subject_id or "").strip()
    if kind not in SUBJECT_KINDS:
        return TrackerError(
            ErrorClass.INVALID_INPUT,
            f"unknown subject kind {kind!r}",
            subtype="subject_kind",
        )
    if not sid:
        return TrackerError(
            ErrorClass.INVALID_INPUT,
            "subject id required",
            subtype="subject_id",
        )
    if kind == "spec":
        # Spec ids are free-form (fn-N-slug or tracker-keyed); non-empty is enough.
        return None
    if kind == "chart":
        if not _CHART_ID_RE.fullmatch(sid):
            return TrackerError(
                ErrorClass.INVALID_INPUT,
                f"invalid chart id {sid!r}",
                subtype="subject_id",
            )
        return None
    if parse_decision_id(sid) is None:
        return TrackerError(
            ErrorClass.INVALID_INPUT,
            f"invalid decision id {sid!r} (expected <chart-id>.D<n>)",
            subtype="subject_id",
        )
    return None


def subject_json_path(flow_dir: Path, kind: str, subject_id: str) -> Path:
    kind = kind.strip().lower()
    sid = subject_id.strip()
    flow_dir = Path(flow_dir)
    if kind == "spec":
        return flow_dir / "specs" / f"{sid}.json"
    if kind == "chart":
        return flow_dir / "charts" / f"{sid}.json"
    parsed = parse_decision_id(sid)
    if parsed is None:
        # Caller should have validated; fall back to a non-resolving path.
        return flow_dir / "charts" / "_invalid" / f"{sid}.json"
    chart_id, n = parsed
    return flow_dir / "charts" / chart_id / f"{n}.json"


def load_subject(
    flow_dir: Path, kind: str, subject_id: str
) -> Union[tuple[Path, dict, dict], TrackerError]:
    """Load subject sidecar + merged tracker block.

    Returns (path, data, tracker) or TrackerError.
    """
    bad = validate_subject_id(kind, subject_id)
    if bad:
        return bad
    kind = kind.strip().lower()
    sid = subject_id.strip()
    if kind == "chart":
        sid = sid.lower()
    elif kind == "decision":
        parsed = parse_decision_id(sid)
        assert parsed is not None
        chart_id, n = parsed
        sid = f"{chart_id.lower()}.D{n}"
    path = subject_json_path(flow_dir, kind, sid)
    if kind in ("decision", "chart"):
        unsafe = leaf_is_safe(Path(flow_dir) / "charts", path)
    else:
        unsafe = leaf_is_safe(Path(flow_dir) / "specs", path)
    if unsafe:
        return unsafe
    if not path.is_file():
        return TrackerError(
            ErrorClass.NOT_FOUND,
            f"{kind} {sid!r} not found",
            subtype=kind,
        )
    try:
        data = path.read_text(encoding="utf-8")
        import json  # noqa: PLC0415

        obj = json.loads(data)
    except (OSError, ValueError) as exc:
        return TrackerError(
            ErrorClass.TRANSPORT,
            f"unreadable {kind}: {exc}",
            subtype=kind,
        )
    if not isinstance(obj, dict):
        return TrackerError(
            ErrorClass.INVALID_INPUT,
            f"{kind} json is not an object",
            subtype=kind,
        )
    tracker = merged_tracker(obj)
    return path, obj, tracker


def write_subject_tracker(
    path: Path, data: dict, tracker: dict
) -> Optional[TrackerError]:
    data = dict(data)
    data["tracker"] = tracker
    data["updated_at"] = now_iso()
    return atomic_write_json(path, data)


# Chart resource lock: the SAME lock file flowctl's chart WAL transactions
# hold around their sidecar read-modify-write cycles. Projection sidecar
# writes must contend on it, or a post-commit projection can persist a tracker
# link between another chart command's load and publish and be clobbered by
# that command's older JSON (duplicate remote issues on the next projection).
_CHARTS_RESOURCE_LOCK_NAME = "charts-resource.lock"
_CHART_PROJECTION_LOCK_NAME = "chart-projection.lock"
_CHARTS_LOCK_TIMEOUT_S = 10.0
# The projection waiter must outlast a normally-held lock: a holder spans
# several remote requests, each with a 30s default budget
# (types.DEFAULT_TIMEOUT_S), so a 10s wait would abandon projections that are
# merely queued behind a healthy holder. A still-failing acquisition keeps the
# best-effort lock_timeout error shape; convergence then rests on the holder's
# drain loop in project_chart, which re-projects any state a timed-out waiter
# committed locally.
_CHART_PROJECTION_LOCK_TIMEOUT_S = 120.0
_CHARTS_LOCK_POLL_S = 0.02


def charts_resource_lock_file(flow_dir: Path) -> Path:
    """Path of flowctl's chart WAL/mutation lock (.flow/locks/charts-resource.lock)."""
    return Path(flow_dir) / "locks" / _CHARTS_RESOURCE_LOCK_NAME


def chart_projection_lock_file(flow_dir: Path) -> Path:
    """Path of the chart projection lock (.flow/locks/chart-projection.lock)."""
    return Path(flow_dir) / "locks" / _CHART_PROJECTION_LOCK_NAME


def _try_kernel_lock(fd: int) -> bool:
    """One non-blocking exclusive acquisition - same mechanism as flowctl's
    cross_process_lock (flock on POSIX, msvcrt byte lock on Windows) so the
    two sides genuinely contend on the shared lock file."""
    if os.name == "nt":  # pragma: no cover - exercised on the Windows CI row
        import msvcrt  # noqa: PLC0415

        os.lseek(fd, 0, os.SEEK_SET)
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            return True
        except OSError as e:
            if e.errno in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                return False
            raise

    import fcntl  # noqa: PLC0415

    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError as e:
        if e.errno in (errno.EACCES, errno.EAGAIN):
            return False
        raise


def _release_kernel_lock(fd: int) -> None:
    if os.name == "nt":  # pragma: no cover - exercised on the Windows CI row
        import msvcrt  # noqa: PLC0415

        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        return

    import fcntl  # noqa: PLC0415

    fcntl.flock(fd, fcntl.LOCK_UN)


@contextlib.contextmanager
def _bounded_file_lock(
    lock_path: Path, *, timeout_s: float, label: str
) -> Iterator[None]:
    """Bounded exclusive kernel lock on a named lock file.

    Raises ConfigLockTimeout on timeout so callers map it to the same
    CONFLICT/lock_timeout TrackerError as the config writer lock.
    """
    from .config_lock import ConfigLockTimeout  # noqa: PLC0415

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        st = os.lstat(lock_path)
        if not stat_mod.S_ISREG(st.st_mode):
            raise ConfigLockTimeout(
                f"{label} lock path is not a regular file: {lock_path}"
            )
    except FileNotFoundError:
        pass
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(lock_path, flags, 0o600)
    acquired = False
    try:
        if os.fstat(fd).st_size == 0:
            os.write(fd, b"\0")
        deadline = time.monotonic() + max(0.0, timeout_s)
        while not acquired:
            acquired = _try_kernel_lock(fd)
            if acquired:
                break
            if time.monotonic() >= deadline:
                raise ConfigLockTimeout(
                    f"timed out acquiring {label} lock {lock_path} "
                    f"after {timeout_s:g}s"
                )
            time.sleep(_CHARTS_LOCK_POLL_S)
        yield
    finally:
        if acquired:
            with contextlib.suppress(OSError):
                _release_kernel_lock(fd)
        with contextlib.suppress(OSError):
            os.close(fd)


@contextlib.contextmanager
def charts_resource_lock(
    flow_dir: Path, *, timeout_s: float = _CHARTS_LOCK_TIMEOUT_S
) -> Iterator[None]:
    """Bounded exclusive kernel lock on the chart resource lock file."""
    with _bounded_file_lock(
        charts_resource_lock_file(flow_dir),
        timeout_s=timeout_s, label="chart resource",
    ):
        yield


@contextlib.contextmanager
def chart_projection_lock(
    flow_dir: Path, *, timeout_s: float = _CHART_PROJECTION_LOCK_TIMEOUT_S
) -> Iterator[None]:
    """Cross-process serialization of whole chart projections.

    A DEDICATED lock file, not the chart WAL lock: holding the WAL lock
    across the remote read/update span would block local chart mutations on
    network latency. The projection reloads chart + decision state inside
    this lock, so an older caller re-projects the newest committed state
    (convergent) instead of overwriting remote bodies with stale content.
    Lock ordering: projection lock OUTERMOST, then charts_resource_lock,
    then config_lock (via locked_subject_write).
    """
    with _bounded_file_lock(
        chart_projection_lock_file(flow_dir),
        timeout_s=timeout_s, label="chart projection",
    ):
        yield


def locked_subject_write(
    flow_dir: Path,
    kind: str,
    subject_id: str,
    mutate,
    *,
    collision_id: Optional[str] = None,
) -> Result:
    """Reload + mutate + persist subject tracker under the shared writer lock.

    Chart/decision subjects additionally serialize against flowctl's chart
    resource lock (taken FIRST, matching chart commands' charts-then-inner
    ordering) so projection writes cannot interleave with a chart command's
    WAL read-modify-write on the same sidecar.
    """
    from .config_lock import ConfigLockTimeout, config_lock  # noqa: PLC0415

    try:
        with contextlib.ExitStack() as stack:
            if (kind or "").strip().lower() in ("chart", "decision"):
                stack.enter_context(charts_resource_lock(flow_dir))
            stack.enter_context(config_lock(flow_dir))
            loaded = load_subject(flow_dir, kind, subject_id)
            if isinstance(loaded, TrackerError):
                return loaded
            path, data, tracker = loaded
            if collision_id is not None:
                hit = subject_collision(
                    flow_dir, collision_id, except_kind=kind, except_id=subject_id
                )
                if hit:
                    return hit
            tracker = mutate(tracker)
            if isinstance(tracker, TrackerError):
                return tracker
            werr = write_subject_tracker(path, data, tracker)
            if werr:
                return werr
            return tracker
    except ConfigLockTimeout as exc:
        return TrackerError(
            ErrorClass.CONFLICT, str(exc), subtype="lock_timeout"
        )


def iter_all_subject_trackers(flow_dir: Path):
    """Yield (kind, subject_id, tracker) for specs, charts, and decisions."""
    flow_dir = Path(flow_dir)
    specs = flow_dir / "specs"
    if specs.is_dir():
        for path in sorted(specs.glob("*.json")):
            try:
                import json  # noqa: PLC0415

                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not isinstance(data, dict):
                continue
            sid = data.get("id") or path.stem
            yield "spec", str(sid), dict_(data.get("tracker"))

    charts = flow_dir / "charts"
    if not charts.is_dir():
        return
    for path in sorted(charts.glob("*.json")):
        if path.name.startswith("."):
            continue
        try:
            import json  # noqa: PLC0415

            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        sid = data.get("id") or path.stem
        yield "chart", str(sid), dict_(data.get("tracker"))
        # Decision records live under charts/<chart-id>/<n>.json
        chart_dir = charts / str(sid)
        if not chart_dir.is_dir():
            continue
        for dpath in sorted(chart_dir.glob("*.json")):
            if not dpath.stem.isdigit():
                continue
            try:
                import json  # noqa: PLC0415

                ddata = json.loads(dpath.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not isinstance(ddata, dict):
                continue
            did = ddata.get("id") or f"{sid}.D{dpath.stem}"
            yield "decision", str(did), dict_(ddata.get("tracker"))


def subject_collision(
    flow_dir: Path,
    durable_id: str,
    *,
    except_kind: Optional[str] = None,
    except_id: Optional[str] = None,
) -> Optional[TrackerError]:
    """One durable id per subject across specs, charts, and decisions."""
    for kind, sid, state in iter_all_subject_trackers(flow_dir):
        if (
            except_kind is not None
            and except_id is not None
            and kind == except_kind
            and str(sid) == str(except_id)
        ):
            continue
        if state.get("id") and str(state["id"]) == str(durable_id):
            return TrackerError(
                ErrorClass.CONFLICT,
                f"Tracker id {durable_id} already linked to {kind} {sid}",
                subtype="durable_collision",
                details={"owner": sid, "kind": kind, "durable": durable_id},
            )
    return None


def ensure_tracker_block(data: dict) -> dict:
    """Ensure subject data has a tracker block with schema defaults."""
    raw = dict_(data.get("tracker"))
    if not raw:
        raw = default_tracker()
    data = dict(data)
    data["tracker"] = {**default_tracker(), **raw}
    data["tracker"]["linkState"] = derive_link_state(raw)
    return data


def charts_projection_enabled(config: dict) -> bool:
    """True iff tracker.charts is the literal string 'on' (fail-closed).

    Bool true / typos / perEvent verbs never activate - same string-enum
    discipline as pipeline.qa.
    """
    tracker = dict_(config.get("tracker"))
    val = tracker.get("charts")
    if isinstance(val, str):
        return val.strip().lower() == "on"
    return False


def projection_gate(config: dict) -> dict:
    """Structured skip/active gate for chart projection.

    Local chart mutations always succeed; this only describes remote projection.
    """
    from .lifecycle.helpers import tracker_type  # noqa: PLC0415

    if not charts_projection_enabled(config):
        return {
            "active": False,
            "skipped": "tracker.charts_off",
            "reason": "tracker.charts is off or unset",
        }
    provider = tracker_type(config)
    if provider is None:
        return {
            "active": False,
            "skipped": "bridge_inactive",
            "reason": "tracker bridge is inactive or unconfigured",
        }
    return {"active": True, "provider": provider, "skipped": None}


def caps_of(config: dict) -> dict:
    from .relate.ledger import caps_of as _caps  # noqa: PLC0415

    return _caps(config)


def subject_marker_token(kind: str, subject_id: str) -> str:
    """Stable token for event markers / receipts (replaces bare spec=)."""
    return f"{kind}:{subject_id}"
