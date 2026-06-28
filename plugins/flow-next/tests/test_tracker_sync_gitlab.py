"""GitLab adapter flowctl-plumbing + ceremony-wiring tests (fn-69.1).

This task adds `tracker.type: gitlab` as a real, activatable tracker. It is
DETERMINISTIC flowctl plumbing only — the enum, the config schema defaults, and
the `set-tracker-id` identifier validator — plus the discovery-ceremony wiring
(prose in steps.md / SKILL.md, asserted by presence). No transport code lives
here (that is the gitlab.md adapter prose in fn-69.2); these tests never invoke
a live `glab`.

Asserts:
  * Activation — `tracker.type: gitlab` flips `tracker_sync_active()` true via
    the type path (R7), case-insensitively, like linear/github.
  * Config defaults — `tracker.perTracker.project` and `tracker.perTracker.host`
    exist with safe `null` defaults, paralleling GitHub's `repo` (R3).
  * Identifier validation (R4-identity) — `set-tracker-id` accepts the GitLab
    `<project>#<iid>` form INCLUDING nested `group/subgroup/project#12` plus the
    bare `#<iid>` form, and rejects `group/#12` (empty segment), `#0` (non-positive
    iid), and the existing malformed forms; the Linear handle path stays strict.
  * Ceremony wiring (R3 + R5) — steps.md / SKILL.md carry the GitLab probe row,
    the GitLab ASK option, the `tracker.type gitlab` + `perTracker.project`/`host`
    config-writes, and the readiness-label ceremony branch (pre-create +
    tolerate-already-exists). Ceremony is prose, so we assert presence/grep, not
    executable shape. The "four signals" probe wording is updated to FIVE.

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -v
"""

from __future__ import annotations

import argparse
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
from typing import Any


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"
REPO_ROOT = HERE.parents[3]
TRACKER_SKILL = REPO_ROOT / "plugins" / "flow-next" / "skills" / "flow-next-tracker-sync"
STEPS_MD = TRACKER_SKILL / "steps.md"
SKILL_MD = TRACKER_SKILL / "SKILL.md"


