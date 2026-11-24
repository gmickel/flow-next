"""Test-only edge entry: import the module, then call its ``main()``."""

import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "plugins" / "flow" / "skills" / "flow" / "scripts" / "edge.py"
sys.path[0] = str(SCRIPT.parent)
sys.argv[0] = str(SCRIPT)

import edge  # noqa: E402

edge.main()
