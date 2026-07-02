"""Unit tests for `flowctl plan-sync-probe` (fn-83.1, R1/R6).

The probe is a pure deterministic drift-possibility check with a FAIL-OPEN
lattice: `skip` only when NO drift is provably possible, else `spawn`.
These tests drive the PRODUCTION `cmd_plan_sync_probe` function (argparse
Namespace + captured JSON stdout — memory: test-production-path), plus one
end-to-end subprocess test using the exact CLI wire form the fn-83.4 caller
uses (two-token `--deviation no --record on`).

Covers:
  - every lattice arm BOTH directions (each single condition flips skip→spawn)
  - multi-commit fix-loop tasks (range diff catches non-head-commit changes)
  - missing/short-circuit evidence fail-open (no base_commit, empty commits,
    non-hash values, unresolvable range)
  - rename D+A both-paths (--no-renames), Windows-path ref normalization,
    root-commit base, base==head empty diff
  - crossSpec arms (off ignores, on scans open specs' bodies + todo tasks,
    enumeration failure ⇒ spawn)
  - morphological identifier predicate table, hunk tokenizer, path-ref
    extraction, PurePosixPath overlap matcher
  - gate ledger: fixed schema, skip_index counting, deterministic audit ramp,
    record-actual pairing + audit_miss, garbage-line tolerance

Fixtures per test_prospect_cli.py conventions: importlib load of flowctl.py,
TemporaryDirectory + real `git init`.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Optional


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_plan_sync_probe_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()


DISJOINT_BODY = (
    "Build the widget.\n\n**Files:** `src/other/widget.py`\n\n"
    "## Investigation targets\n\n- `src/other/helpers.py:10-20`\n"
)


class ProbeRepoTestCase(unittest.TestCase):
    """Shared tmp-repo fixture: real git repo + hand-built .flow files."""

    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp()).resolve()
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        self._git("init", "-q")
        self._git("config", "user.email", "t@example.com")
        self._git("config", "user.name", "t")
        (self.tmpdir / ".flow" / "tasks").mkdir(parents=True)
        (self.tmpdir / ".flow" / "specs").mkdir(parents=True)
        # Root commit — also the range base in most scenarios (root-commit
        # base is an explicit spec edge case).
        self.base = self._commit(
            "src/mod/alpha.py", "def alpha_handler():\n    pass\n", "seed"
        )

    def tearDown(self) -> None:
        os.chdir(self.prev_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # ---- git helpers -------------------------------------------------

    def _git(self, *args: str) -> str:
        result = subprocess.run(
            ["git"] + list(args),
            cwd=str(self.tmpdir),
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def _commit(self, rel: str, content: str, msg: str) -> str:
        path = self.tmpdir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-qm", msg)
        return self._git("rev-parse", "HEAD")

    # ---- .flow fixture helpers ---------------------------------------

    def _mk_spec(self, spec_id: str, status: str = "open", body: Optional[str] = None) -> None:
        specs = self.tmpdir / ".flow" / "specs"
        (specs / f"{spec_id}.json").write_text(
            json.dumps({"id": spec_id, "title": spec_id, "status": status}),
            encoding="utf-8",
        )
        if body is not None:
            (specs / f"{spec_id}.md").write_text(body, encoding="utf-8")

    def _mk_task(
        self, task_id: str, spec_id: str, body: str, status: Optional[str] = None
    ) -> None:
        tasks = self.tmpdir / ".flow" / "tasks"
        (tasks / f"{task_id}.json").write_text(
            json.dumps({"id": task_id, "spec": spec_id, "title": task_id}),
            encoding="utf-8",
        )
        (tasks / f"{task_id}.md").write_text(body, encoding="utf-8")
        if status is not None:
            flowctl.save_task_runtime(task_id, {"status": status})

    def _finish_task(
        self,
        head: str,
        base: Optional[str] = None,
        downstream_body: str = DISJOINT_BODY,
        commits: Optional[list] = None,
        evidence: Optional[dict] = None,
    ) -> None:
        """fn-7.1 done with evidence; fn-7.2 todo with `downstream_body`."""
        self._mk_spec("fn-7")
        self._mk_task("fn-7.1", "fn-7", "impl task body")
        if evidence is None:
            evidence = {
                "commits": commits if commits is not None else [head],
                "tests": [],
                "prs": [],
                "base_commit": base if base is not None else self.base,
            }
        flowctl.save_task_runtime("fn-7.1", {"status": "done", "evidence": evidence})
        self._mk_task("fn-7.2", "fn-7", downstream_body)

    # ---- production-path drivers -------------------------------------

    def _probe(
        self,
        task_id: str = "fn-7.1",
        deviation: str = "no",
        record: Optional[str] = None,
    ) -> dict:
        ns = argparse.Namespace(
            target=task_id,
            record_target=None,
            deviation=deviation,
            record=record,
            actual=None,
            json=True,
        )
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            flowctl.cmd_plan_sync_probe(ns)
        return json.loads(buf.getvalue())

    def _record_actual(self, task_id: str, actual: str) -> dict:
        ns = argparse.Namespace(
            target="record-actual",
            record_target=task_id,
            deviation="missing",
            record=None,
            actual=actual,
            json=True,
        )
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            flowctl.cmd_plan_sync_probe(ns)
        return json.loads(buf.getvalue())

    def _work_commit(self) -> str:
        """One work commit renaming alpha_handler → alpha_handler_v2."""
        return self._commit(
            "src/mod/alpha.py", "def alpha_handler_v2():\n    pass\n", "work"
        )

    def _ledger_lines(self) -> list:
        path = self.tmpdir / ".flow" / "plansync-gate.jsonl"
        if not path.exists():
            return []
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]


# ── Lattice arms — both directions ───────────────────────────────────────


class LatticeArmsTest(ProbeRepoTestCase):
    def test_all_clear_skips(self) -> None:
        # Baseline: disjoint downstream, deviation=no, complete evidence.
        # Base is the ROOT commit (explicit spec edge: root-commit base).
        head = self._work_commit()
        self._finish_task(head)
        out = self._probe()
        self.assertEqual(out["decision"], "skip")
        self.assertEqual(out["facts"]["touched"], ["src/mod/alpha.py"])
        self.assertEqual(out["facts"]["overlaps"], [])
        self.assertEqual(out["facts"]["tokens_matched"], [])

    def test_output_contract_shape(self) -> None:
        head = self._work_commit()
        self._finish_task(head)
        out = self._probe()
        self.assertIn("decision", out)
        self.assertIn("mode", out)
        self.assertEqual(
            set(out["facts"].keys()),
            {
                "touched",
                "overlaps",
                "tokens_matched",
                "deviation",
                "unparseable_downstream",
                "cross_spec",
            },
        )

    def test_path_overlap_exact_spawns(self) -> None:
        head = self._work_commit()
        self._finish_task(
            head, downstream_body="Extend it.\n\n**Files:** `src/mod/alpha.py`\n"
        )
        out = self._probe()
        self.assertEqual(out["decision"], "spawn")
        self.assertTrue(out["facts"]["overlaps"])
        self.assertEqual(out["facts"]["overlaps"][0]["touched"], "src/mod/alpha.py")

    def test_path_overlap_basename_spawns(self) -> None:
        head = self._work_commit()
        self._finish_task(
            head, downstream_body="See `alpha.py` for the shape.\n"
        )
        out = self._probe()
        self.assertEqual(out["decision"], "spawn")

    def test_path_overlap_directory_prefix_spawns(self) -> None:
        head = self._work_commit()
        self._finish_task(
            head, downstream_body="Refactor everything under `src/mod/`.\n"
        )
        out = self._probe()
        self.assertEqual(out["decision"], "spawn")

    def test_token_overlap_spawns(self) -> None:
        # No path overlap; the OLD identifier (a `-` hunk line) appears in
        # the downstream body — the symbol-rename recall case.
        head = self._work_commit()
        self._finish_task(
            head,
            downstream_body=(
                "Call alpha_handler from the widget.\n\n"
                "**Files:** `src/other/widget.py`\n"
            ),
        )
        out = self._probe()
        self.assertEqual(out["decision"], "spawn")
        matched = {m["token"] for m in out["facts"]["tokens_matched"]}
        self.assertIn("alpha_handler", matched)

    def test_token_match_is_word_bounded(self) -> None:
        # `myalpha_handler2` must NOT match token `alpha_handler`.
        head = self._work_commit()
        self._finish_task(
            head,
            downstream_body=(
                "Uses myalpha_handler2 only.\n\n**Files:** `src/other/widget.py`\n"
            ),
        )
        out = self._probe()
        self.assertEqual(out["decision"], "skip")

    def test_deviation_yes_spawns(self) -> None:
        head = self._work_commit()
        self._finish_task(head)
        out = self._probe(deviation="yes")
        self.assertEqual(out["decision"], "spawn")
        self.assertEqual(out["facts"]["deviation"], "yes")

    def test_deviation_missing_spawns(self) -> None:
        head = self._work_commit()
        self._finish_task(head)
        out = self._probe(deviation="missing")
        self.assertEqual(out["decision"], "spawn")
        self.assertEqual(out["facts"]["deviation"], "yes")

    def test_missing_base_commit_spawns(self) -> None:
        head = self._work_commit()
        self._finish_task(
            head, evidence={"commits": [head], "tests": [], "prs": []}
        )
        out = self._probe()
        self.assertEqual(out["decision"], "spawn")
        self.assertIn("base_commit", out["reason"])

    def test_empty_evidence_spawns(self) -> None:
        head = self._work_commit()
        self._finish_task(head, evidence={})
        out = self._probe()
        self.assertEqual(out["decision"], "spawn")

    def test_empty_commits_spawns(self) -> None:
        self._work_commit()
        self._finish_task(
            "unused",
            evidence={"commits": [], "tests": [], "prs": [], "base_commit": self.base},
        )
        out = self._probe()
        self.assertEqual(out["decision"], "spawn")

    def test_non_hash_commit_spawns(self) -> None:
        # A flag-shaped value must never reach git argv.
        head = self._work_commit()
        self._finish_task(
            head,
            evidence={
                "commits": [head],
                "tests": [],
                "prs": [],
                "base_commit": "--output=/tmp/evil",
            },
        )
        out = self._probe()
        self.assertEqual(out["decision"], "spawn")
        self.assertIn("hash", out["reason"])

    def test_unresolvable_range_spawns(self) -> None:
        # Hash-shaped but missing object ⇒ git rc != 0 ⇒ fail-open.
        head = self._work_commit()
        self._finish_task(
            head,
            evidence={
                "commits": [head],
                "tests": [],
                "prs": [],
                "base_commit": "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
            },
        )
        out = self._probe()
        self.assertEqual(out["decision"], "spawn")
        self.assertIn("unresolvable", out["reason"])

    def test_unparseable_downstream_spawns(self) -> None:
        head = self._work_commit()
        self._finish_task(
            head, downstream_body="Pure prose only. Nothing path shaped here.\n"
        )
        out = self._probe()
        self.assertEqual(out["decision"], "spawn")
        self.assertEqual(out["facts"]["unparseable_downstream"], ["fn-7.2"])

    def test_missing_downstream_md_spawns(self) -> None:
        head = self._work_commit()
        self._finish_task(head)
        (self.tmpdir / ".flow" / "tasks" / "fn-7.2.md").unlink()
        out = self._probe()
        self.assertEqual(out["decision"], "spawn")
        self.assertIn("fn-7.2", out["facts"]["unparseable_downstream"])

    def test_base_equals_head_skips(self) -> None:
        # Worker made no commits: empty range diff, nothing changed ⇒ no
        # drift possible ⇒ skip (with deviation=no).
        self._finish_task(self.base, commits=[self.base])
        out = self._probe()
        self.assertEqual(out["decision"], "skip")
        self.assertEqual(out["facts"]["touched"], [])

    def test_no_downstream_tasks_skips(self) -> None:
        head = self._work_commit()
        self._mk_spec("fn-7")
        self._mk_task("fn-7.1", "fn-7", "impl body")
        flowctl.save_task_runtime(
            "fn-7.1",
            {
                "status": "done",
                "evidence": {
                    "commits": [head],
                    "tests": [],
                    "prs": [],
                    "base_commit": self.base,
                },
            },
        )
        out = self._probe()
        self.assertEqual(out["decision"], "skip")


# ── Range semantics: multi-commit, rename, Windows paths ─────────────────


class RangeSemanticsTest(ProbeRepoTestCase):
    def test_multi_commit_fix_loop_catches_early_commit(self) -> None:
        # Review-fix loop: c1 touches the drift-relevant file, c2+c3 touch an
        # unrelated file. head=c3 — a HEAD-only diff would miss c1's change;
        # the base..head RANGE diff must catch it.
        c1 = self._work_commit()
        c2 = self._commit("notes/a.txt", "a\n", "fix1")
        c3 = self._commit("notes/b.txt", "b\n", "fix2")
        self._finish_task(
            c3,
            commits=[c1, c2, c3],
            downstream_body="Extend it.\n\n**Files:** `src/mod/alpha.py`\n",
        )
        out = self._probe()
        self.assertEqual(out["decision"], "spawn")
        self.assertIn("src/mod/alpha.py", out["facts"]["touched"])

    def test_multi_commit_disjoint_skips(self) -> None:
        c1 = self._commit("notes/a.txt", "a\n", "c1")
        c2 = self._commit("notes/b.txt", "b\n", "c2")
        self._finish_task(c2, commits=[c1, c2])
        out = self._probe()
        self.assertEqual(out["decision"], "skip")

    def test_rename_d_plus_a_old_path_counts(self) -> None:
        # --no-renames renders a rename as D+A: the OLD path must be in the
        # touched-set so a downstream ref to it still spawns.
        self._git("mv", "src/mod/alpha.py", "src/mod/gamma.py")
        self._git("commit", "-qm", "rename")
        head = self._git("rev-parse", "HEAD")
        self._finish_task(
            head, downstream_body="Old ref: `src/mod/alpha.py` still cited.\n"
        )
        out = self._probe()
        self.assertEqual(out["decision"], "spawn")
        self.assertIn("src/mod/alpha.py", out["facts"]["touched"])
        self.assertIn("src/mod/gamma.py", out["facts"]["touched"])

    def test_rename_d_plus_a_new_path_counts(self) -> None:
        self._git("mv", "src/mod/alpha.py", "src/mod/gamma.py")
        self._git("commit", "-qm", "rename")
        head = self._git("rev-parse", "HEAD")
        self._finish_task(
            head, downstream_body="New ref: `src/mod/gamma.py` cited.\n"
        )
        out = self._probe()
        self.assertEqual(out["decision"], "spawn")

    def test_windows_path_ref_normalized(self) -> None:
        head = self._work_commit()
        self._finish_task(
            head, downstream_body="Update `src\\mod\\alpha.py` handler.\n"
        )
        out = self._probe()
        self.assertEqual(out["decision"], "spawn")


# ── Downstream scan scope ─────────────────────────────────────────────────


class ScanScopeTest(ProbeRepoTestCase):
    def test_done_and_in_progress_tasks_not_scanned(self) -> None:
        # Only todo tasks are downstream (matches phases.md 3e contract).
        head = self._work_commit()
        self._finish_task(head)
        self._mk_task(
            "fn-7.3", "fn-7", "**Files:** `src/mod/alpha.py`\n", status="done"
        )
        self._mk_task(
            "fn-7.4", "fn-7", "**Files:** `src/mod/alpha.py`\n", status="in_progress"
        )
        out = self._probe()
        self.assertEqual(out["decision"], "skip")

    def test_cross_spec_off_ignores_other_specs(self) -> None:
        head = self._work_commit()
        self._finish_task(head)
        self._mk_spec("fn-8", body="Touches `src/mod/alpha.py` heavily.\n")
        out = self._probe()
        self.assertEqual(out["decision"], "skip")
        self.assertFalse(out["facts"]["cross_spec"])

    def test_cross_spec_on_other_spec_body_overlap_spawns(self) -> None:
        head = self._work_commit()
        self._finish_task(head)
        self._mk_spec("fn-8", body="Touches `src/mod/alpha.py` heavily.\n")
        flowctl.set_config("planSync.crossSpec", True)
        out = self._probe()
        self.assertEqual(out["decision"], "spawn")
        self.assertTrue(out["facts"]["cross_spec"])

    def test_cross_spec_on_other_spec_todo_task_scanned(self) -> None:
        head = self._work_commit()
        self._finish_task(head)
        self._mk_spec("fn-8", body="Own plan: `docs/readme.md`.\n")
        self._mk_task("fn-8.1", "fn-8", "**Files:** `src/mod/alpha.py`\n")
        flowctl.set_config("planSync.crossSpec", True)
        out = self._probe()
        self.assertEqual(out["decision"], "spawn")

    def test_cross_spec_on_all_disjoint_skips(self) -> None:
        head = self._work_commit()
        self._finish_task(head)
        self._mk_spec("fn-8", body="Own plan: `docs/readme.md`.\n")
        self._mk_task("fn-8.1", "fn-8", "**Files:** `docs/other.md`\n")
        flowctl.set_config("planSync.crossSpec", True)
        out = self._probe()
        self.assertEqual(out["decision"], "skip")

    def test_cross_spec_missing_spec_md_spawns(self) -> None:
        # Spec JSON without a readable body ⇒ cannot prove disjoint.
        head = self._work_commit()
        self._finish_task(head)
        self._mk_spec("fn-8", body=None)
        flowctl.set_config("planSync.crossSpec", True)
        out = self._probe()
        self.assertEqual(out["decision"], "spawn")
        self.assertIn("fn-8", out["facts"]["unparseable_downstream"])

    def test_cross_spec_done_spec_ignored(self) -> None:
        head = self._work_commit()
        self._finish_task(head)
        self._mk_spec("fn-9", status="done", body="Touches `src/mod/alpha.py`.\n")
        flowctl.set_config("planSync.crossSpec", True)
        out = self._probe()
        self.assertEqual(out["decision"], "skip")


# ── Morphological predicate / tokenizer / extraction units ───────────────


class MorphologicalPredicateTest(unittest.TestCase):
    def test_predicate_table(self) -> None:
        kept = [
            "snake_case",
            "SCREAMING_SNAKE",
            "camelCase",
            "getUserName",
            "os.path",
            "Foo::bar",
            "ptr->field",
            "HEAD",
            "PR",
            "utf8",
            "sha256",
            "fn83",
            # literal compound arm — kept by shape even though it's prose
            # (over-keeping only produces spawns; no English stoplist).
            "e.g",
        ]
        rejected = [
            "parse",
            "read",
            "word",
            "a",
            "Hello",  # capitalized plain word — no hump, not all-caps
            "2026",  # pure number — no letter, not an identifier
            "2.6.0",  # dotted version — no letter
            "",
        ]
        for tok in kept:
            self.assertTrue(
                flowctl._psp_is_identifier_shaped(tok), f"should keep: {tok!r}"
            )
        for tok in rejected:
            self.assertFalse(
                flowctl._psp_is_identifier_shaped(tok), f"should reject: {tok!r}"
            )

    def test_hunk_tokenizer_scopes_to_hunk_lines(self) -> None:
        diff = (
            "diff --git a/x.py b/x.py\n"
            "index 000..111 100644\n"
            "--- a/header_token_old\n"
            "+++ b/header_token_new\n"
            "@@ -1,2 +1,2 @@\n"
            " context_token_here\n"
            "-def old_name(): pass\n"
            "+def new_name(): pass\n"
        )
        tokens = flowctl._psp_hunk_tokens(diff)
        self.assertIn("old_name", tokens)
        self.assertIn("new_name", tokens)
        self.assertNotIn("context_token_here", tokens)
        self.assertNotIn("header_token_old", tokens)
        self.assertNotIn("header_token_new", tokens)
        # plain words on hunk lines fail the predicate
        self.assertNotIn("def", tokens)
        self.assertNotIn("pass", tokens)


class PathRefExtractionTest(unittest.TestCase):
    def test_files_line_with_backticks_and_annotations(self) -> None:
        body = "**Files:** `a/b/c.py`, `tests/test_c.py` (new)\n"
        refs = flowctl._psp_extract_path_refs(body)
        self.assertIn("a/b/c.py", refs)
        self.assertIn("tests/test_c.py", refs)

    def test_investigation_targets_line_suffix_tolerant(self) -> None:
        body = (
            "## Investigation targets\n\n"
            "- `plugins/flow-next/scripts/flowctl.py:1181-1340` (config)\n"
        )
        refs = flowctl._psp_extract_path_refs(body)
        self.assertIn("plugins/flow-next/scripts/flowctl.py", refs)

    def test_prose_path_and_lone_filename(self) -> None:
        refs = flowctl._psp_extract_path_refs(
            "See src/deep/thing.rs and also worker.md for details.\n"
        )
        self.assertIn("src/deep/thing.rs", refs)
        self.assertIn("worker.md", refs)

    def test_trailing_slash_directory(self) -> None:
        refs = flowctl._psp_extract_path_refs("Everything under `src/mod/`.\n")
        self.assertIn("src/mod", refs)

    def test_windows_separators_normalized(self) -> None:
        refs = flowctl._psp_extract_path_refs("Edit src\\mod\\alpha.py now.\n")
        self.assertIn("src/mod/alpha.py", refs)

    def test_prose_artifacts_not_refs(self) -> None:
        refs = flowctl._psp_extract_path_refs(
            "This is e.g. fine, version 2.6.0, task fn-83.1, i.e. prose.\n"
        )
        self.assertEqual(refs, set())

    def test_pure_prose_yields_no_refs(self) -> None:
        self.assertEqual(
            flowctl._psp_extract_path_refs("Nothing here but words.\n"), set()
        )


class PathOverlapTest(unittest.TestCase):
    def test_exact(self) -> None:
        self.assertTrue(flowctl._psp_paths_overlap("a/b/c.py", "a/b/c.py"))

    def test_basename(self) -> None:
        self.assertTrue(flowctl._psp_paths_overlap("a/b/c.py", "c.py"))
        self.assertTrue(flowctl._psp_paths_overlap("a/b/c.py", "x/y/c.py"))

    def test_directory_prefix(self) -> None:
        self.assertTrue(flowctl._psp_paths_overlap("a/b/c.py", "a/b"))
        self.assertTrue(flowctl._psp_paths_overlap("a/b/c.py", "a"))

    def test_no_overlap(self) -> None:
        self.assertFalse(flowctl._psp_paths_overlap("a/b/c.py", "x/y/z.py"))
        # ref DEEPER than touched is not a directory-prefix of it
        self.assertFalse(flowctl._psp_paths_overlap("a/b", "a/b/c.py"))
        # shared leading segment only counts as full-parts prefix
        self.assertFalse(flowctl._psp_paths_overlap("abc/d.py", "ab"))


# ── Gate ledger ───────────────────────────────────────────────────────────


class LedgerTest(ProbeRepoTestCase):
    def test_record_appends_fixed_schema(self) -> None:
        head = self._work_commit()
        self._finish_task(head)
        out = self._probe(record="shadow")
        self.assertEqual(out["decision"], "skip")
        entries = self._ledger_lines()
        self.assertEqual(len(entries), 1)
        self.assertEqual(
            set(entries[0].keys()),
            {
                "ts",
                "spec",
                "task",
                "mode",
                "decision",
                "skip_index",
                "audit_spawned",
                "actual_drift",
                "audit_miss",
                "reason",
            },
        )
        self.assertEqual(entries[0]["spec"], "fn-7")
        self.assertEqual(entries[0]["task"], "fn-7.1")
        self.assertEqual(entries[0]["mode"], "shadow")
        self.assertEqual(entries[0]["skip_index"], 1)
        self.assertIsNone(entries[0]["actual_drift"])
        self.assertFalse(entries[0]["audit_miss"])

    def test_skip_index_increments_and_spawn_has_none(self) -> None:
        head = self._work_commit()
        self._finish_task(head)
        self._probe(record="shadow")
        self._probe(record="shadow")
        out = self._probe(deviation="yes", record="shadow")  # spawn
        self.assertEqual(out["decision"], "spawn")
        entries = self._ledger_lines()
        self.assertEqual([e["skip_index"] for e in entries], [1, 2, None])
        self.assertFalse(entries[2]["audit_spawned"])
        third = self._probe(record="shadow")  # skip again → index 3
        self.assertEqual(third["record"]["skip_index"], 3)

    def test_audit_ramp_deterministic(self) -> None:
        # 1-in-2 for the first 20 skips, 1-in-5 thereafter (counter, no RNG).
        for i in range(1, 21):
            self.assertEqual(flowctl._psp_audit_due(i), i % 2 == 0, f"index {i}")
        for i in (21, 22, 23, 24, 26, 27, 28, 29, 31):
            self.assertFalse(flowctl._psp_audit_due(i), f"index {i}")
        for i in (25, 30, 35, 100):
            self.assertTrue(flowctl._psp_audit_due(i), f"index {i}")

    def test_on_mode_marks_audit_slots(self) -> None:
        head = self._work_commit()
        self._finish_task(head)
        first = self._probe(record="on")
        second = self._probe(record="on")
        self.assertFalse(first["record"]["audit_spawned"])  # skip_index 1
        self.assertTrue(second["record"]["audit_spawned"])  # skip_index 2

    def test_shadow_mode_never_audits(self) -> None:
        head = self._work_commit()
        self._finish_task(head)
        self._probe(record="shadow")
        second = self._probe(record="shadow")
        self.assertEqual(second["record"]["skip_index"], 2)
        self.assertFalse(second["record"]["audit_spawned"])

    def test_record_actual_pairs_and_computes_audit_miss(self) -> None:
        head = self._work_commit()
        self._finish_task(head)
        self._probe(record="on")
        out = self._record_actual("fn-7.1", "yes")
        self.assertTrue(out["audit_miss"])  # skip + actual drift yes = miss
        entries = self._ledger_lines()
        self.assertEqual(entries[0]["actual_drift"], "yes")
        self.assertTrue(entries[0]["audit_miss"])

    def test_record_actual_no_drift_not_a_miss(self) -> None:
        head = self._work_commit()
        self._finish_task(head)
        self._probe(record="on")
        out = self._record_actual("fn-7.1", "no")
        self.assertFalse(out["audit_miss"])

    def test_record_actual_on_spawn_not_a_miss(self) -> None:
        head = self._work_commit()
        self._finish_task(head)
        self._probe(deviation="yes", record="shadow")  # spawn record
        out = self._record_actual("fn-7.1", "yes")
        self.assertFalse(out["audit_miss"])  # decision was spawn — no miss

    def test_record_actual_without_pending_entry_errors(self) -> None:
        head = self._work_commit()
        self._finish_task(head)
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stdout(io.StringIO()):
                self._record_actual("fn-7.1", "yes")

    def test_ledger_tolerates_garbage_lines(self) -> None:
        head = self._work_commit()
        self._finish_task(head)
        self._probe(record="shadow")
        ledger = self.tmpdir / ".flow" / "plansync-gate.jsonl"
        with open(ledger, "a", encoding="utf-8") as f:
            f.write("not json at all\n")
        out = self._probe(record="shadow")
        self.assertEqual(out["record"]["skip_index"], 2)


# ── CLI wire form + error exits ───────────────────────────────────────────


class WireFormTest(ProbeRepoTestCase):
    def test_exact_caller_wire_form_end_to_end(self) -> None:
        # The EXACT two-token invocation the fn-83.4 caller uses.
        head = self._work_commit()
        self._finish_task(head)
        result = subprocess.run(
            [
                sys.executable,
                str(FLOWCTL_PY),
                "plan-sync-probe",
                "fn-7.1",
                "--json",
                "--deviation",
                "no",
                "--record",
                "on",
            ],
            cwd=str(self.tmpdir),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        out = json.loads(result.stdout)
        self.assertEqual(out["decision"], "skip")
        self.assertEqual(out["mode"], "on")
        result2 = subprocess.run(
            [
                sys.executable,
                str(FLOWCTL_PY),
                "plan-sync-probe",
                "record-actual",
                "fn-7.1",
                "--actual",
                "no",
                "--json",
            ],
            cwd=str(self.tmpdir),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result2.returncode, 0, result2.stderr)
        out2 = json.loads(result2.stdout)
        self.assertEqual(out2["actual_drift"], "no")
        self.assertFalse(out2["audit_miss"])

    def test_invalid_task_id_exits_nonzero(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stdout(io.StringIO()):
                self._probe(task_id="not-a-task")
        self.assertNotEqual(ctx.exception.code, 0)

    def test_missing_task_exits_nonzero(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stdout(io.StringIO()):
                self._probe(task_id="fn-99.1")
        self.assertNotEqual(ctx.exception.code, 0)

    def test_mode_reflects_config_gate(self) -> None:
        head = self._work_commit()
        self._finish_task(head)
        self.assertEqual(self._probe()["mode"], "on")  # default
        flowctl.set_config("planSync.gate", "shadow")
        self.assertEqual(self._probe()["mode"], "shadow")


if __name__ == "__main__":
    unittest.main()
