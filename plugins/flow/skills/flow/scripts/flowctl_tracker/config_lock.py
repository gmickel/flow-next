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


class ConfigLockUnavailable(ConfigLockTimeout):
    """The lock could not be CREATED at all - the filesystem denied it.

    Distinct from contention: no lock directory exists, so nobody holds it;
    `mkdir` itself was refused (unwritable `.flow/.locks`, an ACL denying
    add_subdirectory, a root-owned directory left by a container run). Waiting
    cannot help, so acquisition fails immediately instead of burning the
    deadline and then blaming a holder that never existed (#340).

    Subclasses ConfigLockTimeout so every existing `except ConfigLockTimeout`
    handler keeps working unchanged.
    """


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


def _read_owner(lock: Path) -> dict | None:
    """The owner facts, or None when there is no readable owner.json."""
    try:
        owner = json.loads((lock / "owner.json").read_text(encoding="utf-8"))
        return {"pid": int(owner["pid"]), "host": str(owner["host"]),
                "acquired_at": float(owner["acquired_at"])}
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _denied_detail(exc: OSError) -> str:
    """errno + strerror only. Interpreting *why* the OS said no (uid, mount
    flags, ACLs) is the host's job, not the lock's - report the fact."""
    code = errno.errorcode.get(exc.errno, exc.errno)
    return f"[{code}] {exc.strerror or exc}"


def _unavailable(lock: Path, exc: OSError, *, creating: Path) -> ConfigLockUnavailable:
    return ConfigLockUnavailable(
        f"config lock unavailable: cannot create {creating} - "
        f"{_denied_detail(exc)}; the lock at {lock} cannot be created or "
        f"inspected (a denied traversal also lands here, so holder state is "
        f"unknowable) - fix permissions under {lock.parent}"
    )


def _timeout_message(lock: Path, timeout_s: float, last_error: OSError | None) -> str:
    """Say what was actually observed. 'holder appears alive' is reserved for
    the case where an owner really was read (#340)."""
    head = f"could not acquire {lock} within {timeout_s:.0f}s; "
    if last_error is not None:
        # The path exists (fail-fast handled the absent case) but creating it
        # kept being denied: on Windows a delete is still pending, elsewhere
        # the parent or the directory itself is not writable by us.
        return (head + f"creating it kept being denied ({_denied_detail(last_error)}) "
                f"- on Windows a delete may still be pending, otherwise check "
                f"permissions on {lock.parent}")
    owner = _read_owner(lock)
    if owner is not None:
        age = max(0.0, time.time() - owner["acquired_at"])
        # Honesty (PR #349 review): an owner the staleness probe has already
        # proven reclaimable is not "alive" - reclamation itself is failing.
        if _owner_is_stale(lock, time.time()):
            return (head + f"owner (pid {owner['pid']} on {owner['host']}, "
                    f"acquired {age:.0f}s ago) is stale but reclamation is "
                    f"failing - check permissions on {lock.parent}")
        return (head + f"holder appears alive (pid {owner['pid']} on "
                f"{owner['host']}, acquired {age:.0f}s ago; see owner.json)")
    try:
        dir_age = max(0.0, time.time() - lock.stat().st_mtime)
    except OSError:
        return (head + "the directory exists with no readable owner.json and its "
                "age could not be read")
    remaining = STALE_OWNER_S - dir_age
    if remaining > 0:
        return (head + f"the directory exists with no readable owner.json "
                f"(no holder was observed); it becomes stale-reclaimable in "
                f"{remaining:.0f}s")
    return (head + f"the directory exists with no readable owner.json (no holder "
            f"was observed) and is already past the {STALE_OWNER_S:.0f}s stale "
            f"window - reclaiming it is failing; check permissions on {lock.parent}")


@contextlib.contextmanager
def config_lock(flow_dir: Path, *, timeout_s: float = LOCK_TIMEOUT_S) -> Iterator[None]:
    """Acquire the shared config-writer lock, or raise ConfigLockTimeout.

    Reentrancy is deliberately NOT supported: a writer that needs the lock
    twice in one call stack is two writers racing themselves.
    """
    lock = _lock_dir(flow_dir)
    _assert_lock_path_safe(flow_dir, lock)
    try:
        lock.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        # PermissionError, EROFS (plain OSError), ENOSPC... - environment
        # facts, not contention (#349 round 5).
        raise _unavailable(lock, exc, creating=lock.parent) from None
    deadline = time.monotonic() + timeout_s
    last_error: OSError | None = None
    while True:
        try:
            lock.mkdir()
            break
        except FileExistsError:
            last_error = None  # real contention: the path is occupied, not denied
            if _owner_is_stale(lock, time.time()) and _try_reclaim(lock):
                # Reclaimed: retry the mkdir immediately. If someone else
                # acquires first, their FRESH owner is not stale, so this
                # branch cannot repeat - the loop is bounded by the deadline.
                continue
        except OSError as exc:
            # PermissionError and friends (EROFS arrives as plain OSError -
            # #349 round 5; FileExistsError took its own branch above).
            # Windows: a directory whose deletion is still PENDING (the last
            # holder released while a reader kept a handle open) fails mkdir
            # with ERROR_ACCESS_DENIED, not FileExistsError. Transient - poll.
            # But a denial with NO directory there is not a pending delete and
            # not contention: nothing holds the lock and nothing will change,
            # so waiting out the deadline only delays a wrong answer (#340).
            # RACE GUARD (PR #349 review): a pending delete can finish
            # disappearing between the denied mkdir and the exists probe -
            # denied+absent on a SINGLE observation is not proof. Retry the
            # mkdir once immediately; only a second consecutive denial with
            # the path still absent is genuinely unavailable.
            denied = exc
            if not os.path.lexists(lock):
                try:
                    lock.mkdir()
                    break
                except FileExistsError:
                    last_error = None
                    continue
                except OSError as exc2:
                    if not os.path.lexists(lock):
                        # POSIX: denied twice with nothing there is a
                        # permissions fact - fail fast. Windows: a pending
                        # delete can misreport absent across both probes
                        # (PR #349 round 2), so keep polling to the deadline;
                        # the timeout message still reports the denial.
                        if os.name != "nt":
                            raise _unavailable(lock, exc2, creating=lock) from None
                    denied = exc2
            last_error = denied
        # Held, un-reclaimable, delete-pending, or the reclaim rename failed
        # (permissions, antivirus, read-only fs): all of these go through the
        # deadline so acquisition can never spin forever.
        if time.monotonic() >= deadline:
            raise ConfigLockTimeout(
                _timeout_message(lock, timeout_s, last_error)) from None
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
