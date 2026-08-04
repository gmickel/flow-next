#!/usr/bin/env python3
"""First tests for scripts/run_tests_parallel.py (fn-155).

Three groups:

1. `_default_jobs()` value semantics - the CI/local split and every `CI` value
   case the design names (absent / empty / "false" / "TRUE" / "0").
2. Precedence at `main()`, NOT at the parser. The chain lives after parsing, so
   a parser-level test cannot prove `--serial` > `--jobs` > default, nor that
   `--jobs 0` exits 2 without running the suite. `run_suite` and
   `_default_jobs` are patched so the assertions are about the selection.
3. Contracts a job-count change could plausibly disturb: coverage parity
   between two job counts on the same corpus (sorted `--list-only` output, the
   `parallel-runner:` line and the `SUMMARY` counts), `--exclude` behavior and
   its `EXCLUDED` line, zero-match exit 2, and a failing file exit 1.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNNER_PY = REPO_ROOT / "scripts" / "run_tests_parallel.py"

# The module under test lives in repo-root scripts/, which is not on sys.path
# when this file runs (sys.path[0] is the tests dir). Insert it so the runner's
# own directory is importable, and so this module satisfies the repo-wide
# sys.path guard in test_tracker_package_import.py.
sys.path.insert(0, str(REPO_ROOT / "scripts"))

_RUNNER_MOD = None


def _load_runner():
    """Load the runner by path (same pattern the flowctl test modules use)."""
    global _RUNNER_MOD
    if _RUNNER_MOD is None:
        spec = importlib.util.spec_from_file_location(
            "run_tests_parallel_under_test", RUNNER_PY
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        _RUNNER_MOD = mod
    return _RUNNER_MOD


PASSING_FILE = """\
import unittest


class Passing(unittest.TestCase):
    def test_one(self):
        self.assertTrue(True)

    def test_two(self):
        self.assertEqual(2, 1 + 1)
"""

FAILING_FILE = """\
import unittest


class Failing(unittest.TestCase):
    def test_boom(self):
        self.assertEqual(1, 2)
"""

# fn-120.2: a failing child that emits non-ASCII diagnostics as raw UTF-8
# BYTES. The runner used to decode captured child output with the PARENT's
# locale encoding (cp1252 on windows-latest), which mojibaked the diagnostic.
# Bytes are written directly because the child's own text encoder is a separate
# variable — on Windows unittest's stream is cp1252 and mangles the message
# before it ever reaches the pipe (verified: run 30913423957). What this
# fixture measures is the parent's decode. Escapes keep this harness ASCII.
NON_ASCII_FAILING_FILE = """\
import sys
import unittest


class NonAsciiFailure(unittest.TestCase):
    def test_utf8_message(self):
        sys.stdout.buffer.write("w\\u00f6rks \\u2014 \\u2713\\n".encode("utf-8"))
        sys.stdout.buffer.flush()
        self.fail("non-ascii marker emitted on stdout above")
