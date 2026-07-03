"""Deterministic SUPERSET test for `flowctl anchor` (fn-83.3, R8).

THE STANDING GUARDRAIL: every artifact the worker's Phase-1 re-anchor
currently reads (agents/worker.md:21-68 — show/cat task+spec, git status,
git log -5 --oneline, branch, config get memory.enabled, glossary list,
memory list index) must be present VERBATIM (byte-for-byte) — or strictly
richer — in the anchor bundle. Both arms drive the PRODUCTION CLI wire form
via subprocess (memory: test-production-path, never a parallel
construction): the expected side is the exact command the worker would run;
the actual side is the section `flowctl anchor <task-id> --json` carries.

Any future edit that filters, truncates, or paraphrases a section fails
here. Extending the worker's Phase-1 read list without extending the bundle
must be caught by updating WORKER_PHASE1_COMMANDS alongside worker.md.

Also covered: dependency enrichment (ids/titles/statuses/done-summaries,
fence-aware summary read), markdown render (fixed banner order, verbatim
content, default form), determinism (byte-identical across runs),
memory-disabled skip, short-id resolution, fail-open git sections, and the
--json/--md mutual exclusion.

Fixtures per test_plan_sync_probe.py conventions: importlib load of
flowctl.py, TemporaryDirectory + real `git init`.
"""

from __future__ import annotations

import importlib.util
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
        "flowctl_anchor_bundle_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()


SPEC_BODY = """# fn-9 Anchor fixture spec

## Overview

Fixture spec for the anchor superset test.

## Approach

Build the `anchor_bundle_gadget` in `src/gadget.py`.

## Boundaries / non-goals

- NO network calls.

## Acceptance Criteria

- **R1:** gadget built.
- **R2:** docs updated (owned by a sibling task, not fn-9.2).
"""

TASK1_BODY = """## Description

Seed dependency task.

## Acceptance

- [ ] seeded

## Done summary

Shipped the seed gadget loader.

```bash
## not a heading — fenced content must survive the fence-aware read
echo done
```

## Evidence
- Commits:
"""

TASK2_BODY = """## Description

Anchor target task.

**Files:** `src/gadget.py`

## Acceptance

- [ ] gadget built

## Done summary
TBD
"""


