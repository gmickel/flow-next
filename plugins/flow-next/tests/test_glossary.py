"""Changed-path and batched-object tests for cognitive-aid glossary diffs."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "plugins" / "flow-next" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import flowctl  # noqa: E402


def _git(cwd: Path, *args: str) -> str:
    env = dict(os.environ)
    env.update(
        {
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t.co",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t.co",
        }
    )
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def _entry(term: str, definition: str) -> str:
    return f"# Project Glossary\n\n## {term}\n\n{definition}\n"


class TestChangedGlossaryDiff(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _git(self.root, "init", "-q")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _commit(self, message: str) -> str:
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-qm", message)
        return _git(self.root, "rev-parse", "HEAD").strip()

    def _diff(self, base: str) -> dict:
        status = _git(self.root, "diff", "--name-status", "-M", f"{base}..HEAD")
        return flowctl._export_glossary_diff(
            base,
            self.root,
            name_status=status,
            name_status_rc=0,
        )

    def test_add_delete_and_rename_payloads_match_legacy_order(self) -> None:
        self._write("keep.txt", "base\n")
        base = self._commit("base")

        self._write("added/GLOSSARY.md", _entry("Added", "Added definition."))
        self._commit("add glossary")
        self.assertEqual(
            json.dumps(self._diff(base), separators=(",", ":")),
            '{"added":[{"term":"Added","definition_first_sentence":"Added definition."}],"removed":[],"renamed":[]}',
        )

        # A rename is intentionally represented as removal at the old glossary
        # path plus addition at the new path, preserving the pre-fn-122 union.
        rename_base = _git(self.root, "rev-parse", "HEAD").strip()
        (self.root / "added/GLOSSARY.md").rename(self.root / "GLOSSARY.md")
        self._commit("rename glossary")
        self.assertEqual(
            json.dumps(self._diff(rename_base), separators=(",", ":")),
            '{"added":[{"term":"Added","definition_first_sentence":"Added definition."}],"removed":["Added"],"renamed":[]}',
        )

        delete_base = _git(self.root, "rev-parse", "HEAD").strip()
        (self.root / "GLOSSARY.md").unlink()
        self._commit("delete glossary")
        self.assertEqual(
            json.dumps(self._diff(delete_base), separators=(",", ":")),
            '{"added":[],"removed":["Added"],"renamed":[]}',
        )

    def test_multiple_changed_glossaries_use_one_base_object_process(self) -> None:
        self._write("a/GLOSSARY.md", _entry("Alpha", "Old alpha."))
        self._write("b/GLOSSARY.md", _entry("Beta", "Old beta."))
        base = self._commit("base")
        self._write("a/GLOSSARY.md", _entry("Alpha Two", "New alpha."))
        self._write("b/GLOSSARY.md", _entry("Beta Two", "New beta."))
        self._commit("change both")
        status = _git(self.root, "diff", "--name-status", "-M", f"{base}..HEAD")

        real_run = subprocess.run
        cat_file_calls = []

        def counting_run(args, *run_args, **kwargs):
            if list(args[:3]) == ["git", "cat-file", "--batch"]:
                cat_file_calls.append(list(args))
            return real_run(args, *run_args, **kwargs)

        with mock.patch.object(flowctl.subprocess, "run", side_effect=counting_run):
            result = flowctl._export_glossary_diff(
                base, self.root, status, 0
            )
        self.assertEqual(len(cat_file_calls), 1)
        self.assertEqual([x["term"] for x in result["added"]], ["Alpha Two", "Beta Two"])
        self.assertEqual(result["removed"], ["Alpha", "Beta"])

    def test_unchanged_and_protected_glossaries_do_no_object_reads(self) -> None:
        status = (
            "M\tREADME.md\n"
            "A\tnode_modules/pkg/GLOSSARY.md\n"
            "A\tplugins/flow-next/codex/GLOSSARY.md\n"
            "A\t.flow/memory/GLOSSARY.md\n"
        )
        with mock.patch.object(
            flowctl, "_export_read_base_blobs", side_effect=AssertionError("called")
        ):
            result = flowctl._export_glossary_diff(
                "base", self.root, status, 0
            )
        self.assertEqual(result, {"added": [], "removed": [], "renamed": []})


if __name__ == "__main__":
    unittest.main()
