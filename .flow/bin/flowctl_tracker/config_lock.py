"""The shared `.flow/config.json` writer lock (fn-139.3, R8b).

One named design, used by EVERY config writer - `set_config`, `cmd_init`, and
the resolve transaction. An atomic write alone prevents torn files but not
stale-read clobbering: two writers can read, compute different changes, then
serially replace the whole file, and the second silently discards the first.

Mechanism: an **atomic lock directory** at `.flow/.locks/config.d` - `mkdir` is
atomic on both POSIX and Windows - containing `owner.json` with
`{pid, host, acquired_at}`.

Recovery is rule-based, never manual: an owner older than `STALE_OWNER_S`
whose pid is not alive **on the same host** is stale and reclaimable. A holder
that crashed between `mkdir` and writing `owner.json` leaves an ownerless
directory; that too is reclaimed by age (directory mtime), because refusing
would deadlock every future writer on an artifact nobody owns.

Reclamation is serialized by an atomic `os.rename` of the stale directory to a
unique trash name: exactly one contender wins the rename, and the removal only
ever targets the renamed path - never the live lock path. Removing the stale
directory in place had an ABA race: two contenders both classify it stale, A
removes and acquires a FRESH lock, then B's delayed removal deletes A's new
lock and B acquires while A is inside its critical section.
"""

from __future__ import annotations

import contextlib
import errno
import json
import os
import shutil
import socket
import stat as stat_mod
import time
from pathlib import Path
from typing import Iterator

#: R8b constants - fixed by the spec, not tunables.
LOCK_TIMEOUT_S = 10.0
STALE_OWNER_S = 120.0

_POLL_S = 0.05


class ConfigLockTimeout(TimeoutError):
    """Could not acquire the config lock within LOCK_TIMEOUT_S."""


class ConfigLockUnsafe(RuntimeError):
    """The lock path is a symlink (or otherwise not a plain directory).

    A malicious checkout can commit `.flow/.locks` as a symlink pointing
    outside the repository; acquisition and release would then create and
    recursively DELETE an external directory. Refuse instead - same policy as
    flowctl's other managed-path symlink guards.
    """


def _lock_dir(flow_dir: Path) -> Path:
    return Path(flow_dir) / ".locks" / "config.d"


def _assert_component_safe(path: Path) -> None:
    """No-follow check on one lock-path component. Absent is fine (we create
    it); anything present must be a plain directory, never a symlink."""
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        return
    except OSError:
        return  # unreadable: mkdir/rename below will surface the real error
    if stat_mod.S_ISLNK(st.st_mode) or not stat_mod.S_ISDIR(st.st_mode):
        raise ConfigLockUnsafe(
            f"{path} is not a plain directory; refusing to operate on a "
            "symlinked or spoofed lock path")


def _assert_lock_path_safe(flow_dir: Path, lock: Path) -> None:
    _assert_component_safe(lock.parent)   # .flow/.locks
    _assert_component_safe(lock)          # .flow/.locks/config.d


if os.name == "nt":  # pragma: no cover - exercised on the Windows CI row
    def _pid_alive(pid: int) -> bool:
        """Windows liveness WITHOUT os.kill: `os.kill(pid, sig)` with any sig
        other than the two CTRL events calls TerminateProcess - a liveness
        *probe* built on it KILLS the lock holder (or an unrelated pid-recycled
        process). Query, never signal."""
        if pid <= 0:
            return False
        import ctypes
        from ctypes import wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        ERROR_ACCESS_DENIED = 5
        STILL_ACTIVE = 259
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            # Access denied means the process exists but is not ours - alive.
            return ctypes.get_last_error() == ERROR_ACCESS_DENIED
        try:
            code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return True  # unknowable counts as alive - never reclaim on doubt
            return code.value == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
else:
    def _pid_alive(pid: int) -> bool:
        """Best-effort liveness. Unknowable states count as ALIVE (never
        reclaim a lock we cannot prove abandoned)."""
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True  # exists, owned by someone else
        except OSError as exc:  # pragma: no cover - platform-specific errno spread
            return exc.errno != errno.ESRCH
        return True


def _owner_is_stale(lock: Path, now: float) -> bool:
    owner_path = lock / "owner.json"
    try:
        owner = json.loads(owner_path.read_text(encoding="utf-8"))
        acquired_at = float(owner["acquired_at"])
        pid = int(owner["pid"])
        host = str(owner["host"])
    except (OSError, ValueError, KeyError, TypeError):
        # No readable owner: either the holder crashed between mkdir and the
        # owner write, or the file is corrupt. Fall back to directory age -
        # refusing forever would deadlock every writer on an orphan.
        try:
            return (now - lock.stat().st_mtime) > STALE_OWNER_S
        except OSError:
            return False  # raced with a release; treat as held
    if (now - acquired_at) <= STALE_OWNER_S:
        return False
    if host != socket.gethostname():
        # A different host's pid space is unknowable (shared/network checkout).
        # Age alone must not reclaim there - fail closed.
        return False
    return not _pid_alive(pid)