class AnchorRepoTestCase(unittest.TestCase):
    """Shared tmp-repo fixture: real git repo + hand-built .flow files."""

    memory_enabled = True

    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp()).resolve()
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        self._git("init", "-q")
        self._git("config", "user.email", "t@example.com")
        self._git("config", "user.name", "t")
        (self.tmpdir / ".flow" / "tasks").mkdir(parents=True)
        (self.tmpdir / ".flow" / "specs").mkdir(parents=True)
        (self.tmpdir / ".flow" / "config.json").write_text(
            json.dumps({"memory": {"enabled": self.memory_enabled}}),
            encoding="utf-8",
        )
        (self.tmpdir / "GLOSSARY.md").write_text(
            "# Glossary\n\n## Gadget\n\nThe fixture widget under test.\n\n"
            "## Anchor bundle\n\nSingle-call worker re-anchor payload.\n",
            encoding="utf-8",
        )
        self._commit("src/gadget.py", "def gadget():\n    pass\n", "seed")
        self._mk_spec("fn-9", body=SPEC_BODY)
        self._mk_task("fn-9.1", "fn-9", TASK1_BODY, title="Seed gadget loader")
        flowctl.save_task_runtime("fn-9.1", {"status": "done"})
        self._mk_task(
            "fn-9.2",
            "fn-9",
            TASK2_BODY,
            title="Build gadget",
            depends_on=["fn-9.1"],
        )
        if self.memory_enabled:
            self._seed_memory_entry()

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
            env=self._pinned_env(),
        )
        return result.stdout.strip()

    @staticmethod
    def _pinned_env() -> dict:
        env = dict(os.environ)
        env["GIT_AUTHOR_DATE"] = "2026-01-01T00:00:00Z"
        env["GIT_COMMITTER_DATE"] = "2026-01-01T00:00:00Z"
        return env

    def _commit(self, rel: str, content: str, msg: str) -> str:
        path = self.tmpdir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-qm", msg)
        return self._git("rev-parse", "HEAD")

    # ---- .flow fixture helpers ---------------------------------------

    def _mk_spec(self, spec_id: str, body: str) -> None:
        specs = self.tmpdir / ".flow" / "specs"
        (specs / f"{spec_id}.json").write_text(
            json.dumps(
                {"id": spec_id, "title": "Anchor fixture", "status": "open"}
            ),
            encoding="utf-8",
        )
        (specs / f"{spec_id}.md").write_text(body, encoding="utf-8")

    def _mk_task(
        self,
        task_id: str,
        spec_id: str,
        body: str,
        title: str = "",
        depends_on: Optional[list] = None,
    ) -> None:
        tasks = self.tmpdir / ".flow" / "tasks"
        data: dict = {
            "id": task_id,
            "spec": spec_id,
            "title": title or task_id,
        }
        if depends_on:
            data["depends_on"] = depends_on
        (tasks / f"{task_id}.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        (tasks / f"{task_id}.md").write_text(body, encoding="utf-8")

    def _seed_memory_entry(self) -> None:
        init = self._flowctl("memory", "init", "--json")
        self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
        body = self.tmpdir / "mem-body.md"
        body.write_text(
            "## Problem\nfixture\n\n## Solution\nfixture\n", encoding="utf-8"
        )
        result = self._flowctl(
            "memory",
            "add",
            "--track",
            "bug",
            "--category",
            "build-errors",
            "--title",
            "Fixture memory entry",
            "--module",
            "src/gadget.py",
            "--tags",
            "fixture",
            "--symptoms",
            "none",
            "--root-cause",
            "fixture",
            "--body-file",
            str(body),
            "--json",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        body.unlink()

    # ---- production wire-form drivers --------------------------------

    def _flowctl(self, *args: str) -> "subprocess.CompletedProcess[str]":
        """Run the production CLI wire form (exactly what the worker runs)."""
        return subprocess.run(
            [sys.executable, str(FLOWCTL_PY)] + list(args),
            cwd=str(self.tmpdir),
            capture_output=True,
            text=True,
            env=self._pinned_env(),
        )

    def _bundle(self, task_id: str = "fn-9.2") -> dict:
        result = self._flowctl("anchor", task_id, "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["success"])
        return payload

    @staticmethod
    def _sections_by_name(payload: dict) -> dict:
        return {s["name"]: s for s in payload["sections"]}


# ── The superset guardrail ────────────────────────────────────────────────

# worker.md Phase 1 read list (agents/worker.md:21-68). Update THIS table in
# the same change as any worker.md Phase-1 read-list edit — the bundle must
# stay a verbatim superset of whatever the worker reads.
WORKER_PHASE1_COMMANDS = [
    ("task_show", ("show", "fn-9.2", "--json")),
    ("task_md", ("cat", "fn-9.2")),
    ("spec_show", ("show", "fn-9", "--json")),
    ("spec_md", ("cat", "fn-9")),
    ("memory_enabled", ("config", "get", "memory.enabled", "--json")),
    ("glossary", ("glossary", "list", "--json")),
    ("memory_index", ("memory", "list", "--json")),
]

WORKER_PHASE1_GIT = [
    ("git_status", ("status",)),
    ("git_log", ("log", "-5", "--oneline")),
    ("git_branch", ("rev-parse", "--abbrev-ref", "HEAD")),
]

EXPECTED_SECTION_ORDER = [
    "task_show",
    "task_md",
    "spec_show",
    "spec_md",
    "git_status",
    "git_log",
    "git_branch",
    "memory_enabled",
    "glossary",
    "memory_index",
]


class SupersetTest(AnchorRepoTestCase):
    def test_every_worker_read_verbatim_in_bundle(self) -> None:
        """Each worker Phase-1 flowctl read == its bundle section, byte-for-byte."""
        payload = self._bundle()
        sections = self._sections_by_name(payload)
        for name, argv in WORKER_PHASE1_COMMANDS:
            with self.subTest(section=name):
                cli = self._flowctl(*argv)
                self.assertEqual(cli.returncode, 0, cli.stdout + cli.stderr)
                self.assertIn(name, sections)
                self.assertIsNone(sections[name]["error"])
                self.assertEqual(sections[name]["output"], cli.stdout)

    def test_every_worker_git_read_verbatim_in_bundle(self) -> None:
        """git status / log -5 --oneline / branch == bundle sections."""
        payload = self._bundle()
        sections = self._sections_by_name(payload)
        for name, git_argv in WORKER_PHASE1_GIT:
            with self.subTest(section=name):
                cli = subprocess.run(
                    ["git"] + list(git_argv),
                    cwd=str(self.tmpdir),
                    capture_output=True,
                    text=True,
                    check=True,
                    env=self._pinned_env(),
                )
                self.assertIsNone(sections[name]["error"])
                self.assertEqual(sections[name]["output"], cli.stdout)

    def test_section_order_fixed(self) -> None:
        payload = self._bundle()
        self.assertEqual(
            [s["name"] for s in payload["sections"]], EXPECTED_SECTION_ORDER
        )

    def test_sections_carry_their_commands(self) -> None:
        """Each section names the exact command it reproduces."""
        sections = self._sections_by_name(self._bundle())
        self.assertEqual(
            sections["task_show"]["command"], "flowctl show fn-9.2 --json"
        )
        self.assertEqual(sections["spec_md"]["command"], "flowctl cat fn-9")
        self.assertEqual(sections["git_log"]["command"], "git log -5 --oneline")

    def test_spec_body_full_no_truncation(self) -> None:
        """FULL spec body verbatim — no R-ID filtering, no truncation."""
        sections = self._sections_by_name(self._bundle())
        self.assertEqual(sections["spec_md"]["output"], SPEC_BODY + "\n")


# ── Strictly-richer: dependencies ─────────────────────────────────────────


class DependenciesTest(AnchorRepoTestCase):
    def test_dependency_ids_titles_statuses_summaries(self) -> None:
        payload = self._bundle()
        deps = payload["dependencies"]
        self.assertEqual(len(deps), 1)
        dep = deps[0]
        self.assertEqual(dep["id"], "fn-9.1")
        self.assertEqual(dep["title"], "Seed gadget loader")
        self.assertEqual(dep["status"], "done")
        self.assertIn("Shipped the seed gadget loader.", dep["done_summary"])

    def test_done_summary_read_is_fence_aware(self) -> None:
        """Fenced `## ` content inside Done summary survives (fn-79 parity)."""
        dep = self._bundle()["dependencies"][0]
        self.assertIn(
            "## not a heading — fenced content must survive", dep["done_summary"]
        )

    def test_no_dependencies_is_empty_list(self) -> None:
        payload = self._bundle("fn-9.1")
        self.assertEqual(payload["dependencies"], [])


# ── Markdown render ───────────────────────────────────────────────────────


class MarkdownRenderTest(AnchorRepoTestCase):
    def test_md_contains_every_section_verbatim(self) -> None:
        payload = self._bundle()
        md = self._flowctl("anchor", "fn-9.2", "--md")
        self.assertEqual(md.returncode, 0, md.stdout + md.stderr)
        for s in payload["sections"]:
            if s["output"] is None:
                continue
            with self.subTest(section=s["name"]):
                self.assertIn(s["output"].rstrip("\n"), md.stdout)

    def test_md_banner_order_fixed(self) -> None:
        md = self._flowctl("anchor", "fn-9.2", "--md").stdout
        positions = []
        for i, name in enumerate(EXPECTED_SECTION_ORDER, start=1):
            banner = f"===== [{i}/11] {name}:"
            self.assertIn(banner, md)
            positions.append(md.index(banner))
        deps_banner = "===== [11/11] dependencies:"
        self.assertIn(deps_banner, md)
        positions.append(md.index(deps_banner))
        self.assertEqual(positions, sorted(positions))

    def test_md_dependency_block(self) -> None:
        md = self._flowctl("anchor", "fn-9.2", "--md").stdout
        self.assertIn("- fn-9.1 [done] — Seed gadget loader", md)
        self.assertIn("Shipped the seed gadget loader.", md)

    def test_default_render_is_md(self) -> None:
        default = self._flowctl("anchor", "fn-9.2")
        explicit = self._flowctl("anchor", "fn-9.2", "--md")
        self.assertEqual(default.returncode, 0)
        self.assertEqual(default.stdout, explicit.stdout)

    def test_json_md_mutually_exclusive(self) -> None:
        result = self._flowctl("anchor", "fn-9.2", "--json", "--md")
        self.assertEqual(result.returncode, 2)


# ── Determinism ───────────────────────────────────────────────────────────


class DeterminismTest(AnchorRepoTestCase):
    def test_json_byte_identical_across_runs(self) -> None:
        a = self._flowctl("anchor", "fn-9.2", "--json").stdout
        b = self._flowctl("anchor", "fn-9.2", "--json").stdout
        self.assertEqual(a, b)

    def test_md_byte_identical_across_runs(self) -> None:
        a = self._flowctl("anchor", "fn-9.2", "--md").stdout
        b = self._flowctl("anchor", "fn-9.2", "--md").stdout
        self.assertEqual(a, b)


# ── Memory disabled ───────────────────────────────────────────────────────


class MemoryDisabledTest(AnchorRepoTestCase):
    memory_enabled = False

    def test_memory_index_skipped_with_note(self) -> None:
        payload = self._bundle()
        sections = self._sections_by_name(payload)
        idx = sections["memory_index"]
        self.assertIsNone(idx["output"])
        self.assertIsNone(idx["error"])
        self.assertIn("memory disabled", idx["note"])
        # The flag section still carries the verbatim command output.
        cli = self._flowctl("config", "get", "memory.enabled", "--json")
        self.assertEqual(sections["memory_enabled"]["output"], cli.stdout)
        self.assertFalse(json.loads(cli.stdout)["value"])

    def test_md_render_notes_the_skip(self) -> None:
        md = self._flowctl("anchor", "fn-9.2", "--md").stdout
        self.assertIn("===== [10/11] memory_index:", md)
        self.assertIn("memory disabled — skipped", md)


# ── Resolution + fail-open ────────────────────────────────────────────────


class ResolutionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp()).resolve()
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        (self.tmpdir / ".flow" / "tasks").mkdir(parents=True)
        (self.tmpdir / ".flow" / "specs").mkdir(parents=True)
        (self.tmpdir / ".flow" / "specs" / "fn-12-slugged-spec.json").write_text(
            json.dumps(
                {"id": "fn-12-slugged-spec", "title": "s", "status": "open"}
            ),
            encoding="utf-8",
        )
        (self.tmpdir / ".flow" / "specs" / "fn-12-slugged-spec.md").write_text(
            "# fn-12\n", encoding="utf-8"
        )
        (
            self.tmpdir / ".flow" / "tasks" / "fn-12-slugged-spec.1.json"
        ).write_text(
            json.dumps(
                {"id": "fn-12-slugged-spec.1", "spec": "fn-12-slugged-spec",
                 "title": "t"}
            ),
            encoding="utf-8",
        )
        (
            self.tmpdir / ".flow" / "tasks" / "fn-12-slugged-spec.1.md"
        ).write_text("## Description\n\nbody\n", encoding="utf-8")

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

    def test_short_id_resolves_to_slug_form(self) -> None:
        """`anchor fn-12.1` resolves via the existing short-id resolver."""
        result = self._flowctl("anchor", "fn-12.1", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["task"], "fn-12-slugged-spec.1")
        self.assertEqual(payload["spec"], "fn-12-slugged-spec")

    def test_invalid_task_id_errors(self) -> None:
        result = self._flowctl("anchor", "not-an-id", "--json")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(json.loads(result.stdout)["success"])

    def test_missing_task_errors(self) -> None:
        result = self._flowctl("anchor", "fn-12.9", "--json")
        self.assertNotEqual(result.returncode, 0)

    def test_git_sections_fail_open_without_repo(self) -> None:
        """No git repo: git sections carry errors, the bundle still renders."""
        result = self._flowctl("anchor", "fn-12.1", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        sections = {
            s["name"]: s for s in json.loads(result.stdout)["sections"]
        }
        # Not a git repo (or an empty one, when a parent dir is a repo):
        # either way the bundle must render with the sections present.
        for name in ("git_status", "git_log", "git_branch"):
            self.assertIn(name, sections)


if __name__ == "__main__":
    unittest.main()
