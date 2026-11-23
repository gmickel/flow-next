"""Shared test support for tests that spawn flowctl (fn-256 R1, R3).

``FLOWCTL_CMD`` spawns ``flowctl_runner.py``, which imports the flowctl module
instead of running ``scripts/flowctl.py`` as a script. Tests that exercise the
real product entry (launcher and bootstrap parity) spawn ``FLOWCTL_SCRIPT`` or
the launchers directly instead.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FLOWCTL_SCRIPT = HERE.parent / "scripts" / "flowctl.py"
RUNNER = HERE / "flowctl_runner.py"
if not RUNNER.is_file():
    raise FileNotFoundError(f"flowctl test runner not found: {RUNNER}")

FLOWCTL_CMD = (sys.executable, str(RUNNER))


class MemoryRepoTemplate:
    """One ``init`` + ``memory.enabled`` + ``memory init`` repo per test class.

    ``init_repo(dest)`` copies the template into the test's own directory, so
    each test gets an isolated repo and the template itself is never handed
    out. Set ``TEMPLATE_GIT = True`` for a template that is also a git repo.
    """

    TEMPLATE_GIT = False

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        cls._template = Path(tmp.name)
        if cls.TEMPLATE_GIT:
            for argv in (
                ["git", "init", "-q"],
                ["git", "config", "user.email", "t@t"],
                ["git", "config", "user.name", "t"],
            ):
                subprocess.check_call(argv, cwd=cls._template, stdout=subprocess.DEVNULL)
        for args in (["init"], ["config", "set", "memory.enabled", "true"], ["memory", "init"]):
            subprocess.check_call(
                [*FLOWCTL_CMD, *args, "--json"], cwd=cls._template, stdout=subprocess.DEVNULL
            )

    def init_repo(self, dest: Path) -> Path:
        """Copy the class template into ``dest``; return its memory dir."""
        shutil.copytree(self._template, dest, dirs_exist_ok=True)
        return dest / ".flow" / "memory"
