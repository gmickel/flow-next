"""fn-134.7 / R21: ``task set-title`` + dual-rep title sync with set-spec --file.

A task title lives in exactly two places — JSON ``title`` and the markdown H1.
``task set-title`` writes both; ``task set-spec --file`` syncs JSON from the H1
so the two cannot disagree. Routes through production argparse (two-token
``task set-title`` form).
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_task_set_title_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()


class TestTaskSetTitle(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._cwd = os.getcwd()
        os.chdir(self.root)
        subprocess.run(
            ["git", "init", "-q"], cwd=self.root, check=True, capture_output=True
        )
        # Minimal flow + one task via production commands.
        code, out, err = self._run("init", "--json")
        self.assertEqual(code, 0, err or out)
        code, out, err = self._run(
            "spec", "create", "--title", "Title dual-rep fixture", "--json"
        )
        self.assertEqual(code, 0, err or out)
        self.spec_id = json.loads(out)["id"]
        code, out, err = self._run(
            "task",
            "create",
            "--spec",
            self.spec_id,
            "--title",
            "Original title",
            "--json",
        )
        self.assertEqual(code, 0, err or out)
        self.task_id = json.loads(out)["id"]

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def _run(self, *argv: str) -> "tuple[int, str, str]":
        """Invoke production argparse routing; return (code, stdout, stderr)."""
        out, err = io.StringIO(), io.StringIO()
        code = 0
        with mock.patch.object(sys, "argv", ["flowctl", *argv]):
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                try:
                    flowctl.main()
                except SystemExit as e:
                    code = int(e.code or 0)
        return code, out.getvalue(), err.getvalue()

    def _task_json(self) -> dict:
        return json.loads(
            (self.root / ".flow" / "tasks" / f"{self.task_id}.json").read_text(
                encoding="utf-8"
            )
        )

    def _task_md(self) -> str:
        return (self.root / ".flow" / "tasks" / f"{self.task_id}.md").read_text(
            encoding="utf-8"
        )

    def _h1_title(self) -> str:
        for line in self._task_md().splitlines():
            if line.startswith("# "):
                body = line[2:].strip()
                prefix = f"{self.task_id} "
                self.assertTrue(body.startswith(prefix), body)
                return body[len(prefix) :]
        self.fail("no H1 in task markdown")
        return ""

    def test_set_title_updates_json_and_markdown_h1(self) -> None:
        """Production two-token form updates both representations."""
        code, out, err = self._run(
            "task",
            "set-title",
            self.task_id,
            "--title",
            "Renamed mid-review",
            "--json",
        )
        self.assertEqual(code, 0, err or out)
        payload = json.loads(out)
        self.assertEqual(payload["id"], self.task_id)
        self.assertEqual(payload["title"], "Renamed mid-review")
        self.assertEqual(self._task_json()["title"], "Renamed mid-review")
        self.assertEqual(self._h1_title(), "Renamed mid-review")

    def test_set_spec_file_syncs_json_title_from_h1(self) -> None:
        """``set-spec --file`` must not leave JSON title and H1 disagreeing."""
        new_body = (
            f"# {self.task_id} Title from full file replace\n\n"
            "## Description\nReplaced body\n\n"
            "## Acceptance\n- [ ] one\n\n"
            "## Done summary\nTBD\n\n"
            "## Evidence\n- Commits:\n- Tests:\n- PRs:\n"
        )
        path = self.root / "replacement.md"
        path.write_text(new_body, encoding="utf-8")
        code, out, err = self._run(
            "task", "set-spec", self.task_id, "--file", str(path), "--json"
        )
        self.assertEqual(code, 0, err or out)
        self.assertEqual(self._task_json()["title"], "Title from full file replace")
        self.assertEqual(self._h1_title(), "Title from full file replace")
        # After a subsequent set-title both still agree.
        code, out, err = self._run(
            "task",
            "set-title",
            self.task_id,
            "--title",
            "After set-spec",
            "--json",
        )
        self.assertEqual(code, 0, err or out)
        self.assertEqual(self._task_json()["title"], "After set-spec")
        self.assertEqual(self._h1_title(), "After set-spec")

    def test_set_spec_file_missing_h1_pins_from_json(self) -> None:
        """Missing H1: rewrite from JSON title so dual-rep stays agreed."""
        path = self.root / "no-h1.md"
        path.write_text(
            "## Description\nno h1\n\n## Acceptance\n- [ ] x\n\n"
            "## Done summary\nTBD\n\n## Evidence\n- Commits:\n",
            encoding="utf-8",
        )
        before = self._task_json()["title"]
        code, out, err = self._run(
            "task", "set-spec", self.task_id, "--file", str(path), "--json"
        )
        self.assertEqual(code, 0, err or out)
        self.assertEqual(self._task_json()["title"], before)
        self.assertEqual(self._h1_title(), before)

    def test_set_title_empty_rejected(self) -> None:
        code, out, err = self._run(
            "task", "set-title", self.task_id, "--title", "   ", "--json"
        )
        self.assertNotEqual(code, 0)
        self.assertIn("non-empty", out + err)


class TaskH1LookupIsFenceAware(unittest.TestCase):
    """A `# <task-id> ...` line inside a fenced block is not the H1.

    Found by PR review on #241. Task bodies routinely open with a shell block
    whose comments start with `#`. Treating one as the H1 syncs the JSON title
    from an example and leaves the real heading alone - reintroducing exactly
    the JSON/markdown divergence `task set-title` exists to prevent.
    """

    TASK_ID = "fn-9-demo.1"

    def _body(self, real_title: str) -> str:
        return (
            "```bash\n"
            f"# {self.TASK_ID} example invocation from the docs\n"
            "flowctl show " + self.TASK_ID + "\n"
            "```\n"
            "\n"
            f"# {self.TASK_ID} {real_title}\n"
            "\n"
            "Body text.\n"
        )

    def test_title_comes_from_the_real_h1_not_the_fenced_comment(self) -> None:
        got = flowctl._task_h1_title(self._body("The real title"), self.TASK_ID)
        self.assertEqual(got, "The real title")

    def test_rewrite_targets_the_real_h1_and_preserves_the_fence(self) -> None:
        out = flowctl._task_rewrite_h1(self._body("Old title"), self.TASK_ID, "New title")
        self.assertIn(f"# {self.TASK_ID} New title", out)
        self.assertIn(
            f"# {self.TASK_ID} example invocation from the docs", out,
            "the fenced example must not be rewritten",
        )
        self.assertNotIn("Old title", out)
        self.assertEqual(out.count(f"# {self.TASK_ID} New title"), 1)


    def test_indented_code_comment_is_not_the_h1(self) -> None:
        """Indented code is markdown code too (PR #241 follow-up).

        The first fence-aware fix still called `line.strip()`, so a 4-space
        indented `    # <id> example` block was read as the heading. The marker
        must be at column zero.
        """
        body = (
            "    # " + self.TASK_ID + " example from an indented block\n"
            "\n"
            "# " + self.TASK_ID + " The real title\n"
        )
        self.assertEqual(flowctl._task_h1_title(body, self.TASK_ID), "The real title")
        out = flowctl._task_rewrite_h1(body, self.TASK_ID, "Renamed")
        self.assertIn("    # " + self.TASK_ID + " example from an indented block", out)
        self.assertIn("# " + self.TASK_ID + " Renamed", out)


    def test_yaml_frontmatter_comment_is_not_the_h1(self) -> None:
        """Frontmatter is the third H1 look-alike (PR #241 wave 3)."""
        body = (
            "---\n"
            "satisfies: [R1]\n"
            "# " + self.TASK_ID + " metadata example\n"
            "---\n"
            "\n"
            "# " + self.TASK_ID + " The real title\n"
        )
        self.assertEqual(flowctl._task_h1_title(body, self.TASK_ID), "The real title")
        out = flowctl._task_rewrite_h1(body, self.TASK_ID, "Renamed")
        self.assertIn("# " + self.TASK_ID + " metadata example", out)
        self.assertIn("# " + self.TASK_ID + " Renamed", out)
        self.assertNotIn("The real title", out)

    def test_all_three_lookalikes_together(self) -> None:
        """Frontmatter + fenced + indented in one body, real H1 last."""
        body = (
            "---\n"
            "# " + self.TASK_ID + " frontmatter\n"
            "---\n"
            "```bash\n"
            "# " + self.TASK_ID + " fenced\n"
            "```\n"
            "    # " + self.TASK_ID + " indented\n"
            "\n"
            "# " + self.TASK_ID + " Actual heading\n"
        )
        self.assertEqual(flowctl._task_h1_title(body, self.TASK_ID), "Actual heading")
        out = flowctl._task_rewrite_h1(body, self.TASK_ID, "Final")
        for survivor in ("frontmatter", "fenced", "indented"):
            self.assertIn("# " + self.TASK_ID + " " + survivor, out)
        self.assertEqual(out.count("# " + self.TASK_ID + " Final"), 1)


    def test_unmatched_fence_in_frontmatter_does_not_hide_the_h1(self) -> None:
        """Frontmatter is YAML, not markdown (PR #241 wave 13).

        A stray fence marker inside a block scalar must not leak fence state
        into the body and hide the real heading.
        """
        body = (
            "---\n"
            "note: |\n"
            "    ```\n"
            "---\n"
            "\n"
            "# " + self.TASK_ID + " The real title\n"
        )
        self.assertEqual(flowctl._task_h1_title(body, self.TASK_ID), "The real title")
        out = flowctl._task_rewrite_h1(body, self.TASK_ID, "Renamed")
        self.assertIn("# " + self.TASK_ID + " Renamed", out)


    def test_indented_delimiter_does_not_close_frontmatter(self) -> None:
        """An indented `---` in a block scalar is content (PR #241 wave 14)."""
        body = (
            "---\n"
            "note: |\n"
            "    ---\n"
            "    # " + self.TASK_ID + " decoy inside the scalar\n"
            "---\n"
            "\n"
            "# " + self.TASK_ID + " The real title\n"
        )
        self.assertEqual(flowctl._task_h1_title(body, self.TASK_ID), "The real title")


    def test_insert_path_respects_column_zero_delimiters(self) -> None:
        """The INSERT branch had its own delimiter check (PR #241 wave 15).

        An indented `---` in a block scalar must not be read as the close, or
        the heading is inserted INTO the frontmatter.
        """
        body = "---\nnote: |\n    ---\n    still scalar\n---\n\nBody text.\n"
        out = flowctl._task_rewrite_h1(body, self.TASK_ID, "Inserted")
        head, _, tail = out.partition("# " + self.TASK_ID + " Inserted")
        self.assertEqual(head.count("\n---\n"), 1, "heading landed inside the frontmatter")
        self.assertIn("still scalar", head)
        self.assertIn("Body text.", tail)


    def test_bare_cr_line_endings_are_understood(self) -> None:
        """Bare CR is a valid Markdown line ending (PR #241 wave 16).

        Splitting on "\\n" alone treated a CR-delimited file as one line, so the
        fenced decoy was not skipped and the real heading was not found.
        """
        cr = "```\r# " + self.TASK_ID + " decoy\r```\r\r# " + self.TASK_ID + " Real\r"
        self.assertEqual(flowctl._task_h1_title(cr, self.TASK_ID), "Real")
        self.assertEqual(
            flowctl._task_h1_title("# " + self.TASK_ID + " Plain\r\rbody\r", self.TASK_ID),
            "Plain",
        )


    def test_rewrite_preserves_the_original_line_terminator(self) -> None:
        """Bare CR / CRLF must survive the rewrite (PR #241 wave 17)."""
        for term in ("\r", "\n", "\r\n"):
            with self.subTest(terminator=repr(term)):
                body = "# " + self.TASK_ID + " Old" + term + "body" + term
                out = flowctl._task_rewrite_h1(body, self.TASK_ID, "New")
                self.assertEqual(out, "# " + self.TASK_ID + " New" + term + "body" + term)

    def test_unfenced_h1_still_works(self) -> None:
        plain = f"# {self.TASK_ID} Plain title\n\nBody.\n"
        self.assertEqual(flowctl._task_h1_title(plain, self.TASK_ID), "Plain title")


class TaskTitleRejectsMultiline(unittest.TestCase):
    """A newline splits the two representations set-title exists to keep together.

    PR #241 wave 11: `New\\nInjected` wrote `New` into the H1 while the JSON kept
    the whole string, so they disagreed immediately.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        run = lambda *a: subprocess.run(
            [sys.executable, str(FLOWCTL_PY), *a],
            cwd=str(self.repo), capture_output=True, text=True, check=False)
        run("init")
        spec_id = json.loads(run("spec", "create", "--title", "S", "--json").stdout)["id"]
        self.task_id = json.loads(
            run("task", "create", "--spec", spec_id, "--title", "T", "--json").stdout
        )["id"]

    def tearDown(self) -> None:
        self._tmp.cleanup()


    def test_task_create_also_rejects_multiline(self) -> None:
        """Guarding only set-title left the bad state reachable one command earlier."""
        r = subprocess.run(
            [sys.executable, str(FLOWCTL_PY), "task", "create",
             "--spec", self.task_id.rsplit(".", 1)[0], "--title", "New\nInjected"],
            cwd=str(self.repo), capture_output=True, text=True, check=False,
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("single line", (r.stdout + r.stderr).lower())

    def test_embedded_newline_is_rejected(self) -> None:
        r = subprocess.run(
            [sys.executable, str(FLOWCTL_PY), "task", "set-title", self.task_id,
             "--title", "New\nInjected"],
            cwd=str(self.repo), capture_output=True, text=True, check=False,
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("single line", (r.stdout + r.stderr).lower())
        self.assertNotIn("Traceback", r.stderr)


if __name__ == "__main__":
    unittest.main()
