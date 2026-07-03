"""fn-83.4 — worker anchor-call prose, gate-removal guards, evidence provenance.

The plan-sync skip-gate was proven NON-VIABLE (fn-83.6 cross-repo verdict
FAIL — a genuine false skip + 6.7% skip-rate vs >=50% required; decision
record `.flow/memory/knowledge/decisions/plan-sync-skip-gate-not-viable-
2026-07-03.md`) and its machinery was removed from the shipped CLI. What
DOES ship from fn-83 — and what this test locks:

1. worker.md Phase 1 is the single ``flowctl anchor <TASK_ID> --md`` call
   with floor-not-ceiling prose (memory keyword-search + read-more freedom
   retained), and BASE_COMMIT is captured at Phase-1 end. Canonical file
   AND the Codex mirror (sync-codex.sh regenerates the mirror, but the
   contract must survive that rewrite pass — same discipline as
   test_pnpm_home_hint_prose.py).
2. phases.md 3e passes ``CROSS_SPEC`` to the plan-sync spawn (single
   config-leaf read of ``planSync.crossSpec`` — the documented
   plan-sync.md input the caller historically never passed). The spawn
   itself stays UNCONDITIONAL — no gate branch, no probe, no mode matrix.
3. Gate-removal grep guards (fn-83 R4):
   - user-surface: no `plan-sync-probe` / `planSync.gate` / `plansync-gate`
     anywhere in scripts/skills/agents (canonical) or the work-loop mirror;
   - symbol-level: no `cmd_plan_sync_probe` / `PLANSYNC_GATE_LEDGER` /
     `_psp_*` in flowctl.py EXCEPT the retained `_psp_run_git` (reused by
     `flowctl anchor`);
   - the dead gate signal `PLAN_DEVIATION` is fully deleted from agents +
     skills.
4. BASE_COMMIT + done-evidence provenance are RETAINED (load-bearing
   independent of the gate: impl-review diff scoping, delegation
   git-ownership, commit-range provenance): ``base_commit`` + the FULL
   base..HEAD commit list in the evidence templates, verified by a real
   `flowctl done` round-trip against a tmp-repo fixture (production CLI
   wire form).
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN = REPO_ROOT / "plugins" / "flow-next"
FLOWCTL_PY = PLUGIN / "scripts" / "flowctl.py"

CANONICAL_WORKER = PLUGIN / "agents" / "worker.md"
MIRROR_WORKER = PLUGIN / "codex" / "agents" / "worker.toml"
CANONICAL_PHASES = PLUGIN / "skills" / "flow-next-work" / "phases.md"
MIRROR_PHASES = PLUGIN / "codex" / "skills" / "flow-next-work" / "phases.md"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def _iter_text_files(root: pathlib.Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        try:
            yield path, path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue


class WorkerAnchorCallProse(unittest.TestCase):
    """Phase 1 = single anchor call, floor-not-ceiling; BASE_COMMIT at end."""

    def _assert_anchor_contract(self, path: pathlib.Path) -> None:
        text = _read(path)
        self.assertIn("anchor <TASK_ID> --md", text, path)
        # Floor, not a ceiling — read-more freedom retained.
        self.assertRegex(
            text, re.compile(r"FLOOR, not a ceiling", re.IGNORECASE), path
        )
        self.assertIn("memory search", text, path)
        self.assertIn("memory read", text, path)
        # Fail-open fallback: a broken section is run directly.
        self.assertIn("section unavailable", text, path)
        # BASE_COMMIT captured at Phase-1 end, before any edit.
        self.assertIn("BASE_COMMIT=$(git rev-parse HEAD)", text, path)
        self.assertIn("BEFORE any edit", text, path)
        # Persisted to a gitignored file — bash vars do not survive across
        # tool-call Bash blocks, so BASE_COMMIT must be written once and
        # re-read where used, else Phase-5 evidence records a blank base.
        self.assertIn("> .flow/tmp/base_commit", text, path)

    def _assert_evidence_contract(self, path: pathlib.Path) -> None:
        text = _read(path)
        # Full commit list, oldest first, from the Phase-1 base commit.
        self.assertIn('git rev-list --reverse "$BASE_COMMIT"..HEAD', text, path)
        # Each evidence block re-reads BASE_COMMIT from the persisted file
        # (self-contained — no cross-tool-call variable dependency).
        self.assertEqual(
            text.count("BASE_COMMIT=$(cat .flow/tmp/base_commit)") >= 2, True, path
        )
        # base_commit provenance in BOTH evidence templates (standard +
        # delegation) — retained per fn-83 R4 (only the removed probe's
        # CONSUMPTION of it is gone).
        self.assertEqual(
            text.count('"base_commit": "$BASE_COMMIT"'), 2, path
        )
        self.assertEqual(text.count('"commits": $COMMITS_JSON'), 2, path)

    def test_canonical_worker(self) -> None:
        self._assert_anchor_contract(CANONICAL_WORKER)
        self._assert_evidence_contract(CANONICAL_WORKER)

    def test_mirror_worker(self) -> None:
        self._assert_anchor_contract(MIRROR_WORKER)
        self._assert_evidence_contract(MIRROR_WORKER)


class PhasesCrossSpecProse(unittest.TestCase):
    """phases.md 3e: CROSS_SPEC passed; spawn stays unconditional."""

    def _assert_phases_contract(self, path: pathlib.Path) -> None:
        text = _read(path)
        # Single config-leaf read + spawn-prompt input.
        self.assertIn("planSync.crossSpec", text, path)
        self.assertIn("CROSS_SPEC=$(", text, path)  # reads the actual config value
        # The spawn template references the READ value, not the ambiguous
        # literal "true|false" (plan-sync Phase 4b only skips on exact false).
        self.assertIn("$CROSS_SPEC value read above", text, path)
        self.assertNotIn("CROSS_SPEC: true|false", text, path)
        # The spawn is gated ONLY on planSync.enabled — today's behavior.
        self.assertIn("planSync.enabled", text, path)

    def test_canonical_phases(self) -> None:
        self._assert_phases_contract(CANONICAL_PHASES)

    def test_mirror_phases(self) -> None:
        self._assert_phases_contract(MIRROR_PHASES)


class GateRemovalGuards(unittest.TestCase):
    """fn-83 R4 grep guards — the shipped plugin carries NO gate machinery."""

    # User-surface tokens that must not appear anywhere in the shipped
    # plugin's prose or code. `plan.sync.probe` covers `plan-sync-probe`
    # and `plan_sync_probe` spellings.
    USER_SURFACE_RE = re.compile(
        r"plan.sync.probe|planSync\.gate|plansync-gate", re.IGNORECASE
    )

    def _scan(self, roots) -> list:
        hits = []
        for root in roots:
            for path, text in _iter_text_files(root):
                if self.USER_SURFACE_RE.search(text):
                    hits.append(str(path))
        return hits

    def test_user_surface_guard_canonical(self) -> None:
        roots = [PLUGIN / "scripts", PLUGIN / "skills", PLUGIN / "agents"]
        self.assertEqual(self._scan(roots), [])

    def test_user_surface_guard_mirror_worker_files(self) -> None:
        for path in (MIRROR_WORKER, MIRROR_PHASES):
            with self.subTest(file=str(path)):
                self.assertIsNone(self.USER_SURFACE_RE.search(_read(path)))

    def test_symbol_guard_flowctl_psp_run_git_only(self) -> None:
        # `grep -n 'cmd_plan_sync_probe\|PLANSYNC_GATE_LEDGER\|_psp_'
        # flowctl.py` must return ONLY `_psp_run_git` mentions (the one
        # helper `flowctl anchor` reuses; its `_psp_` prefix is historical).
        text = _read(FLOWCTL_PY)
        self.assertNotIn("cmd_plan_sync_probe", text)
        self.assertNotIn("PLANSYNC_GATE_LEDGER", text)
        offenders = [
            m.group(0)
            for m in re.finditer(r"_psp_[A-Za-z_]*", text)
            if m.group(0) != "_psp_run_git"
        ]
        self.assertEqual(offenders, [])

    def test_plan_deviation_deleted(self) -> None:
        # The dead gate SIGNAL: its only consumer (the probe) is gone, so
        # the worker terminal line + host parser prose are deleted too.
        roots = [PLUGIN / "agents", PLUGIN / "skills"]
        hits = []
        for root in roots:
            for path, text in _iter_text_files(root):
                if "PLAN_DEVIATION" in text:
                    hits.append(str(path))
        self.assertEqual(hits, [])
        for path in (MIRROR_WORKER, MIRROR_PHASES):
            with self.subTest(file=str(path)):
                self.assertNotIn("PLAN_DEVIATION", _read(path))


# ── Done-evidence provenance: base_commit + full commit list ──────────────

TASK_BODY = """## Description