"""
NON_ASCII_NEEDLE = "w\u00f6rks \u2014 \u2713"


class DefaultJobsTest(unittest.TestCase):
    """R1/R5: the CI vs local split and the `CI` value semantics."""

    def setUp(self):
        self.mod = _load_runner()

    def _jobs(self, ci_value, cpus=8, cursor_agent=None):
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("CI", "CURSOR_AGENT")
        }
        if ci_value is not None:
            env["CI"] = ci_value
        if cursor_agent is not None:
            env["CURSOR_AGENT"] = cursor_agent
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
            self.mod.os, "cpu_count", return_value=cpus
        ):
            return self.mod._default_jobs()

    def test_local_default_reserves_two_cores(self):
        self.assertEqual(self._jobs(None), 6)

    def test_ci_truthy_values_use_full_cpu_count(self):
        for value in ("1", "true", "yes", "TRUE", "  True  ", "Yes"):
            with self.subTest(value=value):
                self.assertEqual(self._jobs(value), 8)

    def test_ci_falsey_and_unrecognized_values_are_local(self):
        for value in ("", "  ", "false", "FALSE", "0", "no", "off", "maybe"):
            with self.subTest(value=value):
                self.assertEqual(self._jobs(value), 6)

    def test_absent_ci_is_local(self):
        self.assertEqual(self._jobs(None), 6)

    def test_cursor_agent_shell_keeps_local_headroom_despite_ci(self):
        """Cursor's agent shell sets CI=1 on a developer machine.

        Documented in plugins/flow-next/skills/flow-next-setup/workflow.md.
        That is exactly the case the reservation protects - the editor and the
        agent driving the session compete for the same cores - so CURSOR_AGENT
        must force the local branch even though CI parses truthy.
        """
        for ci_value in ("1", "true", "yes", "TRUE"):
            with self.subTest(ci=ci_value):
                self.assertEqual(
                    self._jobs(ci_value, cursor_agent="1"), 6
                )

    def test_cursor_agent_empty_or_absent_does_not_suppress_ci(self):
        """Only a non-empty CURSOR_AGENT forces local; hosted CI never sets it."""
        self.assertEqual(self._jobs("true", cursor_agent=None), 8)
        self.assertEqual(self._jobs("true", cursor_agent=""), 8)
        self.assertEqual(self._jobs("true", cursor_agent="   "), 8)

    def test_cursor_agent_alone_is_still_local(self):
        self.assertEqual(self._jobs(None, cursor_agent="1"), 6)

    def test_low_core_machines_never_go_below_one(self):
        self.assertEqual(self._jobs(None, cpus=1), 1)
        self.assertEqual(self._jobs(None, cpus=2), 1)
        self.assertEqual(self._jobs("true", cpus=1), 1)

    def test_unknown_cpu_count_falls_back_to_two(self):
        env = {k: v for k, v in os.environ.items() if k != "CI"}
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
            self.mod.os, "cpu_count", return_value=None
        ):
            self.assertEqual(self.mod._default_jobs(), 1)
        env["CI"] = "true"
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
            self.mod.os, "cpu_count", return_value=None
        ):
            self.assertEqual(self.mod._default_jobs(), 2)


class MainPrecedenceTest(unittest.TestCase):
    """R4/R5: --serial > --jobs > default, resolved inside main()."""

    def setUp(self):
        self.mod = _load_runner()

    @contextlib.contextmanager
    def _patched(self, default_jobs=7, run_rc=0):
        calls = {}

        def fake_run_suite(**kwargs):
            calls["kwargs"] = kwargs
            return run_rc

        default = mock.Mock(return_value=default_jobs)
        with mock.patch.object(self.mod, "run_suite", side_effect=fake_run_suite), \
                mock.patch.object(self.mod, "_default_jobs", default):
            yield calls, default

    def test_bare_invocation_uses_default_jobs(self):
        with self._patched() as (calls, default):
            rc = self.mod.main([])
        self.assertEqual(rc, 0)
        self.assertEqual(default.call_count, 1)
        self.assertEqual(calls["kwargs"]["jobs"], 7)

    def test_explicit_jobs_wins_over_default_and_never_calls_it(self):
        with self._patched() as (calls, default):
            rc = self.mod.main(["--jobs", "6"])
        self.assertEqual(rc, 0)
        self.assertEqual(default.call_count, 0)
        self.assertEqual(calls["kwargs"]["jobs"], 6)

    def test_serial_beats_explicit_jobs(self):
        with self._patched() as (calls, default):
            rc = self.mod.main(["--serial", "--jobs", "6"])
        self.assertEqual(rc, 0)
        self.assertEqual(default.call_count, 0)
        self.assertEqual(calls["kwargs"]["jobs"], 1)

    def test_jobs_below_one_exits_two_without_running(self):
        for value in ("0", "-1"):
            with self.subTest(value=value):
                with self._patched() as (calls, default):
                    buf = io.StringIO()
                    with contextlib.redirect_stderr(buf):
                        rc = self.mod.main(["--jobs", value])
                self.assertEqual(rc, 2)
                self.assertNotIn("kwargs", calls)
                self.assertEqual(default.call_count, 0)
                self.assertIn("--jobs must be >= 1", buf.getvalue())


class CorpusContractTest(unittest.TestCase):
    """R3: coverage parity across job counts, plus the exclude/exit contracts."""

    def setUp(self):
        self.mod = _load_runner()
        self._tmp = tempfile.TemporaryDirectory()
        self.corpus = Path(self._tmp.name)
        for name in ("test_alpha.py", "test_beta.py", "test_gamma.py"):
            (self.corpus / name).write_text(PASSING_FILE, encoding="utf-8")
        self.addCleanup(self._tmp.cleanup)

    def _run(self, extra_args, auto_jobs=None):
        """Run main() over the temp corpus.

        `auto_jobs` omits both overrides so the auto default path is the one
        under test, with `_default_jobs` pinned so the comparison is
        deterministic on any machine.
        """
        buf = io.StringIO()
        ctx = (
            mock.patch.object(self.mod, "_default_jobs", return_value=auto_jobs)
            if auto_jobs is not None
            else contextlib.nullcontext()
        )
        with ctx, contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = self.mod.main(["--tests-dir", str(self.corpus)] + extra_args)
        return rc, buf.getvalue()

    @staticmethod
    def _line_starting(text, prefix):
        for line in text.splitlines():
            if line.startswith(prefix):
                return line
        return None

    def test_list_only_file_set_identical_at_jobs_two_and_auto(self):
        rc_a, out_a = self._run(["--jobs", "2", "--list-only"])
        # No --jobs and no --serial: the auto default is the path under test.
        rc_b, out_b = self._run(["--list-only"], auto_jobs=3)
        self.assertEqual((rc_a, rc_b), (0, 0))
        self.assertIn("jobs=2", self._line_starting(out_a, "parallel-runner:"))
        self.assertIn("jobs=3", self._line_starting(out_b, "parallel-runner:"))
        names_a = sorted(ln for ln in out_a.splitlines() if ln.endswith(".py"))
        names_b = sorted(ln for ln in out_b.splitlines() if ln.endswith(".py"))
        self.assertEqual(names_a, ["test_alpha.py", "test_beta.py", "test_gamma.py"])
        self.assertEqual(names_a, names_b)
        # Counts alone are not proof, so the file list above is compared too.
        self.assertIn("3 file(s)", self._line_starting(out_a, "parallel-runner:"))
        self.assertIn("3 file(s)", self._line_starting(out_b, "parallel-runner:"))

    def test_summary_counts_identical_at_jobs_two_and_auto(self):
        rc_a, out_a = self._run(["--jobs", "2"])
        # Auto default (no overrides), pinned to a different job count so the
        # comparison is between two genuinely different schedules.
        rc_b, out_b = self._run([], auto_jobs=3)
        self.assertEqual((rc_a, rc_b), (0, 0))
        summary_a = self._line_starting(out_a, "SUMMARY")
        summary_b = self._line_starting(out_b, "SUMMARY")
        self.assertIsNotNone(summary_a)
        counts_a = summary_a.split("  wall=")[0]
        counts_b = summary_b.split("  wall=")[0]
        self.assertEqual(counts_a, counts_b)
        self.assertIn("files=3 ran=6 failures=0 errors=0 skipped=0", counts_a)
        # ... and the serial fallback agrees with both.
        rc_c, out_c = self._run(["--serial"])
        self.assertEqual(rc_c, 0)
        self.assertEqual(self._line_starting(out_c, "SUMMARY").split("  wall=")[0], counts_a)

    def test_exclude_drops_exactly_the_named_file_and_prints_it(self):
        rc, out = self._run(["--jobs", "2", "--exclude", "test_beta.py", "--list-only"])
        self.assertEqual(rc, 0)
        self.assertIn("EXCLUDED  test_beta.py  (--exclude)", out)
        names = sorted(ln for ln in out.splitlines() if ln.endswith(".py"))
        self.assertEqual(names, ["test_alpha.py", "test_gamma.py"])
        self.assertIn("2 file(s)", self._line_starting(out, "parallel-runner:"))

    def test_zero_match_pattern_exits_two(self):
        rc, out = self._run(["--pattern", "test_nothing_here*.py"])
        self.assertEqual(rc, 2)
        self.assertIn("zero test files matched", out)

    def test_failing_file_exits_one(self):
        (self.corpus / "test_delta.py").write_text(FAILING_FILE, encoding="utf-8")
        rc, out = self._run(["--jobs", "2"])
        self.assertEqual(rc, 1)
        self.assertEqual(self._line_starting(out, "FAILED FILES"), "FAILED FILES (1):")
        self.assertIn("- test_delta.py", out)

    def test_non_ascii_child_output_survives_capture(self):
        """fn-120.2: child output is decoded as UTF-8, not the parent locale.

        The child emits UTF-8 bytes; on windows-latest the parent's locale
        default is cp1252, so before the explicit `encoding=` those bytes came
        back mojibaked and the real failure text was unreadable in CI logs.
        """
        (self.corpus / "test_utf8.py").write_text(
            NON_ASCII_FAILING_FILE, encoding="utf-8"
        )
        rc, out = self._run(["--serial"])
        self.assertEqual(rc, 1)
        self.assertTrue(
            NON_ASCII_NEEDLE in out,
            "non-ASCII child failure text was not captured verbatim; "
            "needle={} out={}".format(
                NON_ASCII_NEEDLE.encode("unicode_escape").decode("ascii"),
                out.encode("unicode_escape").decode("ascii"),
            ),
        )

    def test_child_capture_pins_utf8_decoding(self):
        """The decode is pinned at the SPAWN, not inferred from the platform.

        The verbatim-capture test above cannot fail on a POSIX runner (PEP 538
        coerces even `LC_ALL=C` to a UTF-8 locale), so the kwargs the runner
        hands `subprocess.run` are asserted directly - that is the thing that
        was wrong on windows-latest.
        """
        real_run = self.mod.subprocess.run
        seen = {}

        def capture(cmd, **kwargs):
            seen.update(kwargs)
            return real_run(cmd, **kwargs)

        with mock.patch.object(self.mod.subprocess, "run", side_effect=capture):
            rc, _ = self._run(["--serial", "--pattern", "test_alpha.py"])
        self.assertEqual(rc, 0)
        self.assertEqual(seen.get("encoding"), "utf-8")
        self.assertEqual(seen.get("errors"), "replace")


if __name__ == "__main__":
    unittest.main()