def _load_flowctl(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, FLOWCTL_PY)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class GitlabActivationConfigTestCase(unittest.TestCase):
    """Enum activation (R7) + config-schema defaults (R3)."""

    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        self.flowctl = _load_flowctl("flowctl_gitlab_config_under_test")
        (self.tmpdir / ".flow").mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        os.chdir(self.prev_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_config(self, data: dict) -> None:
        (self.tmpdir / ".flow" / "config.json").write_text(
            json.dumps(data), encoding="utf-8"
        )

    # --- R7: enum activation ------------------------------------------------

    def test_gitlab_in_tracker_types(self) -> None:
        self.assertIn("gitlab", self.flowctl.TRACKER_TYPES)

    def test_activation_active_for_gitlab_type(self) -> None:
        # `tracker.type: gitlab` flips sync active via the type path — like
        # linear/github, case-insensitively (the predicate lowercases).
        for ttype in ("gitlab", "GitLab", "GITLAB"):
            self._write_config({"tracker": {"enabled": False, "type": ttype}})
            self.assertTrue(
                self.flowctl.tracker_sync_active(), f"type={ttype} should activate"
            )

    # --- R3: config schema defaults -----------------------------------------

    def test_default_config_carries_gitlab_per_tracker_keys(self) -> None:
        pt = self.flowctl.get_default_config()["tracker"]["perTracker"]
        # `project` parallels GitHub's `repo` (group/project path); `host` pins a
        # self-managed base. Both default null (safe — null ⇒ resolve from glab /
        # CI_SERVER_URL, never assume gitlab.com).
        self.assertIn("project", pt)
        self.assertIsNone(pt["project"])
        self.assertIn("host", pt)
        self.assertIsNone(pt["host"])

    def test_gitlab_per_tracker_keys_resolve_via_dotted_path(self) -> None:
        # No on-disk override → merged defaults resolve the new leaves (not a
        # missing-key error).
        self.assertIsNone(self.flowctl.get_config("tracker.perTracker.project"))
        self.assertIsNone(self.flowctl.get_config("tracker.perTracker.host"))


class GitlabIdentifierValidatorTestCase(unittest.TestCase):
    """set-tracker-id identifier validation for GitLab forms (R4-identity)."""

    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        subprocess.run(
            ["git", "init", "-q"], cwd=self.tmpdir, check=True, capture_output=True
        )
        self.flowctl = _load_flowctl("flowctl_gitlab_idval_under_test")
        self._call(func=self.flowctl.cmd_init)

    def tearDown(self) -> None:
        os.chdir(self.prev_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _call(self, *, func, **kwargs) -> dict:
        kwargs.setdefault("json", True)
        ns = argparse.Namespace(**kwargs)
        buf = io.StringIO()
        with redirect_stdout(buf):
            func(ns)
        out = buf.getvalue().strip()
        return json.loads(out) if out else {}

    def _create_spec(self, title: str) -> str:
        return self._call(func=self.flowctl.cmd_spec_create, title=title, branch=None)["id"]

    def _state(self, spec_id: str) -> dict:
        return self._call(func=self.flowctl.cmd_sync_get_state, id=spec_id)["tracker"]

    def _set_id(self, spec_id: str, tracker_id: str, **kw) -> dict:
        return self._call(
            func=self.flowctl.cmd_sync_set_tracker_id,
            id=spec_id,
            tracker_id=tracker_id,
            identifier=kw.get("identifier"),
            url=kw.get("url"),
            force=kw.get("force", False),
        )

    # --- valid GitLab forms (stored display-only, not rejected) -------------

    def test_nested_group_path_identifier_accepted(self) -> None:
        # The headline GitLab widening: nested group/subgroup/project paths.
        spec_id = self._create_spec("GitLab nested ref")
        self._set_id(
            spec_id,
            "gid://gitlab/Issue/1",
            identifier="group/subgroup/project#12",
            url="https://gitlab.com/group/subgroup/project/-/issues/12",
        )
        state = self._state(spec_id)
        self.assertEqual(state["id"], "gid://gitlab/Issue/1")
        self.assertEqual(state["identifier"], "group/subgroup/project#12")

    def test_deeply_nested_group_path_identifier_accepted(self) -> None:
        spec_id = self._create_spec("GitLab deep ref")
        self._set_id(spec_id, "gid-deep", identifier="a/b/c/d#5")
        self.assertEqual(self._state(spec_id)["identifier"], "a/b/c/d#5")

    def test_single_segment_group_path_identifier_accepted(self) -> None:
        # `group/project#7` — the GitLab one-slash form (also the GitHub
        # owner/repo shape) stays accepted.
        spec_id = self._create_spec("GitLab single ref")
        self._set_id(spec_id, "gid-single", identifier="group/project#7")
        self.assertEqual(self._state(spec_id)["identifier"], "group/project#7")

    def test_bare_hash_iid_identifier_accepted(self) -> None:
        spec_id = self._create_spec("GitLab bare hash")
        self._set_id(spec_id, "gid-bare", identifier="#34")
        self.assertEqual(self._state(spec_id)["identifier"], "#34")

    # --- invalid GitLab forms (rejected) ------------------------------------

    def test_empty_trailing_segment_rejected(self) -> None:
        # `group/#12` has an empty final path segment — not a real project path.
        spec_id = self._create_spec("GitLab empty seg")
        with self.assertRaises(SystemExit):
            self._set_id(spec_id, "gid-x", identifier="group/#12")
        self.assertIsNone(self._state(spec_id)["id"])

    def test_empty_middle_segment_rejected(self) -> None:
        spec_id = self._create_spec("GitLab mid seg")
        with self.assertRaises(SystemExit):
            self._set_id(spec_id, "gid-y", identifier="group//project#5")
        self.assertIsNone(self._state(spec_id)["id"])

    def test_zero_iid_with_hash_rejected(self) -> None:
        # `#0` is not a positive issue iid (R4-identity: positive iid only).
        spec_id = self._create_spec("GitLab zero iid")
        with self.assertRaises(SystemExit):
            self._set_id(spec_id, "gid-z", identifier="#0")
        self.assertIsNone(self._state(spec_id)["id"])

    def test_zero_iid_with_path_rejected(self) -> None:
        spec_id = self._create_spec("GitLab path zero iid")
        with self.assertRaises(SystemExit):
            self._set_id(spec_id, "gid-pz", identifier="group/project#0")
        self.assertIsNone(self._state(spec_id)["id"])

    def test_leading_zero_iid_rejected(self) -> None:
        spec_id = self._create_spec("GitLab leading zero")
        with self.assertRaises(SystemExit):
            self._set_id(spec_id, "gid-lz", identifier="#01")
        self.assertIsNone(self._state(spec_id)["id"])

    # --- regressions: existing forms unchanged ------------------------------

    def test_github_owner_repo_reference_still_accepted(self) -> None:
        spec_id = self._create_spec("GH ref still ok")
        self._set_id(spec_id, "node-gh", identifier="octo/repo#7")
        self.assertEqual(self._state(spec_id)["identifier"], "octo/repo#7")

    def test_malformed_reference_still_rejected(self) -> None:
        spec_id = self._create_spec("Bad ref")
        with self.assertRaises(SystemExit):
            self._set_id(spec_id, "node-bad", identifier="#abc")
        self.assertIsNone(self._state(spec_id)["id"])

    def test_linear_handle_still_strict(self) -> None:
        spec_id = self._create_spec("Linear strict")
        with self.assertRaises(SystemExit):
            self._set_id(spec_id, "uuid-x", identifier="wor-17-slug")
        self.assertIsNone(self._state(spec_id)["id"])


class GitlabCeremonyWiringTestCase(unittest.TestCase):
    """Discovery-ceremony prose wiring (R3 + R5) — presence/grep assertions.

    The ceremony is prose the host agent executes, so we assert the GitLab
    sites are PRESENT (probe row, ASK option, config-writes, readiness branch),
    not an executable shape.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.steps = STEPS_MD.read_text(encoding="utf-8")
        cls.skill = SKILL_MD.read_text(encoding="utf-8")

    # --- probe table (R3) ---------------------------------------------------

    def test_steps_has_gitlab_probe(self) -> None:
        self.assertIn("glab auth status", self.steps)
        # The headless REST fallback signal.
        self.assertIn("GITLAB_TOKEN", self.steps)
        self.assertIn("CI_JOB_TOKEN", self.steps)

    def test_skill_probe_table_has_gitlab_row(self) -> None:
        self.assertIn("glab auth status", self.skill)
        self.assertIn("GITLAB_TOKEN", self.skill)

    def test_probe_count_wording_not_stale_four(self) -> None:
        # The PROBE-count wording grew past FOUR when GitLab landed (fn-69) and
        # again to SIX when Jira landed (fn-70). Assert it is NOT the stale
        # "four"; the EXACT count is owned by test_tracker_sync_jira (so this
        # test doesn't break each time a tracker is added). Scope the negative
        # assertion to the probe phrasing — steps.md legitimately says "four
        # signals" elsewhere about the RALPH autonomy-marker family (FLOW_RALPH /
        # REVIEW_RECEIPT_PATH / FLOW_AUTONOMOUS / mode:autonomous), which is a
        # DIFFERENT four and must stay.
        self.assertNotIn("probes four signals", self.skill)
        self.assertNotIn("Probe these four signals", self.skill)
        self.assertNotIn("Probe the four signals", self.steps)
        # GitLab is still offered regardless of the count wording.
        self.assertIn("`gitlab`", self.steps)

    # --- ASK option (R3) ----------------------------------------------------

    def test_steps_ask_offers_gitlab(self) -> None:
        # The tracker-choice question must offer gitlab alongside linear/github.
        self.assertIn("`gitlab`", self.steps)

    # --- config-write block (R3) --------------------------------------------

    def test_steps_config_write_emits_gitlab_keys(self) -> None:
        self.assertIn("tracker.perTracker.project", self.steps)
        self.assertIn("tracker.perTracker.host", self.steps)
        # tracker.type gitlab is offered as a write choice.
        self.assertIn("gitlab", self.steps)

    # --- readiness-label ceremony branch (R5) -------------------------------

    def test_steps_has_gitlab_readiness_label_branch(self) -> None:
        # A dedicated GitLab readiness branch that pre-creates the label and
        # tolerates already-exists (mirrors the GitHub branch).
        self.assertIn("POST /projects/:id/labels", self.steps)
        self.assertIn("already exists", self.steps)
        # never write readyState on a failed/unconfirmed create.
        self.assertIn("LABEL_OK", self.steps)
        self.assertIn("tracker.readyState", self.steps)


if __name__ == "__main__":
    unittest.main()
