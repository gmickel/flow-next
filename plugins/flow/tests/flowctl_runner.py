"""Test-only flowctl entry: import the module, then call its ``main()``.

A script run as ``__main__`` is recompiled on every spawn; an imported module
reuses its cached bytecode. Each spawn is still its own process, so exit codes,
stdout/stderr and env behave exactly as a script run. ``sys.path[0]`` and
``sys.argv[0]`` are set to what a script run of ``scripts/flowctl.py`` sees, so
argparse's program name and every usage/error line stay byte-identical.
Tests spawn this through ``flowctl_test_support.FLOWCTL_CMD``.
"""

import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "flowctl.py"
sys.path[0] = str(SCRIPT.parent)
sys.argv[0] = str(SCRIPT)

import flowctl  # noqa: E402

flowctl.main()