def _acquire_reclaimer_claim(lock: Path):
    """Take the reclaimer claim as an OS FILE LOCK, or return None.

    The claim's ONE job is to make the staleness re-check race-free, and it
    must not itself need stale recovery - an aged-out mkdir claim reintroduced
    the exact ABA it existed to close (a contender deleting a live claim off
    an old observation). An OS lock has neither problem: the kernel releases
    it when the holder dies (crash recovery for free, no age heuristic) and
    nothing ever deletes the claim path - the file persists, only the lock
    state changes. flock on POSIX, msvcrt byte-range locking on Windows.
    """
    path = lock.with_name("config.d.reclaimer.lock")
    # No-follow semantics on the claim leaf, same policy as the directory
    # components: a malicious checkout can commit this path as a symlink (or a
    # FIFO/device) pointing outside the repository, and a following open would
    # create or open the external target. lstat rejects what exists;
    # O_NOFOLLOW closes the check-to-open window where the platform has it.
    try:
        st = os.lstat(path)
        if not stat_mod.S_ISREG(st.st_mode):
            raise ConfigLockUnsafe(
                f"{path} is not a regular file; refusing to open a symlinked "
                "or special claim leaf")
    except FileNotFoundError:
        pass
    except OSError:
        return None
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    try:
        f = os.fdopen(os.open(path, flags, 0o644), "r+b")
    except OSError:
        return None
    try:
        if os.name == "nt":  # pragma: no cover - exercised on the Windows CI row
            import msvcrt
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return f
    except OSError:
        f.close()
        return None


def _release_reclaimer_claim(f) -> None:
    try:
        if os.name == "nt":  # pragma: no cover - exercised on the Windows CI row
            import msvcrt
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except OSError:  # pragma: no cover - close() below still drops the lock
        pass
    finally:
        f.close()


def _try_reclaim(lock: Path) -> bool:
    """Reclaim a stale lock without the ABA race, in two layers:

    1. The **reclaimer claim** (an OS file lock, see above) serializes
       reclaimers and makes the staleness RE-CHECK inside it race-free: while
       the claim is held the live path cannot change hands - acquirers cannot
       `mkdir` an occupied path and no other reclaimer can rename it. The
       hole in check-then-remove was a contender acting on a classification
       made before another contender reclaimed and re-acquired.
    2. Removal goes through an atomic rename to a unique trash name, so the
       live lock path is never the target of a recursive delete.
    """
    claim = _acquire_reclaimer_claim(lock)
    if claim is None:
        return False  # another reclaimer is active; wait through the deadline loop
    try:
        if not _owner_is_stale(lock, time.time()):
            return False  # the world changed before we got the claim
        trash = lock.with_name(f"config.d.reclaim-{os.getpid()}-{time.monotonic_ns()}")
        try:
            os.rename(lock, trash)
        except OSError:
            return False  # removal not possible right now (permissions, AV, ro-fs)
        shutil.rmtree(trash, ignore_errors=True)
        return True
    finally:
        _release_reclaimer_claim(claim)


@contextlib.contextmanager
def config_lock(flow_dir: Path, *, timeout_s: float = LOCK_TIMEOUT_S) -> Iterator[None]:
    """Acquire the shared config-writer lock, or raise ConfigLockTimeout.

    Reentrancy is deliberately NOT supported: a writer that needs the lock
    twice in one call stack is two writers racing themselves.
    """
    lock = _lock_dir(flow_dir)
    _assert_lock_path_safe(flow_dir, lock)
    lock.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout_s
    while True:
        try:
            lock.mkdir()
            break
        except FileExistsError:
            if _owner_is_stale(lock, time.time()) and _try_reclaim(lock):
                # Reclaimed: retry the mkdir immediately. If someone else
                # acquires first, their FRESH owner is not stale, so this
                # branch cannot repeat - the loop is bounded by the deadline.
                continue
        except PermissionError:
            # Windows: a directory whose deletion is still PENDING (the last
            # holder released while a reader kept a handle open) fails mkdir
            # with ERROR_ACCESS_DENIED, not FileExistsError. Transient - poll.
            pass
        # Held, un-reclaimable, delete-pending, or the reclaim rename failed
        # (permissions, antivirus, read-only fs): all of these go through the
        # deadline so acquisition can never spin forever.
        if time.monotonic() >= deadline:
            raise ConfigLockTimeout(
                f"could not acquire {lock} within {timeout_s:.0f}s; "
                "holder appears alive (see owner.json)"
            ) from None
        time.sleep(_POLL_S)
    try:
        (lock / "owner.json").write_text(json.dumps({
            "pid": os.getpid(),
            "host": socket.gethostname(),
            "acquired_at": time.time(),
        }), encoding="utf-8")
        yield
    finally:
        _release(lock)


def _release(lock: Path) -> None:
    """Windows-robust release. A concurrent staleness check holds owner.json
    open for milliseconds; deleting it in that window raises a sharing
    violation, and `rmtree(ignore_errors=True)` swallowed it - the lock then
    NEVER released, deadlocking every writer until the 120s stale rule fired
    (measured on the windows-latest CI row as 10s acquisition timeouts).
    Retry briefly; sharing violations clear as soon as the reader closes.
    """
    deadline = time.monotonic() + 5.0
    while True:
        try:
            try:
                (lock / "owner.json").unlink()
            except FileNotFoundError:
                pass
            os.rmdir(lock)
            return
        except FileNotFoundError:
            return
        except OSError:
            if time.monotonic() >= deadline:
                shutil.rmtree(lock, ignore_errors=True)  # last resort
                return
            time.sleep(0.01)
