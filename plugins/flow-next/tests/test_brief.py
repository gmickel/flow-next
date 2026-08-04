"""Deterministic fixture suite for `flowctl brief` (fn-164.1, R1–R3/R5).

Contract (pinned by this suite; implementation is the source of truth for
render format, these tests lock the behaviour):

- Six fixed sections (header counts, open specs, actionable, completions,
  memory, pointers). Empty `.flow/` → every body is "(none)", exit 0.
- Pure read, no git. Default budget 8000 chars on BOTH markdown and JSON
  (measure the larger). Selection computed once so both forms retain
  identical ids/omissions. `--full` lifts the budget.
- Truncation tiers in order: oldest completions → memory lines →
  open-spec goal lines → whole actionable rows (count line kept) →
  whole open-spec rows (count line kept) → excess unreadable lines to
  aggregate count. One `[truncated: … — use --full]` marker per tier.
- Titles 80-char end-ellipsis; goals/summaries/paths 120-char.
- Readiness = cmd_ready semantics (task-deps + parent-spec-deps).
  Closed-parent orphans still appear.
- Evidence: commits/tests/prs must be non-empty lists → true; default-empty
  dict, missing dict, or non-list values (string/dict) → false.
- Corrupt files → `[unreadable: <repo-relative path capped 120>]` at END
  of their section; siblings intact.
- No writes: `.flow/` tree hash-identical before/after all three forms.

Fixtures: importlib load of flowctl.py, TemporaryDirectory, NO git.
Drive through the production CLI (subprocess) where feasible; module-
level helpers used for hash / byte comparisons only.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any, Optional
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"
BUDGET = 8000
TITLE_CAP = 80
LINE_CAP = 120
PATH_CAP = 120


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_brief_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()


# ── Fixture helpers ───────────────────────────────────────────────────────


class BriefRepoTestCase(unittest.TestCase):
    """Shared TemporaryDirectory + hand-built `.flow/` (no git)."""

    memory_enabled: bool = False

    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp()).resolve()
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        self.flow = self.tmpdir / ".flow"
        (self.flow / "specs").mkdir(parents=True)
        (self.flow / "tasks").mkdir(parents=True)
        cfg: dict[str, Any] = {}
        if self.memory_enabled:
            cfg["memory"] = {"enabled": True}
        (self.flow / "config.json").write_text(
            json.dumps(cfg), encoding="utf-8"
        )

    def tearDown(self) -> None:
        os.chdir(self.prev_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # ---- writers -----------------------------------------------------

    def _mk_spec(
        self,
        spec_id: str,
        *,
        title: str = "",
        status: str = "open",
        ready: bool = False,
        depends_on_epics: Optional[list[str]] = None,
        goal: str = "",
    ) -> None:
        data: dict[str, Any] = {
            "id": spec_id,
            "title": title or spec_id,
            "status": status,
            "ready": ready,
            "depends_on_epics": depends_on_epics or [],
        }
        (self.flow / "specs" / f"{spec_id}.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        body = f"# {spec_id}\n\n"
        if goal:
            body += f"## Goal & Context\n\n{goal}\n\n"
        body += "## Overview\n\nBody.\n"
        (self.flow / "specs" / f"{spec_id}.md").write_text(
            body, encoding="utf-8"
        )

    def _mk_task(
        self,
        task_id: str,
        spec_id: str,
        *,
        title: str = "",
        status: str = "todo",
        depends_on: Optional[list[str]] = None,
        evidence: Any = ...,  # ellipsis sentinel = omit key
        updated_at: str = "",
        assignee: str = "",
        claimed_at: str = "",
        claim_note: str = "",
        done_summary: str = "",
        priority: Optional[int] = None,
    ) -> None:
        data: dict[str, Any] = {
            "id": task_id,
            "spec": spec_id,
            "title": title or task_id,
            "status": status,
            "depends_on": depends_on or [],
        }
        if evidence is not ...:
            data["evidence"] = evidence
        if updated_at:
            data["updated_at"] = updated_at
        if assignee:
            data["assignee"] = assignee
        if claimed_at:
            data["claimed_at"] = claimed_at
        if claim_note:
            data["claim_note"] = claim_note
        if priority is not None:
            data["priority"] = priority
        (self.flow / "tasks" / f"{task_id}.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        summary = done_summary or f"Shipped {task_id}."
        md = (
            f"## Description\n\nFixture task.\n\n"
            f"## Done summary\n\n{summary}\n"
        )
        (self.flow / "tasks" / f"{task_id}.md").write_text(
            md, encoding="utf-8"
        )

    def _mk_memory(
        self,
        slug: str,
        date: str,
        *,
        title: str = "",
        track: str = "bug",
        category: str = "build-errors",
        status: str = "",
        body: str = "body\n",
        corrupt: bool = False,
    ) -> Path:
        d = self.flow / "memory" / track / category
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"{slug}-{date}.md"
        if corrupt:
            path.write_text("not a memory entry\n", encoding="utf-8")
            return path
        title = title or slug.replace("-", " ")
        fm_status = f'status: {status}\n' if status else ""
        text = (
            f"---\n"
            f'title: "{title}"\n'
            f'date: "{date}"\n'
            f"track: {track}\n"
            f"category: {category}\n"
            f"module: fixture\n"
            f"tags: []\n"
            f"{fm_status}"
            f"---\n\n"
            f"{body}"
        )
        path.write_text(text, encoding="utf-8")
        return path

    # ---- CLI drivers -------------------------------------------------

    def _flowctl(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(FLOWCTL_PY)] + list(args),
            cwd=str(self.tmpdir),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def _brief(self, *flags: str) -> subprocess.CompletedProcess[str]:
        return self._flowctl("brief", *flags)

    def _brief_md(self) -> str:
        r = self._brief()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def _brief_json(self, *flags: str) -> dict:
        r = self._brief("--json", *flags)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return json.loads(r.stdout)

    # ---- tree hash (no-writes) ---------------------------------------

    @staticmethod
    def _hash_flow_tree(flow_dir: Path) -> dict[str, str]:
        """Map repo-relative paths → content sha256 (files only, sorted)."""
        out: dict[str, str] = {}
        if not flow_dir.is_dir():
            return out
        for path in sorted(flow_dir.rglob("*")):
            if not path.is_file():
                continue
            rel = str(path.relative_to(flow_dir)).replace("\\", "/")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            out[rel] = digest
        return out


def _section(md: str, heading: str) -> str:
    """Extract body under `## <heading>` until the next `## ` or EOF."""
    pattern = re.compile(
        rf"^## {re.escape(heading)}.*$", re.MULTILINE
    )
    m = pattern.search(md)
    if not m:
        raise AssertionError(f"section {heading!r} not found in:\n{md}")
    start = m.end()
    nxt = re.search(r"^## ", md[start:], re.MULTILINE)
    end = start + nxt.start() if nxt else len(md)
    return md[start:end].strip("\n")


def _ids_from_md_section(body: str) -> list[str]:
    """Pull leading ids from `- id:` / `- [status] id:` / `- entry_id —` lines."""
    ids: list[str] = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("- ") or line.startswith("- [unreadable"):
            continue
        # actionable: - [ready] fn-1.1: title
        m = re.match(r"- \[[^\]]+\] (\S+):", line)
        if m:
            ids.append(m.group(1))
            continue
        # open specs / completions: - fn-1: title
        m = re.match(r"- (\S+):", line)
        if m:
            ids.append(m.group(1))
            continue
        # memory: - entry_id — title
        m = re.match(r"- (\S+) —", line)
        if m:
            ids.append(m.group(1))
    return ids


# ── 1. Pinned populated + empty ───────────────────────────────────────────


class EmptyFixtureTest(BriefRepoTestCase):
    """Empty `.flow/` → every section body is `(none)`, exit 0."""

    def setUp(self) -> None:
        # Bare `.flow/` — no specs/tasks dirs either.
        self.tmpdir = Path(tempfile.mkdtemp()).resolve()
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        (self.tmpdir / ".flow").mkdir()
        self.flow = self.tmpdir / ".flow"

    def test_empty_all_none_exit_zero(self) -> None:
        r = self._brief()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        md = r.stdout
        self.assertIn("# Session brief\n", md)
        self.assertEqual(_section(md, "Open specs (0)").strip(), "(none)")
        self.assertEqual(
            _section(md, "Actionable tasks (0)").strip(), "(none)"
        )
        self.assertEqual(
            _section(md, "Recent completions (0)").strip(), "(none)"
        )
        self.assertEqual(_section(md, "Memory (0)").strip(), "(none)")
        self.assertIn("## Pointers", md)
        self.assertIn("Go deeper (not included in this brief):", md)
        # header counts all zero / memory off
        self.assertIn(
            "Open specs: 0 | Ready: 0 | In progress: 0 | Done: 0 | Memory: off",
            md,
        )

    def test_empty_json(self) -> None:
        payload = self._brief_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["header"]["open_specs"], 0)
        self.assertEqual(payload["header"]["ready_tasks"], 0)
        self.assertEqual(payload["header"]["in_progress_tasks"], 0)
        self.assertEqual(payload["header"]["done_tasks"], 0)
        self.assertFalse(payload["header"]["memory_enabled"])
        self.assertEqual(payload["open_specs"]["items"], [])
        self.assertEqual(payload["actionable_tasks"]["items"], [])
        self.assertEqual(payload["recent_completions"]["items"], [])
        self.assertEqual(payload["memory"]["items"], [])
        for flag in payload["truncated"].values():
            self.assertFalse(flag)


class PopulatedFixtureTest(BriefRepoTestCase):
    """Pinned populated fixture — exact section contents for known data."""

    memory_enabled = True

    def setUp(self) -> None:
        super().setUp()
        self._mk_spec(
            "fn-1",
            title="Alpha Spec",
            ready=True,
            goal="Ship the alpha gadget for testing.",
        )
        # closed/done/superseded excluded from open-specs
        self._mk_spec("fn-2", title="Done Spec", status="done")
        self._mk_spec("fn-3", title="Closed Spec", status="closed")
        self._mk_spec("fn-4", title="Superseded Spec", status="superseded")

        self._mk_task("fn-1.1", "fn-1", title="Ready task", status="todo")
        self._mk_task(
            "fn-1.2",
            "fn-1",
            title="Blocked by unfinished dep",
            status="todo",
            depends_on=["fn-1.1"],
        )
        self._mk_task(
            "fn-1.3",
            "fn-1",
            title="In progress work",
            status="in_progress",
            assignee="alice",
            claimed_at="2026-01-01T00:00:00Z",
            claim_note="wip",
        )
        self._mk_task(
            "fn-1.4",
            "fn-1",
            title="Done with evidence",
            status="done",
            evidence={"commits": ["abc123"], "tests": [], "prs": []},
            updated_at="2026-06-01T00:00:00Z",
            done_summary="Shipped evidence task.",
        )
        self._mk_task(
            "fn-1.5",
            "fn-1",
            title="Done empty evidence",
            status="done",
            evidence={"commits": [], "tests": [], "prs": []},
            updated_at="2026-06-02T00:00:00Z",
            done_summary="Shipped empty-evidence task.",
        )
        self._mk_task(
            "fn-1.6",
            "fn-1",
            title="Done legacy no evidence",
            status="done",
            updated_at="2026-06-03T00:00:00Z",
            done_summary="Shipped legacy task.",
        )
        self._mk_memory(
            "fixture-entry", "2026-05-01", title="Fixture memory"
        )

    def test_pinned_markdown_sections(self) -> None:
        md = self._brief_md()
        # section order
        positions = [
            md.index("# Session brief"),
            md.index("## Open specs (1)"),
            md.index("## Actionable tasks (2)"),
            md.index("## Recent completions (3)"),
            md.index("## Memory (1)"),
            md.index("## Pointers"),
        ]
        self.assertEqual(positions, sorted(positions))

        self.assertIn(
            "Open specs: 1 | Ready: 1 | In progress: 1 | Done: 3 | Memory: on",
            md,
        )

        open_body = _section(md, "Open specs (1)")
        self.assertEqual(
            open_body.strip(),
            "- fn-1: Alpha Spec [open] ready — Ship the alpha gadget for testing.",
        )
        # closed statuses excluded
        self.assertNotIn("fn-2", open_body)
        self.assertNotIn("fn-3", open_body)
        self.assertNotIn("fn-4", open_body)

        act_body = _section(md, "Actionable tasks (2)")
        self.assertIn("- [ready] fn-1.1: Ready task", act_body)
        self.assertIn(
            "- [in_progress] fn-1.3: In progress work "
            "(@alice, claimed_at=2026-01-01T00:00:00Z, note=wip)",
            act_body,
        )
        # blocked-by-dep must NOT appear
        self.assertNotIn("fn-1.2", act_body)

        comp_body = _section(md, "Recent completions (3)")
        self.assertEqual(
            [ln.strip() for ln in comp_body.strip().splitlines()],
            [
                "- fn-1.4: Shipped evidence task. [evidence=yes]",
                "- fn-1.5: Shipped empty-evidence task. [evidence=no]",
                "- fn-1.6: Shipped legacy task. [evidence=no]",
            ],
        )

        mem_body = _section(md, "Memory (1)")
        self.assertEqual(
            mem_body.strip(),
            "- bug/build-errors/fixture-entry-2026-05-01 — Fixture memory",
        )

        ptr = _section(md, "Pointers")
        self.assertIn("`flowctl cat <id>`", ptr)
        self.assertIn("`flowctl anchor <task-id> --md`", ptr)
        self.assertIn("Git state is NOT in brief", ptr)

    def test_pinned_json_sections(self) -> None:
        payload = self._brief_json()
        self.assertEqual(
            [s["id"] for s in payload["open_specs"]["items"]], ["fn-1"]
        )
        self.assertEqual(
            payload["open_specs"]["items"][0]["goal"],
            "Ship the alpha gadget for testing.",
        )
        self.assertTrue(payload["open_specs"]["items"][0]["ready"])
        act_ids = [t["id"] for t in payload["actionable_tasks"]["items"]]
        self.assertEqual(act_ids, ["fn-1.1", "fn-1.3"])
        comps = payload["recent_completions"]["items"]
        self.assertEqual(
            [(c["id"], c["evidence"]) for c in comps],
            [
                ("fn-1.4", True),
                ("fn-1.5", False),
                ("fn-1.6", False),
            ],
        )
        self.assertEqual(
            payload["memory"]["items"][0]["entry_id"],
            "bug/build-errors/fixture-entry-2026-05-01",
        )


# ── 2. Budget fixture (20/50/30) ──────────────────────────────────────────


class BudgetFixtureTest(BriefRepoTestCase):
    """20 specs / 50 tasks / 30 memory — both forms <= 8000; tiers ordered."""

    memory_enabled = True

    def setUp(self) -> None:
        super().setUp()
        for i in range(1, 21):
            self._mk_spec(
                f"fn-{i}",
                title=f"Spec {i} title with padding " + "x" * 30,
                goal=f"Goal line for spec {i} " + "G" * 90,
            )
        # 50 tasks on fn-1: 35 ready, 5 in_progress, 10 done
        for i in range(1, 51):
            if i > 40:
                status = "done"
            elif i > 35:
                status = "in_progress"
            else:
                status = "todo"
            kwargs: dict[str, Any] = {
                "title": f"Task {i} " + "T" * 40,
                "status": status,
                "updated_at": f"2026-01-{(i % 28) + 1:02d}T00:00:00Z",
                "done_summary": f"Done summary for task {i} " + "S" * 50,
            }
            if status == "done":
                kwargs["evidence"] = {
                    "commits": [f"c{i}"],
                    "tests": [],
                    "prs": [],
                }
            self._mk_task(f"fn-1.{i}", "fn-1", **kwargs)
        for i in range(1, 31):
            day = f"2026-05-{(i % 28) + 1:02d}"
            self._mk_memory(
                f"mem-entry-{i:03d}",
                day,
                title=f"Memory entry {i} " + "M" * 30,
            )

    def test_both_forms_under_budget(self) -> None:
        md_r = self._brief()
        js_r = self._brief("--json")
        self.assertEqual(md_r.returncode, 0, md_r.stderr)
        self.assertEqual(js_r.returncode, 0, js_r.stderr)
        self.assertLessEqual(len(md_r.stdout), BUDGET)
        self.assertLessEqual(len(js_r.stdout), BUDGET)

    def test_truncation_tiers_applied_in_order(self) -> None:
        """With 20/50/30, early tiers fire; count lines survive."""
        md = self._brief_md()
        payload = self._brief_json()
        flags = payload["truncated"]

        # Completions tier fires (oldest first) — may empty residual pool
        self.assertTrue(flags["completions"])
        # Memory tier fires
        self.assertTrue(flags["memory"])
        # Spec goals tier fires (goals empty, rows may remain)
        self.assertTrue(flags["spec_goals"])

        # Count lines always kept at header values
        self.assertIn(f"## Open specs ({payload['header']['open_specs']})", md)
        self.assertIn(
            f"## Actionable tasks ({payload['actionable_tasks']['count']})",
            md,
        )
        self.assertIn(f"## Memory ({payload['memory']['count']})", md)

        # Markers present for every fired tier
        if flags["completions"]:
            self.assertIn(
                "[truncated: recent completions omitted — use --full]", md
            )
        if flags["memory"]:
            self.assertIn(
                "[truncated: memory lines omitted — use --full]", md
            )
        if flags["spec_goals"] and not flags["open_specs"]:
            self.assertIn(
                "[truncated: open-spec goal lines omitted — use --full]", md
            )
        if flags["actionable"]:
            self.assertIn(
                "[truncated: actionable-task rows omitted — use --full]", md
            )
        if flags["open_specs"]:
            self.assertIn(
                "[truncated: open-spec rows omitted — use --full]", md
            )

        # Goals dropped when tier 3 fired
        if flags["spec_goals"]:
            for item in payload["open_specs"]["items"]:
                self.assertEqual(item["goal"], "")

        # Header counts preserved (pre-truncation totals)
        self.assertEqual(payload["header"]["open_specs"], 20)
        self.assertEqual(payload["memory"]["count"], 30)
        self.assertEqual(payload["actionable_tasks"]["count"], 40)

        # Residual items <= original counts
        self.assertLessEqual(
            len(payload["open_specs"]["items"]), 20
        )
        self.assertLessEqual(
            len(payload["actionable_tasks"]["items"]), 40
        )
        self.assertLessEqual(
            len(payload["memory"]["items"]), 30
        )
        self.assertLessEqual(
            len(payload["recent_completions"]["items"]), 5
        )


# ── 3. Pathological (mandatory rows alone > 8000) ─────────────────────────


class PathologicalFixtureTest(BriefRepoTestCase):
    """100+ rows, long titles — budget holds; 80-char title cap w/ ellipsis."""

    def setUp(self) -> None:
        super().setUp()
        long_title = "T" * 200
        for i in range(1, 121):
            self._mk_spec(
                f"fn-{i}",
                title=long_title,
                goal="G" * 200,
            )
        for i in range(1, 80):
            self._mk_task(
                f"fn-1.{i}",
                "fn-1",
                title=long_title,
                status="todo",
            )

    def test_budget_holds_and_title_capped(self) -> None:
        md_r = self._brief()
        js_r = self._brief("--json")
        self.assertEqual(md_r.returncode, 0, md_r.stderr)
        self.assertLessEqual(len(md_r.stdout), BUDGET)
        self.assertLessEqual(len(js_r.stdout), BUDGET)

        payload = json.loads(js_r.stdout)
        self.assertEqual(payload["header"]["open_specs"], 120)
        # Some open-spec rows must have been dropped (tier 5)
        self.assertTrue(payload["truncated"]["open_specs"])
        self.assertLess(len(payload["open_specs"]["items"]), 120)
        # Count line kept
        self.assertIn("## Open specs (120)", md_r.stdout)

        # Title cap 80 with end ellipsis
        for item in payload["open_specs"]["items"]:
            self.assertEqual(len(item["title"]), TITLE_CAP)
            self.assertTrue(item["title"].endswith("…"))
        for item in payload["actionable_tasks"]["items"]:
            self.assertEqual(len(item["title"]), TITLE_CAP)
            self.assertTrue(item["title"].endswith("…"))


# ── 4. Many-corrupt + long-root-path ──────────────────────────────────────


class ManyCorruptAndLongRootTest(unittest.TestCase):
    """Many unreadable files → aggregate; long root path capped at 120."""

    def setUp(self) -> None:
        self.prev_cwd = Path.cwd()

    def tearDown(self) -> None:
        os.chdir(self.prev_cwd)

    def _run(self, cwd: Path, *flags: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(FLOWCTL_PY), "brief", *flags],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_many_corrupt_aggregate_under_budget(self) -> None:
        td = Path(tempfile.mkdtemp()).resolve()
        try:
            flow = td / ".flow"
            (flow / "specs").mkdir(parents=True)
            (flow / "tasks").mkdir(parents=True)
            for i in range(1, 201):
                (flow / "specs" / f"fn-{i}.json").write_text(
                    "{bad", encoding="utf-8"
                )
                (flow / "tasks" / f"fn-1.{i}.json").write_text(
                    "{bad", encoding="utf-8"
                )
                (flow / "tasks" / f"fn-1.{i}.md").write_text(
                    "x", encoding="utf-8"
                )
            os.chdir(td)
            md_r = self._run(td)
            js_r = self._run(td, "--json")
            self.assertEqual(md_r.returncode, 0, md_r.stderr)
            self.assertLessEqual(len(md_r.stdout), BUDGET)
            self.assertLessEqual(len(js_r.stdout), BUDGET)
            payload = json.loads(js_r.stdout)
            self.assertTrue(payload["truncated"]["unreadable"])
            self.assertEqual(payload["unreadable_aggregate"], 400)
            self.assertIn(
                "[400 unreadable files — use --full]", md_r.stdout
            )
            # Individual unreadable lines collapsed
            self.assertEqual(payload["open_specs"]["unreadable"], [])
            self.assertEqual(payload["actionable_tasks"]["unreadable"], [])
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_long_root_path_capped_at_120(self) -> None:
        # Build a deliberately deep root so resolved path >> 120.
        deep = "a" * 30
        base = (
            Path(tempfile.gettempdir()).resolve()
            / "brief-long-root"
            / deep
            / deep
            / deep
            / deep
            / deep
            / deep
        )
        try:
            flow = base / ".flow"
            (flow / "specs").mkdir(parents=True, exist_ok=True)
            (flow / "tasks").mkdir(parents=True, exist_ok=True)
            os.chdir(base)
            md_r = self._run(base)
            js_r = self._run(base, "--json")
            self.assertEqual(md_r.returncode, 0, md_r.stderr)
            payload = json.loads(js_r.stdout)
            root = payload["header"]["repo_root"]
            self.assertLessEqual(len(root), PATH_CAP)
            self.assertEqual(len(root), PATH_CAP)
            self.assertTrue(root.endswith("…"))
            # Markdown header uses the same capped path
            repo_line = [
                ln for ln in md_r.stdout.splitlines() if ln.startswith("Repo: ")
            ][0]
            self.assertEqual(len(repo_line[len("Repo: ") :]), PATH_CAP)
            # Full path is actually longer than the cap
            self.assertGreater(len(str(base.resolve())), PATH_CAP)
        finally:
            # climb out before rmtree
            os.chdir(Path(tempfile.gettempdir()))
            shutil.rmtree(
                Path(tempfile.gettempdir()) / "brief-long-root",
                ignore_errors=True,
            )


# ── 5. Determinism ────────────────────────────────────────────────────────


class DeterminismTest(BriefRepoTestCase):
    memory_enabled = True

    def setUp(self) -> None:
        super().setUp()
        self._mk_spec("fn-1", title="Det Spec", goal="Deterministic goal.")
        self._mk_task("fn-1.1", "fn-1", title="Det task", status="todo")
        self._mk_task(
            "fn-1.2",
            "fn-1",
            title="Done det",
            status="done",
            evidence={"commits": ["x"], "tests": [], "prs": []},
            updated_at="2026-06-01T00:00:00Z",
        )
        self._mk_memory("det-mem", "2026-05-01", title="Det mem")

    def test_md_byte_identical_across_runs(self) -> None:
        a = self._brief()
        b = self._brief()
        self.assertEqual(a.returncode, 0)
        self.assertEqual(a.stdout, b.stdout)

    def test_json_byte_identical_across_runs(self) -> None:
        a = self._brief("--json")
        b = self._brief("--json")
        self.assertEqual(a.returncode, 0)
        self.assertEqual(a.stdout, b.stdout)


# ── 6. md / JSON parity ───────────────────────────────────────────────────


class MdJsonParityTest(BudgetFixtureTest):
    """Identical retained ids/omissions; both <= 8000; per-section truncated flags."""

    def test_parity_retained_ids_and_flags(self) -> None:
        md_r = self._brief()
        js_r = self._brief("--json")
        self.assertLessEqual(len(md_r.stdout), BUDGET)
        self.assertLessEqual(len(js_r.stdout), BUDGET)
        payload = json.loads(js_r.stdout)
        md = md_r.stdout

        # Per-section truncated flags present
        for key in (
            "completions",
            "memory",
            "spec_goals",
            "actionable",
            "open_specs",
            "unreadable",
        ):
            self.assertIn(key, payload["truncated"])
            self.assertIsInstance(payload["truncated"][key], bool)

        # Also on section objects
        self.assertIn("truncated", payload["open_specs"])
        self.assertIn("truncated", payload["actionable_tasks"])
        self.assertIn("truncated", payload["recent_completions"])
        self.assertIn("truncated", payload["memory"])

        # Retained ids match across forms
        open_md = _ids_from_md_section(
            _section(md, f"Open specs ({payload['header']['open_specs']})")
        )
        open_js = [i["id"] for i in payload["open_specs"]["items"]]
        self.assertEqual(open_md, open_js)

        act_md = _ids_from_md_section(
            _section(
                md,
                f"Actionable tasks ({payload['actionable_tasks']['count']})",
            )
        )
        act_js = [i["id"] for i in payload["actionable_tasks"]["items"]]
        self.assertEqual(act_md, act_js)

        # Completions section heading uses residual count
        n_comp = len(payload["recent_completions"]["items"])
        comp_md = _ids_from_md_section(
            _section(md, f"Recent completions ({n_comp})")
        )
        comp_js = [i["id"] for i in payload["recent_completions"]["items"]]
        self.assertEqual(comp_md, comp_js)

        mem_md = _ids_from_md_section(
            _section(md, f"Memory ({payload['memory']['count']})")
        )
        mem_js = [i["entry_id"] for i in payload["memory"]["items"]]
        self.assertEqual(mem_md, mem_js)


# ── 7. Readiness semantics ────────────────────────────────────────────────


class ReadinessTest(BriefRepoTestCase):
    """Task-dep block, parent-spec-dep block, closed-parent orphan."""

    def setUp(self) -> None:
        super().setUp()
        # fn-10 depends on open fn-11 → its tasks not ready
        self._mk_spec(
            "fn-10",
            title="Gated parent",
            depends_on_epics=["fn-11"],
        )
        self._mk_spec("fn-11", title="Blocker parent", status="open")
        # closed parent — orphan tasks still surface
        self._mk_spec("fn-12", title="Closed parent", status="done")

        self._mk_task(
            "fn-10.1",
            "fn-10",
            title="Gated by parent dep",
            status="todo",
        )
        self._mk_task(
            "fn-11.1",
            "fn-11",
            title="Ready on open parent",
            status="todo",
        )
        self._mk_task(
            "fn-11.2",
            "fn-11",
            title="Blocked by task dep",
            status="todo",
            depends_on=["fn-11.1"],
        )
        self._mk_task(
            "fn-12.1",
            "fn-12",
            title="Orphan on closed parent",
            status="todo",
        )

    def test_task_dep_and_spec_dep_gates(self) -> None:
        payload = self._brief_json()
        ready_ids = [
            t["id"]
            for t in payload["actionable_tasks"]["items"]
            if t["status"] == "ready"
        ]
        # Ready: open-parent free task + closed-parent orphan
        self.assertIn("fn-11.1", ready_ids)
        self.assertIn("fn-12.1", ready_ids)
        # NOT ready: unfinished task-dep
        self.assertNotIn("fn-11.2", ready_ids)
        # NOT ready: parent has unmet spec-dep
        self.assertNotIn("fn-10.1", ready_ids)

        md = self._brief_md()
        act = _section(md, "Actionable tasks (2)")
        self.assertIn("fn-11.1", act)
        self.assertIn("fn-12.1", act)
        self.assertNotIn("fn-11.2", act)
        self.assertNotIn("fn-10.1", act)


# ── 8. Evidence + completions ordering ────────────────────────────────────


class CompletionsEvidenceTest(BriefRepoTestCase):
    """Evidence flag, ordering (updated_at asc + id), last 5, summary cap 120."""

    def setUp(self) -> None:
        super().setUp()
        self._mk_spec("fn-1", title="E")
        # 7 done tasks so only last 5 survive the pool cap
        long_summary = "S" * 200
        cases = [
            # (n, updated_at, evidence, summary)
            (1, "2026-01-01T00:00:00Z", {"commits": [], "tests": [], "prs": []}, "oldest empty"),
            (2, "2026-01-02T00:00:00Z", {"commits": ["c"], "tests": [], "prs": []}, "has commits"),
            (3, "2026-01-03T00:00:00Z", {"commits": [], "tests": ["t"], "prs": []}, "has tests"),
            (4, "2026-01-04T00:00:00Z", {"commits": [], "tests": [], "prs": ["p"]}, "has prs"),
            (5, "2026-01-05T00:00:00Z", None, "legacy no dict"),  # omit key
            (6, "2026-01-06T00:00:00Z", {"commits": [], "tests": [], "prs": []}, long_summary),
            (7, "2026-01-06T00:00:00Z", {"commits": ["z"], "tests": ["t"], "prs": []}, "same day later id"),
        ]
        for n, updated, evid, summary in cases:
            kwargs: dict[str, Any] = {
                "title": f"Done {n}",
                "status": "done",
                "updated_at": updated,
                "done_summary": summary,
            }
            if evid is None:
                # legacy: no evidence key
                pass
            else:
                kwargs["evidence"] = evid
            self._mk_task(f"fn-1.{n}", "fn-1", **kwargs)

    def test_evidence_ordering_cap_and_summary_cap(self) -> None:
        payload = self._brief_json()
        items = payload["recent_completions"]["items"]
        # last 5 of 7 (pool sorted asc, take tail) → fn-1.3 .. fn-1.7
        self.assertEqual(len(items), 5)
        self.assertEqual(
            [c["id"] for c in items],
            ["fn-1.3", "fn-1.4", "fn-1.5", "fn-1.6", "fn-1.7"],
        )
        by_id = {c["id"]: c for c in items}
        # evidence flags
        self.assertTrue(by_id["fn-1.3"]["evidence"])   # tests nonempty
        self.assertTrue(by_id["fn-1.4"]["evidence"])   # prs nonempty
        self.assertFalse(by_id["fn-1.5"]["evidence"])  # legacy no dict
        self.assertFalse(by_id["fn-1.6"]["evidence"])  # empty dict
        self.assertTrue(by_id["fn-1.7"]["evidence"])   # commits+tests
        # summary capped at 120 with ellipsis
        self.assertEqual(len(by_id["fn-1.6"]["summary"]), LINE_CAP)
        self.assertTrue(by_id["fn-1.6"]["summary"].endswith("…"))

        md = self._brief_md()
        body = _section(md, "Recent completions (5)")
        self.assertIn("fn-1.3: has tests [evidence=yes]", body)
        self.assertIn("fn-1.5: legacy no dict [evidence=no]", body)
        self.assertIn("fn-1.6:", body)
        self.assertIn("[evidence=no]", body)
        # oldest two dropped from the N=5 pool
        self.assertNotIn("fn-1.1", body)
        self.assertNotIn("fn-1.2", body)


# ── 9. Corrupt-file degradation ───────────────────────────────────────────


class CorruptFileDegradationTest(BriefRepoTestCase):
    """One corrupt of each type → unreadable line at END; siblings intact."""

    memory_enabled = True

    def setUp(self) -> None:
        super().setUp()
        self._mk_spec("fn-1", title="Good Spec", goal="Good goal line.")
        # corrupt spec
        (self.flow / "specs" / "fn-2.json").write_text(
            "{not-json", encoding="utf-8"
        )
        self._mk_task("fn-1.1", "fn-1", title="Good task", status="todo")
        # corrupt task
        (self.flow / "tasks" / "fn-1.2.json").write_text(
            "NOT JSON", encoding="utf-8"
        )
        (self.flow / "tasks" / "fn-1.2.md").write_text("x", encoding="utf-8")
        self._mk_memory("good-entry", "2026-05-01", title="Good mem")
        self._mk_memory("bad-entry", "2026-05-02", corrupt=True)

    def test_unreadable_at_end_siblings_intact(self) -> None:
        md = self._brief_md()
        payload = self._brief_json()

        open_body = _section(md, "Open specs (1)")
        lines = [ln for ln in open_body.splitlines() if ln.strip()]
        self.assertTrue(lines[0].startswith("- fn-1: Good Spec"))
        self.assertTrue(lines[-1].startswith("- [unreadable: "))
        self.assertIn(".flow/specs/fn-2.json", lines[-1])
        # path repo-relative (no absolute prefix) and capped
        unreadable_spec = payload["open_specs"]["unreadable"]
        self.assertEqual(len(unreadable_spec), 1)
        self.assertEqual(unreadable_spec[0], ".flow/specs/fn-2.json")
        self.assertLessEqual(len(unreadable_spec[0]), PATH_CAP)

        act_body = _section(md, "Actionable tasks (1)")
        act_lines = [ln for ln in act_body.splitlines() if ln.strip()]
        self.assertTrue(act_lines[0].startswith("- [ready] fn-1.1: Good task"))
        self.assertTrue(act_lines[-1].startswith("- [unreadable: "))
        unreadable_task = payload["actionable_tasks"]["unreadable"]
        self.assertEqual(len(unreadable_task), 1)
        self.assertEqual(unreadable_task[0], ".flow/tasks/fn-1.2.json")

        mem_body = _section(md, "Memory (1)")
        mem_lines = [ln for ln in mem_body.splitlines() if ln.strip()]
        self.assertTrue(
            mem_lines[0].startswith(
                "- bug/build-errors/good-entry-2026-05-01 — Good mem"
            )
        )
        self.assertTrue(mem_lines[-1].startswith("- [unreadable: "))
        self.assertIn(
            ".flow/memory/bug/build-errors/bad-entry-2026-05-02.md",
            mem_lines[-1],
        )
        unreadable_mem = payload["memory"]["unreadable"]
        self.assertEqual(len(unreadable_mem), 1)
        self.assertEqual(
            unreadable_mem[0],
            ".flow/memory/bug/build-errors/bad-entry-2026-05-02.md",
        )


# ── 10. No-writes assertion ───────────────────────────────────────────────


class NoWritesTest(BriefRepoTestCase):
    memory_enabled = True

    def setUp(self) -> None:
        super().setUp()
        self._mk_spec("fn-1", title="NW", goal="No write goal.")
        self._mk_task("fn-1.1", "fn-1", title="NW task", status="todo")
        self._mk_task(
            "fn-1.2",
            "fn-1",
            title="NW done",
            status="done",
            evidence={"commits": ["a"], "tests": [], "prs": []},
            updated_at="2026-06-01T00:00:00Z",
        )
        self._mk_memory("nw-mem", "2026-05-01", title="NW mem")

    def test_flow_tree_unchanged_across_all_forms(self) -> None:
        before = self._hash_flow_tree(self.flow)
        for flags in ((), ("--json",), ("--full",), ("--json", "--full")):
            r = self._brief(*flags)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            after = self._hash_flow_tree(self.flow)
            self.assertEqual(
                before,
                after,
                f".flow/ mutated by brief {' '.join(flags)!r}",
            )


# ── 11. --full lifts budget ───────────────────────────────────────────────


class FullFlagTest(BudgetFixtureTest):
    """`--full` lifts the 8000 budget; default truncates where full exceeds."""

    def test_full_exceeds_budget_where_default_truncates(self) -> None:
        default_md = self._brief()
        default_js = self._brief("--json")
        full_md = self._brief("--full")
        full_js = self._brief("--json", "--full")

        self.assertEqual(default_md.returncode, 0)
        self.assertEqual(full_md.returncode, 0)
        self.assertLessEqual(len(default_md.stdout), BUDGET)
        self.assertLessEqual(len(default_js.stdout), BUDGET)
        # --full retains everything → over budget on this fixture
        self.assertGreater(len(full_md.stdout), BUDGET)
        self.assertGreater(len(full_js.stdout), BUDGET)

        full_payload = json.loads(full_js.stdout)
        for flag in full_payload["truncated"].values():
            self.assertFalse(flag)
        # Full retains all memory + open specs + actionable
        self.assertEqual(len(full_payload["open_specs"]["items"]), 20)
        self.assertEqual(len(full_payload["memory"]["items"]), 30)
        self.assertEqual(len(full_payload["actionable_tasks"]["items"]), 40)
        # Completions still capped at N=5 (pool size, not budget)
        self.assertEqual(len(full_payload["recent_completions"]["items"]), 5)
        # Goals retained under --full
        self.assertTrue(
            any(i.get("goal") for i in full_payload["open_specs"]["items"])
        )
        # No truncation markers in full md
        self.assertNotIn("[truncated:", full_md.stdout)


# ── 12. No-subprocess / no-git contract ───────────────────────────────────


class NoSubprocessContractTest(BriefRepoTestCase):
    """brief never shells out — monkeypatched subprocess raises."""

    memory_enabled = True

    def setUp(self) -> None:
        super().setUp()
        self._mk_spec(
            "fn-1",
            title="NoSub Spec",
            ready=True,
            goal="Goal for no-subprocess fixture.",
        )
        self._mk_task("fn-1.1", "fn-1", title="Ready", status="todo")
        self._mk_task(
            "fn-1.2",
            "fn-1",
            title="Done",
            status="done",
            evidence={"commits": ["abc"], "tests": [], "prs": []},
            updated_at="2026-06-01T00:00:00Z",
        )
        self._mk_memory("nosub-mem", "2026-05-01", title="NoSub mem")
        # Optional .git pointer — resolver must read it without git(1).
        (self.tmpdir / ".git").write_text(
            "gitdir: /nonexistent/worktree/gitdir\n", encoding="utf-8"
        )

    def _run_cmd_brief(self, *, use_json: bool = False, full: bool = False) -> str:
        args = argparse.Namespace(json=use_json, full=full)
        buf = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            flowctl.cmd_brief(args)
        return buf.getvalue()

    def test_brief_forms_invoke_no_subprocess(self) -> None:
        def boom(*_a: Any, **_k: Any) -> None:
            raise AssertionError("subprocess invoked from brief path")

        with (
            mock.patch.object(flowctl.subprocess, "run", side_effect=boom),
            mock.patch.object(flowctl.subprocess, "Popen", side_effect=boom),
            mock.patch.object(
                flowctl.subprocess, "check_output", side_effect=boom
            ),
        ):
            md = self._run_cmd_brief()
            js = self._run_cmd_brief(use_json=True)
            full = self._run_cmd_brief(full=True)

        self.assertIn("# Session brief", md)
        self.assertIn("fn-1.1", md)
        payload = json.loads(js)
        self.assertTrue(payload["success"])
        self.assertIn("fn-1", [s["id"] for s in payload["open_specs"]["items"]])
        self.assertIn("# Session brief", full)
        self.assertGreater(len(full), 0)


# ── 13. Tolerant collectors (UTF-8 / consistency / chmod) ─────────────────


class TolerantCollectorExtrasTest(BriefRepoTestCase):
    """Invalid UTF-8, mismatched task id, unreadable task md, bad memory."""

    memory_enabled = True

    def setUp(self) -> None:
        super().setUp()
        self._mk_spec("fn-1", title="Good Spec", goal="Good goal line.")
        # Invalid-UTF-8 spec markdown (json sibling remains valid).
        (self.flow / "specs" / "fn-1.md").write_bytes(
            b"## Goal & Context\n\n\xff\xfe invalid utf-8 goal\n"
        )
        # Valid sibling task
        self._mk_task("fn-1.1", "fn-1", title="Good task", status="todo")
        # Task json with mismatched payload id → consistency error, not crash
        bad_task = {
            "id": "fn-1.99",
            "spec": "fn-1",
            "title": "Mismatched id",
            "status": "todo",
            "depends_on": [],
        }
        (self.flow / "tasks" / "fn-1.2.json").write_text(
            json.dumps(bad_task), encoding="utf-8"
        )
        (self.flow / "tasks" / "fn-1.2.md").write_text(
            "## Description\n\nx\n\n## Done summary\n\nn/a\n",
            encoding="utf-8",
        )
        # Done task whose md is unreadable (chmod 000)
        self._mk_task(
            "fn-1.3",
            "fn-1",
            title="Done unreadable md",
            status="done",
            evidence={"commits": ["c"], "tests": [], "prs": []},
            updated_at="2026-06-01T00:00:00Z",
            done_summary="Should not be readable.",
        )
        self._unreadable_md = self.flow / "tasks" / "fn-1.3.md"
        self._unreadable_md.chmod(0o000)
        # Good + invalid-UTF-8 memory
        self._mk_memory("good-entry", "2026-05-01", title="Good mem")
        mem_bad = (
            self.flow
            / "memory"
            / "bug"
            / "build-errors"
            / "bad-utf8-2026-05-02.md"
        )
        mem_bad.parent.mkdir(parents=True, exist_ok=True)
        mem_bad.write_bytes(
            b'---\ntitle: "Bad"\ndate: "2026-05-02"\ntrack: bug\n'
            b"category: build-errors\nmodule: fixture\ntags: []\n---\n\n"
            b"\xff\xfe corrupt body\n"
        )

    def tearDown(self) -> None:
        try:
            self._unreadable_md.chmod(0o644)
        except OSError:
            pass
        super().tearDown()

    def test_mismatched_id_and_invalid_utf8_degrade(self) -> None:
        r = self._brief()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        md = r.stdout
        payload = self._brief_json()

        # Sibling good task still listed; mismatched id is NOT a ready row
        act = _section(md, "Actionable tasks (1)")
        self.assertIn("- [ready] fn-1.1: Good task", act)
        self.assertFalse(
            any(
                re.match(r"- \[[^\]]+\] fn-1\.2:", ln.strip())
                for ln in act.splitlines()
            )
        )
        # Consistency error surfaces as unreadable path at section end
        unreadable_tasks = payload["actionable_tasks"]["unreadable"]
        self.assertIn(".flow/tasks/fn-1.2.json", unreadable_tasks)
        self.assertTrue(
            any(
                ln.startswith("- [unreadable: ") and "fn-1.2.json" in ln
                for ln in act.splitlines()
            )
        )

        # Invalid UTF-8 goal → empty goal + inline unreadable diagnostic (R1)
        open_items = payload["open_specs"]["items"]
        self.assertEqual(len(open_items), 1)
        self.assertEqual(open_items[0]["id"], "fn-1")
        self.assertEqual(open_items[0]["goal"], "")
        self.assertIn(
            ".flow/specs/fn-1.md", payload["open_specs"]["unreadable"]
        )
        specs_body = _section(md, "Open specs (1)")
        self.assertTrue(
            any(
                ln.strip().startswith("- [unreadable: ")
                and "fn-1.md" in ln
                for ln in specs_body.splitlines()
            )
        )

        # Invalid UTF-8 memory → unreadable line; good sibling intact
        mem_body = _section(md, "Memory (1)")
        self.assertIn("good-entry-2026-05-01", mem_body)
        self.assertIn(
            ".flow/memory/bug/build-errors/bad-utf8-2026-05-02.md",
            mem_body,
        )
        self.assertIn(
            ".flow/memory/bug/build-errors/bad-utf8-2026-05-02.md",
            payload["memory"]["unreadable"],
        )

        # Unreadable task md: summary empty (skip if platform root bypasses)
        can_read = False
        try:
            self._unreadable_md.read_bytes()
            can_read = True
        except OSError:
            can_read = False
        if not can_read:
            comps = {
                c["id"]: c for c in payload["recent_completions"]["items"]
            }
            self.assertIn("fn-1.3", comps)
            self.assertEqual(comps["fn-1.3"]["summary"], "")
            # Failed summary read surfaces the inline diagnostic (R1)
            self.assertIn(
                ".flow/tasks/fn-1.3.md",
                payload["actionable_tasks"]["unreadable"],
            )


# ── 14. Evidence type strictness ──────────────────────────────────────────


class EvidenceTypeStrictnessTest(BriefRepoTestCase):
    """Non-list evidence values (string / dict) must not count as evidence."""

    def setUp(self) -> None:
        super().setUp()
        self._mk_spec("fn-1", title="E")
        self._mk_task(
            "fn-1.1",
            "fn-1",
            title="String commits",
            status="done",
            evidence={"commits": "abc123", "tests": [], "prs": []},
            updated_at="2026-01-01T00:00:00Z",
            done_summary="string commits",
        )
        self._mk_task(
            "fn-1.2",
            "fn-1",
            title="Dict tests",
            status="done",
            evidence={"commits": [], "tests": {}, "prs": []},
            updated_at="2026-01-02T00:00:00Z",
            done_summary="dict tests",
        )
        self._mk_task(
            "fn-1.3",
            "fn-1",
            title="Real list",
            status="done",
            evidence={"commits": ["abc123"], "tests": [], "prs": []},
            updated_at="2026-01-03T00:00:00Z",
            done_summary="real list",
        )

    def test_non_list_evidence_is_false(self) -> None:
        payload = self._brief_json()
        by_id = {c["id"]: c for c in payload["recent_completions"]["items"]}
        self.assertFalse(by_id["fn-1.1"]["evidence"])  # commits string
        self.assertFalse(by_id["fn-1.2"]["evidence"])  # tests dict
        self.assertTrue(by_id["fn-1.3"]["evidence"])  # commits list
        md = self._brief_md()
        body = _section(md, "Recent completions (3)")
        self.assertIn("fn-1.1: string commits [evidence=no]", body)
        self.assertIn("fn-1.2: dict tests [evidence=no]", body)
        self.assertIn("fn-1.3: real list [evidence=yes]", body)


if __name__ == "__main__":
    unittest.main()