Evidence fixture task.

## Acceptance

- [ ] done

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
"""


class DoneEvidenceProvenance(unittest.TestCase):
    """`flowctl done` round-trips base_commit + a multi-commit list.

    Drives the production CLI wire form (the exact command the worker runs)
    against a tmp .flow fixture — the additive `base_commit` field and the
    full fix-loop commit list must survive into `show --json` evidence.
    """

    def setUp(self) -> None:
        self.tmpdir = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.prev_cwd = pathlib.Path.cwd()
        os.chdir(self.tmpdir)
        flow = self.tmpdir / ".flow"
        (flow / "tasks").mkdir(parents=True)
        (flow / "specs").mkdir(parents=True)
        (flow / "specs" / "fn-9.json").write_text(
            json.dumps({"id": "fn-9", "title": "Fixture", "status": "open"}),
            encoding="utf-8",
        )
        (flow / "specs" / "fn-9.md").write_text("# fn-9\n", encoding="utf-8")
        (flow / "tasks" / "fn-9.2.json").write_text(
            json.dumps({"id": "fn-9.2", "spec": "fn-9", "title": "Fixture"}),
            encoding="utf-8",
        )
        (flow / "tasks" / "fn-9.2.md").write_text(TASK_BODY, encoding="utf-8")

    def tearDown(self) -> None:
        os.chdir(self.prev_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _flowctl(self, *args: str) -> "subprocess.CompletedProcess[str]":
        return subprocess.run(
            [sys.executable, str(FLOWCTL_PY)] + list(args),
            cwd=str(self.tmpdir),
            capture_output=True,
            text=True,
        )

    def test_base_commit_and_full_commit_list_round_trip(self) -> None:
        start = self._flowctl("start", "fn-9.2", "--json")
        self.assertEqual(start.returncode, 0, start.stdout + start.stderr)

        base = "aaaa111122223333444455556666777788889999"
        fix_loop_commits = [
            "bbbb111122223333444455556666777788889999",
            "cccc111122223333444455556666777788889999",
            "dddd111122223333444455556666777788889999",
        ]
        evidence = {
            "commits": fix_loop_commits,
            "base_commit": base,
            "tests": ["pytest -q"],
            "prs": [],
        }
        ev_path = self.tmpdir / "evidence.json"
        ev_path.write_text(json.dumps(evidence), encoding="utf-8")

        done = self._flowctl(
            "done",
            "fn-9.2",
            "--summary",
            "fixture done",
            "--evidence-json",
            str(ev_path),
            "--json",
        )
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

        show = self._flowctl("show", "fn-9.2", "--json")
        self.assertEqual(show.returncode, 0, show.stdout + show.stderr)
        record = json.loads(show.stdout)
        self.assertEqual(record["status"], "done")
        got = record["evidence"]
        # Additive field survives untouched — no migration, no filtering.
        self.assertEqual(got["base_commit"], base)
        # Multi-commit fix-loop tasks fully covered: the FULL ordered list.
        self.assertEqual(got["commits"], fix_loop_commits)
        self.assertEqual(got["tests"], ["pytest -q"])


if __name__ == "__main__":
    unittest.main()
