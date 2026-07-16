"""Windows-only real-subprocess smoke for the Copilot stdin path (1.1.9).

Validates that on the actual Windows kernel, ``subprocess.run`` with
``input=prompt`` delivers a 60 KB prompt to a child process without
hitting the ``CreateProcessW`` 32,767-char argv cap. This is the real
failure mode reported by Simon Flauger (SEMA-CAD) in 1.1.8.

Strategy: stand up a tiny fake ``copilot.bat`` shim that reads stdin and
echoes a stable summary, prepend the shim directory to ``PATH``, then
call ``run_copilot_exec`` for real. The shim is what
``shutil.which("copilot")`` returns inside ``require_copilot``.

Skipped on non-Windows hosts — this fault mode is Windows-specific and
the mocked unit tests in ``test_copilot_run_exec.py`` cover behavioral
expectations on every platform.
"""

import hashlib
import os
import shutil
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "plugins" / "flow-next" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import flowctl  # noqa: E402

_FAKE_COPILOT_PY = '''\
import hashlib
import sys

data = sys.stdin.read()
digest = hashlib.sha256(data.encode("utf-8")).hexdigest()
sys.stdout.write(f"FAKE_COPILOT_OK chars={len(data)} sha256={digest}\\n")
sys.stdout.write("<verdict>SHIP</verdict>\\n")
sys.exit(0)
'''


@unittest.skipUnless(
    sys.platform == "win32",
    "Windows-only smoke (CreateProcessW argv cap is Windows-specific; "
    "mocked unit tests cover behavior on other platforms).",
)
class CopilotWindowsRealSubprocessSmoke(unittest.TestCase):
    """Spawn a real subprocess via Windows CreateProcessW + stdin pipe.

    The 1.1.8 failure was specifically: spec-sized prompt + Windows +
    Copilot CLI's argv-only ``-p`` blew the 32,767-char ``lpCommandLine``
    cap. The 1.1.9 stdin path should make this impossible because the
    prompt never enters argv — it goes through the stdin pipe Python
    opens to the child.
    """

    @classmethod
    def setUpClass(cls):
        cls.shim_dir = Path(tempfile.mkdtemp(prefix="flowctl-copilot-shim-"))
        # Real Python fake — reads stdin, prints summary, returns 0.
        fake_py = cls.shim_dir / "_fake_copilot.py"
        fake_py.write_text(_FAKE_COPILOT_PY, encoding="utf-8")
        # Windows shim: copilot.bat dispatches to the Python fake. CRLF
        # line endings keep cmd.exe happy regardless of git autocrlf.
        shim = cls.shim_dir / "copilot.bat"
        shim.write_text(
            "@echo off\r\n"
            f'python "{fake_py}" %*\r\n',
            encoding="utf-8",
        )
        cls.shim_path = shim
        # Prepend shim dir to PATH so shutil.which("copilot") hits our fake.
        cls._old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = (
            str(cls.shim_dir) + os.pathsep + cls._old_path
        )
        # Sanity: shutil.which should resolve our shim.
        resolved = shutil.which("copilot")
        assert resolved is not None and resolved.lower().startswith(
            str(cls.shim_dir).lower()
        ), (
            f"shim not on PATH: which={resolved!r}, "
            f"expected dir prefix={cls.shim_dir!s}"
        )

    @classmethod
    def tearDownClass(cls):
        os.environ["PATH"] = cls._old_path
        shutil.rmtree(cls.shim_dir, ignore_errors=True)

    def test_60kb_prompt_delivered_via_stdin(self):
        # 60 KB is roughly 2× the Windows argv cap. The -p path would
        # definitely fail; the stdin path should sail through.
        prompt = ("0123456789ABCDEF" * 4096)[:60_000]
        self.assertEqual(len(prompt), 60_000)
        expected_sha = hashlib.sha256(
            prompt.encode("utf-8")
        ).hexdigest()

        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            stdout, _sid, rc, stderr = flowctl.run_copilot_exec(
                prompt=prompt,
                session_id=str(uuid.uuid4()),
                repo_root=repo_root,
                spec=flowctl.BackendSpec("copilot").resolve(),
            )

        self.assertEqual(
            rc, 0,
            f"copilot exit {rc}; stdout={stdout!r} stderr={stderr!r}",
        )
        # Fake reports the exact byte count + SHA256 it received via stdin.
        self.assertIn("FAKE_COPILOT_OK", stdout)
        self.assertIn(f"chars={len(prompt)}", stdout)
        self.assertIn(f"sha256={expected_sha}", stdout)
        # Verdict marker passes through cleanly (verdict-parsing seam stays
        # intact for callers downstream of run_copilot_exec).
        self.assertIn("<verdict>SHIP</verdict>", stdout)

    def test_marker_created_after_successful_first_call(self):
        # Verify the create-vs-resume marker discipline on real Windows
        # subprocess. First call → --session-id; marker written. Second
        # call same session_id → --resume.
        session_id = str(uuid.uuid4())
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            marker = flowctl._copilot_session_marker(repo_root, session_id)
            self.assertFalse(marker.exists())

            _, _, rc1, _ = flowctl.run_copilot_exec(
                prompt="first call",
                session_id=session_id,
                repo_root=repo_root,
            )
            self.assertEqual(rc1, 0)
            self.assertTrue(marker.exists(),
                            "Windows path must touch marker after success")

            # Second call: marker present → resume path is taken. Fake
            # ignores the session args, so we just verify rc and that the
            # marker is still there (idempotent touch).
            _, _, rc2, _ = flowctl.run_copilot_exec(
                prompt="second call",
                session_id=session_id,
                repo_root=repo_root,
            )
            self.assertEqual(rc2, 0)
            self.assertTrue(marker.exists())


if __name__ == "__main__":
    unittest.main()
