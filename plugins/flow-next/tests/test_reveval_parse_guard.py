"""fn-90 R8: the fn-54 eval-harness parse+convergence guard runs in the gate.

`optimization/review-prompt/reveval_parse_guard.py` is an OFFLINE regression for
the two deterministic root causes of the Cursor review-backend loop runaway
(poisoned-stream verdict parse + fresh-review churn). It is runnable standalone,
and this wrapper wires it into the flow-next unittest suite so the runaway class
is caught on every gate run — not only when someone remembers to run the harness.
"""
import importlib.util
import subprocess
import unittest

import sys
from pathlib import Path

# fn-139.1: the tracker package sits beside flowctl.py; under a test module
# sys.path[0] is THIS directory, not scripts/, so it would not import.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

REPO = Path(__file__).resolve().parents[3]
_GUARD_PATH = REPO / "optimization" / "review-prompt" / "reveval_parse_guard.py"


def _load_guard():
    spec = importlib.util.spec_from_file_location("reveval_parse_guard", str(_GUARD_PATH))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestRevevalParseGuard(unittest.TestCase):
    def test_guard_module_present(self):
        self.assertTrue(
            _GUARD_PATH.is_file(),
            f"fn-90 eval-harness guard missing: {_GUARD_PATH}",
        )

    def test_guard_all_pass(self):
        """The offline poisoned-stream + convergence guard must pass end-to-end."""
        guard = _load_guard()
        self.assertTrue(
            guard.run_guard(),
            "fn-90 parse+convergence guard reported a FAILURE — the runaway "
            "regression class is not held. Run "
            "`python3 optimization/review-prompt/reveval_parse_guard.py`.",
        )

    def test_guard_standalone_subprocess_passes(self):
        """The resolved guard path remains executable outside this test process."""
        result = subprocess.run(
            [sys.executable, str(_GUARD_PATH)],
            cwd=REPO,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()
