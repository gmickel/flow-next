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
would deadlock every future writer on a artifact nobody owns.
"""

from __future__ import annotations

import contextlib
import errno
import json
import os
import shutil
import socket
import time
from pathlib import Path
from typing import Iterator

#: R8b constants - fixed by the spec, not tunables.
LOCK_TIMEOUT_S = 10.0
STALE_OWNER_S = 120.0

_POLL_S = 0.05


class ConfigLockTimeout(TimeoutError):
    """Could not acquire the config lock within LOCK_TIMEOUT_S."""


def _lock_dir(flow_dir: Path) -> Path:
    return Path(flow_dir) / ".locks" / "config.d"


def _pid_alive(pid: int) -> bool:
    """Best-effort liveness. Unknowable states count as ALIVE (never reclaim
    a lock we cannot prove abandoned)."""
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


@contextlib.contextmanager
def config_lock(flow_dir: Path, *, timeout_s: float = LOCK_TIMEOUT_S) -> Iterator[None]:
    """Acquire the shared config-writer lock, or raise ConfigLockTimeout.

    Reentrancy is deliberately NOT supported: a writer that needs the lock
    twice in one call stack is two writers racing themselves.
    """
    lock = _lock_dir(flow_dir)
    lock.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout_s
    while True:
        try:
            lock.mkdir()
            break
        except FileExistsError:
            if _owner_is_stale(lock, time.time()):
                # Reclaim: remove and retry. A concurrent reclaimer may win the
                # subsequent mkdir - that is the normal contention path, not an
                # error.
                shutil.rmtree(lock, ignore_errors=True)
                continue
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
        shutil.rmtree(lock, ignore_errors=True)
