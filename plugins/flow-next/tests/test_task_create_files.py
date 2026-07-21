"""`task create` create-time completeness tests (fn-110.1, R2).

Pins the new create-time flags and the invariants around them:

  * `--description-file` — same normalization pipeline as set-spec's
    description path (fn-79 H2-layering: leading own-title H2 stripped,
    embedded H2 demoted to H3).
  * `--satisfies R1,R3` — strict comma-list grammar (`R[1-9][0-9]*[a-z]?`;
    empty tokens rejected, duplicates rejected, order preserved), rendered
    as `satisfies:` YAML frontmatter by the new zero-dependency renderer,
    parseable by the existing reader (`_export_parse_task_satisfies`).
  * Equivalence — a `--satisfies` create parses identically to an
    equivalent create + `set-spec --file` with a frontmatter document.
  * Byte-compat — flagless and `--acceptance-file`-only invocations write
    the exact 2.20.0 scaffold bytes.
  * Pre-write ordering — every input file is read and every flag validated
    BEFORE any task JSON/markdown is written; a failed create leaves no
    orphan files and does not consume a task number.
  * File error cases — missing file, unreadable file, directory-as-path.

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -p "test_task_create_files.py" -v
"""

from __future__ import annotations

import argparse
import concurrent.futures
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any, Optional
from unittest import mock


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_task_create_files_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class TaskCreateFilesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        subprocess.run(
            ["git", "init", "-q"], cwd=self.tmpdir, check=True, capture_output=True
        )
        self.flowctl = _load_flowctl()
        self._call(func=self.flowctl.cmd_init)
        self.spec_id = self._call(
            func=self.flowctl.cmd_spec_create, title="Create-time subject", branch=None
        )["id"]

    def tearDown(self) -> None:
        os.chdir(self.prev_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # --- helpers -------------------------------------------------------------

    def _call(self, *, func, **kwargs) -> dict:
        kwargs.setdefault("json", True)
        ns = argparse.Namespace(**kwargs)
        buf = io.StringIO()
        with redirect_stdout(buf):
            func(ns)
        out = buf.getvalue().strip()
        return json.loads(out) if out else {}

    def _create(
        self,
        title: str = "Task",
        acceptance_file: Optional[str] = None,
        description_file: Optional[str] = None,
        satisfies: Optional[str] = None,
    ) -> dict:
        return self._call(
            func=self.flowctl.cmd_task_create,
            spec=self.spec_id,
            epic=None,
            title=title,
            priority=None,
            deps=None,
            acceptance_file=acceptance_file,
            description_file=description_file,
            satisfies=satisfies,
        )

    def _create_expect_error(
        self,
        title: str = "Task",
        acceptance_file: Optional[str] = None,
        description_file: Optional[str] = None,
        satisfies: Optional[str] = None,
    ) -> str:
        ns = argparse.Namespace(
            spec=self.spec_id,
            epic=None,
            title=title,
            priority=None,
            deps=None,
            acceptance_file=acceptance_file,
            description_file=description_file,
            satisfies=satisfies,
            json=True,
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as ctx:
                self.flowctl.cmd_task_create(ns)
        self.assertNotEqual(ctx.exception.code, 0)
        return json.loads(buf.getvalue())["error"]

    def _task_md(self, task_id: str) -> str:
        return (self.tmpdir / ".flow" / "tasks" / f"{task_id}.md").read_text(
            encoding="utf-8"
        )

    def _write(self, name: str, content: str) -> str:
        path = self.tmpdir / name
        path.write_text(content, encoding="utf-8")
        return str(path)

    def _scaffold(self, task_id: str, title: str) -> str:
        """The exact 2.20.0 flagless scaffold bytes."""
        return (
            f"# {task_id} {title}\n\n"
            "## Description\nTBD\n\n"
            "## Acceptance\n- [ ] TBD\n\n"
            "## Done summary\nTBD\n\n"
            "## Evidence\n- Commits:\n- Tests:\n- PRs:\n"
        )

    # --- byte-compat regression (2.20.0) ---------------------------------------

    def test_flagless_create_byte_identical(self) -> None:
        result = self._create(title="Plain")
        self.assertEqual(
            self._task_md(result["id"]), self._scaffold(result["id"], "Plain")
        )

    def test_acceptance_only_create_byte_identical(self) -> None:
        # `--acceptance-file` pre-exists (do NOT re-register); its output must
        # stay byte-compatible: content embedded as-is, no rstrip.
        acc = self._write("acc.md", "- [ ] real criterion\n")
        result = self._create(title="AccOnly", acceptance_file=acc)
        expected = (
            f"# {result['id']} AccOnly\n\n"
            "## Description\nTBD\n\n"
            "## Acceptance\n- [ ] real criterion\n\n\n"
            "## Done summary\nTBD\n\n"
            "## Evidence\n- Commits:\n- Tests:\n- PRs:\n"
        )
        self.assertEqual(self._task_md(result["id"]), expected)

    # --- --description-file -----------------------------------------------------

    def test_description_file_written_into_section(self) -> None:
        desc = self._write("desc.md", "Do the thing.\n\nCarefully.\n")
        result = self._create(title="Desc", description_file=desc)
        md = self._task_md(result["id"])
        self.assertIn("## Description\nDo the thing.\n\nCarefully.\n\n## Acceptance", md)

    def test_description_normalization_h2_layering(self) -> None:
        # fn-79: a leading own-title H2 is stripped; embedded H2 demoted to H3.
        desc = self._write(
            "desc.md", "## Description\nBody text.\n\n## Rogue heading\nMore.\n"
        )
        result = self._create(title="Norm", description_file=desc)
        md = self._task_md(result["id"])
        self.assertIn("## Description\nBody text.\n\n### Rogue heading\nMore.", md)
        # Exactly the canonical H2 set — the rogue H2 must not become a sibling.
        h2s = [line for line in md.splitlines() if line.startswith("## ")]
        self.assertEqual(
            h2s, ["## Description", "## Acceptance", "## Done summary", "## Evidence"]
        )

    def test_empty_description_file_writes_empty_section(self) -> None:
        # Review round 1: an explicitly empty file is an intentional empty
        # section (matching `task set-spec --description`), never TBD.
        desc = self._write("empty.md", "")
        result = self._create(title="EmptyDesc", description_file=desc)
        md = self._task_md(result["id"])
        self.assertIn("## Description\n\n\n## Acceptance", md)
        self.assertNotIn("## Description\nTBD", md)

    def test_heading_only_description_file_writes_empty_section(self) -> None:
        # Normalization strips the own-title H2; nothing remains → empty
        # section, not TBD.
        desc = self._write("heading_only.md", "## Description\n")
        result = self._create(title="HeadingOnly", description_file=desc)
        md = self._task_md(result["id"])
        self.assertNotIn("## Description\nTBD", md)
        h2s = [line for line in md.splitlines() if line.startswith("## ")]
        self.assertEqual(
            h2s, ["## Description", "## Acceptance", "## Done summary", "## Evidence"]
        )

    def test_description_and_acceptance_together(self) -> None:
        desc = self._write("desc.md", "The description.\n")
        acc = self._write("acc.md", "- [ ] the criterion\n")
        result = self._create(
            title="Both", description_file=desc, acceptance_file=acc
        )
        md = self._task_md(result["id"])
        self.assertIn("## Description\nThe description.", md)
        self.assertIn("## Acceptance\n- [ ] the criterion", md)

    # --- --satisfies grammar -----------------------------------------------------

    def test_satisfies_valid_tokens_and_order_preserved(self) -> None:
        result = self._create(title="Sat", satisfies="R10, R1 ,R4a")
        md = self._task_md(result["id"])
        self.assertTrue(md.startswith("---\nsatisfies: [R10, R1, R4a]\n---\n"))
        # Round-trips through the EXISTING reader, order preserved.
        self.assertEqual(
            self.flowctl._export_parse_task_satisfies(md), ["R10", "R1", "R4a"]
        )

    def test_satisfies_invalid_tokens_rejected(self) -> None:
        for bad in ("R0", "R4A", "R4ab", "R", "r1", "R01", "x"):
            with self.subTest(bad=bad):
                err = self._create_expect_error(title="Bad", satisfies=bad)
                self.assertIn(bad, err)

    def test_satisfies_empty_token_rejected(self) -> None:
        for raw in ("R1,,R2", "R1,", "", " , R1"):
            with self.subTest(raw=raw):
                err = self._create_expect_error(title="Empty", satisfies=raw)
                self.assertIn("empty token", err)

    def test_satisfies_duplicates_rejected_not_deduped(self) -> None:
        err = self._create_expect_error(title="Dup", satisfies="R1,R2,R1")
        self.assertIn("duplicate", err)
        self.assertIn("R1", err)

    def test_parse_satisfies_tokens_unit(self) -> None:
        parse = self.flowctl.parse_satisfies_tokens
        self.assertEqual(parse("R1"), ["R1"])
        self.assertEqual(parse("R1,R10,R4a"), ["R1", "R10", "R4a"])
        self.assertEqual(parse(" R3 , R1 "), ["R3", "R1"])  # order preserved
        for bad in ("R0", "R4A", "R4ab", "R1,R1", "R1,,R2", ""):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    parse(bad)

    # --- equivalence vs create + set-spec --file ---------------------------------

    def test_satisfies_equivalent_to_set_spec_frontmatter_document(self) -> None:
        desc = self._write("desc.md", "Shared body.\n")
        via_create = self._create(
            title="ViaCreate", description_file=desc, satisfies="R1,R4a"
        )["id"]

        via_set_spec = self._create(title="ViaSetSpec")["id"]
        doc = self._write(
            "full.md",
            "---\nsatisfies: [R1, R4a]\n---\n\n"
            "## Description\nShared body.\n\n"
            "## Acceptance\n- [ ] TBD\n\n"
            "## Done summary\nTBD\n\n"
            "## Evidence\n- Commits:\n- Tests:\n- PRs:\n",
        )
        self._call(
            func=self.flowctl.cmd_task_set_spec,
            id=via_set_spec,
            file=doc,
            description=None,
            acceptance=None,
        )

        # Parsed identically by the existing reader.
        self.assertEqual(
            self.flowctl._export_parse_task_satisfies(self._task_md(via_create)),
            self.flowctl._export_parse_task_satisfies(self._task_md(via_set_spec)),
        )
        self.assertEqual(
            self.flowctl._export_parse_task_satisfies(self._task_md(via_create)),
            ["R1", "R4a"],
        )

    # --- pre-write ordering + file error cases -----------------------------------

    def _assert_no_orphan_writes(self) -> None:
        tasks_dir = self.tmpdir / ".flow" / "tasks"
        leftovers = sorted(p.name for p in tasks_dir.glob("*")) if tasks_dir.exists() else []
        self.assertEqual(leftovers, [])

    def test_missing_description_file_errors_before_write(self) -> None:
        err = self._create_expect_error(
            title="Missing", description_file=str(self.tmpdir / "nope.md")
        )
        self.assertIn("Description file missing", err)
        self._assert_no_orphan_writes()

    def test_missing_acceptance_file_errors_before_write(self) -> None:
        err = self._create_expect_error(
            title="Missing", acceptance_file=str(self.tmpdir / "nope.md")
        )
        self.assertIn("Acceptance file missing", err)
        self._assert_no_orphan_writes()

    def test_directory_as_path_errors_before_write(self) -> None:
        d = self.tmpdir / "adir"
        d.mkdir()
        err = self._create_expect_error(title="Dir", description_file=str(d))
        self.assertIn("Description file unreadable", err)
        self._assert_no_orphan_writes()

    @unittest.skipIf(os.geteuid() == 0, "chmod 000 is not enforced for root")
    def test_unreadable_file_errors_before_write(self) -> None:
        path = self.tmpdir / "locked.md"
        path.write_text("secret\n", encoding="utf-8")
        path.chmod(0o000)
        try:
            err = self._create_expect_error(
                title="Locked", description_file=str(path)
            )
            self.assertIn("Description file unreadable", err)
        finally:
            path.chmod(0o600)
        self._assert_no_orphan_writes()

    def test_invalid_satisfies_errors_before_any_write(self) -> None:
        # Even with valid files supplied, a malformed --satisfies must error
        # before either output file lands and must not consume a task number.
        desc = self._write("desc.md", "Body.\n")
        self._create_expect_error(
            title="BadSat", description_file=desc, satisfies="R1,R0"
        )
        self._assert_no_orphan_writes()
        result = self._create(title="Next")
        self.assertEqual(result["id"], f"{self.spec_id}.1")

    def test_second_publication_failure_rolls_back_first_file(self) -> None:
        real_create = self.flowctl.atomic_create
        calls = 0

        def fail_second(path: Path, content: str) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected markdown publication failure")
            real_create(path, content)

        with mock.patch.object(self.flowctl, "atomic_create", side_effect=fail_second):
            err = self._create_expect_error(title="Rollback")
        self.assertIn("injected markdown publication failure", err)
        self._assert_no_orphan_writes()
        self.assertEqual(self._create(title="Retry")["id"], f"{self.spec_id}.1")

    def test_post_link_temp_cleanup_failure_still_reports_publication(self) -> None:
        target = self.tmpdir / "published.txt"
        with mock.patch.object(
            self.flowctl.os, "unlink", side_effect=PermissionError("injected cleanup")
        ):
            self.flowctl.atomic_create(target, "complete\n")
        self.assertEqual(target.read_text(encoding="utf-8"), "complete\n")

    def test_orphan_collision_is_explicit_and_never_overwritten(self) -> None:
        tasks = self.tmpdir / ".flow" / "tasks"
        tasks.mkdir(parents=True, exist_ok=True)
        orphan = tasks / f"{self.spec_id}.1.md"
        orphan.write_text("preserve me\n", encoding="utf-8")
        err = self._create_expect_error(title="Collision")
        self.assertIn("Refusing to overwrite", err)
        self.assertEqual(orphan.read_text(encoding="utf-8"), "preserve me\n")
        self.assertFalse((tasks / f"{self.spec_id}.1.json").exists())

    def test_40_process_creators_publish_unique_matching_pairs(self) -> None:
        def create_one(index: int) -> subprocess.CompletedProcess:
            return subprocess.run(
                [
                    sys.executable,
                    str(FLOWCTL_PY),
                    "task",
                    "create",
                    "--spec",
                    self.spec_id,
                    "--title",
                    f"Concurrent {index}",
                    "--json",
                ],
                cwd=self.tmpdir,
                capture_output=True,
                text=True,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
            results = list(pool.map(create_one, range(40)))

        failures = [p.stdout + p.stderr for p in results if p.returncode != 0]
        self.assertEqual(failures, [])
        created = [json.loads(p.stdout) for p in results]
        self.assertEqual(len({item["id"] for item in created}), 40)

        tasks = self.tmpdir / ".flow" / "tasks"
        json_paths = sorted(tasks.glob(f"{self.spec_id}.*.json"))
        md_paths = sorted(tasks.glob(f"{self.spec_id}.*.md"))
        self.assertEqual(len(json_paths), 40)
        self.assertEqual(len(md_paths), 40)
        expected_ids = {f"{self.spec_id}.{i}" for i in range(1, 41)}
        self.assertEqual({p.stem for p in json_paths}, expected_ids)
        self.assertEqual({p.stem for p in md_paths}, expected_ids)

        reported_titles = {item["id"]: item["title"] for item in created}
        for task_id, title in reported_titles.items():
            data = json.loads((tasks / f"{task_id}.json").read_text(encoding="utf-8"))
            markdown = (tasks / f"{task_id}.md").read_text(encoding="utf-8")
            self.assertEqual(data["title"], title)
            self.assertTrue(markdown.startswith(f"# {task_id} {title}\n"))

    # --- partial flag combinations (each flag independent) -------------------------

    def test_partial_flag_combinations_all_valid(self) -> None:
        desc = self._write("desc.md", "D.\n")
        acc = self._write("acc.md", "- [ ] A\n")
        combos = [
            {"description_file": desc},
            {"acceptance_file": acc},
            {"satisfies": "R1"},
            {"description_file": desc, "satisfies": "R2"},
            {"acceptance_file": acc, "satisfies": "R3"},
            {"description_file": desc, "acceptance_file": acc, "satisfies": "R4"},
        ]
        for i, combo in enumerate(combos):
            with self.subTest(**combo):
                result = self._create(title=f"Combo{i}", **combo)
                md = self._task_md(result["id"])
                if "description_file" in combo:
                    self.assertIn("## Description\nD.", md)
                else:
                    self.assertIn("## Description\nTBD", md)
                if "acceptance_file" in combo:
                    self.assertIn("## Acceptance\n- [ ] A", md)
                else:
                    self.assertIn("## Acceptance\n- [ ] TBD", md)
                if "satisfies" in combo:
                    self.assertTrue(md.startswith("---\nsatisfies: ["))
                else:
                    self.assertTrue(md.startswith(f"# {result['id']}"))


if __name__ == "__main__":
    unittest.main()
