"""Jira adapter flowctl-plumbing + ceremony-wiring tests (fn-70.1).

This task adds `tracker.type: jira` as a real, activatable tracker. It is
DETERMINISTIC flowctl plumbing only — the activation enum, the `perTracker`
config schema (`baseUrl`/`projectKey`/`authScheme`/`apiVersion`/`sslVerify`/
`statusMap`), and the `set-tracker-id` identifier validator (Jira keys are the
existing `KEY-N` form, so this is regression coverage + error-text, NOT a
rewrite) — plus the discovery-ceremony wiring (prose in steps.md / SKILL.md,
asserted by presence) and the receipt-transport `rest` token. No Jira transport
code lives here (that is the jira.md adapter prose in fn-70.2/.3); these tests
never invoke a live Jira REST API.

Asserts:
  * Activation (R7) — `tracker.type: jira` flips `tracker_sync_active()` true via
    the type path, case-insensitively, like linear/github/gitlab.
  * Config defaults (R8) — `tracker.perTracker` carries `baseUrl`/`projectKey`/
    `authScheme`/`apiVersion`/`sslVerify`/`statusMap` with safe defaults.
  * Identifier validation (R6-identity) — `set-tracker-id` accepts Jira
    `PROJ-123` / bare `proj-123` (the `KEY-N` form), preserving GitHub `#N` and
    the reserved-`fn` guard; the Linear handle path stays strict.
  * Resolver END-TO-END (R6-identity, fn-69 scar: a green validator ≠ a working
    resolver) — `flowctl show PROJ-123` AND the `work`/`start PROJ-123.M` command
    surface actually resolve to the linked spec, not just the validator.
  * Tracker-first (R6-identity) — `spec create --tracker-first
    --tracker-identifier PROJ-123` mints a clean `proj-123-slug` (Jira IS
    `KEY-N` like Linear; BOTH entry flows work).
  * Receipt transport (R2) — `sync receipt --transport rest` round-trips
    (free-form; `rest` accepted).
  * Ceremony wiring (R5) — steps.md / SKILL.md carry the Jira probe row, the
    Jira ASK option, the `tracker.type jira` + `perTracker` config-writes, and
    the Jira readiness branch. Ceremony is prose, so presence/grep, not shape.
    The probe-count wording reads SIX.

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


class JiraActivationConfigTestCase(unittest.TestCase):
    """Enum activation (R7) + config-schema defaults (R8)."""

    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        self.flowctl = _load_flowctl("flowctl_jira_config_under_test")
        (self.tmpdir / ".flow").mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        os.chdir(self.prev_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_config(self, data: dict) -> None:
        (self.tmpdir / ".flow" / "config.json").write_text(
            json.dumps(data), encoding="utf-8"
        )

    # --- R7: enum activation ------------------------------------------------

    def test_jira_in_tracker_types(self) -> None:
        self.assertIn("jira", self.flowctl.TRACKER_TYPES)

    def test_activation_active_for_jira_type(self) -> None:
        # `tracker.type: jira` flips sync active via the type path — like
        # linear/github/gitlab, case-insensitively (the predicate lowercases).
        for ttype in ("jira", "Jira", "JIRA"):
            self._write_config({"tracker": {"enabled": False, "type": ttype}})
            self.assertTrue(
                self.flowctl.tracker_sync_active(), f"type={ttype} should activate"
            )

    # --- R8: config schema defaults -----------------------------------------

    def test_default_config_carries_jira_per_tracker_keys(self) -> None:
        pt = self.flowctl.get_default_config()["tracker"]["perTracker"]
        # site base + project key default null (env/ceremony fill them).
        self.assertIn("baseUrl", pt)
        self.assertIsNone(pt["baseUrl"])
        self.assertIn("projectKey", pt)
        self.assertIsNone(pt["projectKey"])
        # auth scheme + api version persist the ceremony's deployment decision;
        # null until the ceremony detects + writes them.
        self.assertIn("authScheme", pt)
        self.assertIsNone(pt["authScheme"])
        self.assertIn("apiVersion", pt)
        self.assertIsNone(pt["apiVersion"])
        # sslVerify defaults TRUE (opt-in false for self-hosted internal-CA).
        self.assertIn("sslVerify", pt)
        self.assertTrue(pt["sslVerify"])
        # statusMap defaults to an empty dict (normalized status → Jira name/id).
        self.assertIn("statusMap", pt)
        self.assertEqual(pt["statusMap"], {})

    def test_jira_per_tracker_keys_resolve_via_dotted_path(self) -> None:
        # No on-disk override → merged defaults resolve the new leaves (not a
        # missing-key error). NOTE: `get_config` collapses an empty-dict leaf to
        # the `default` (None) — pre-existing behavior shared by `labelMap` /
        # `priorityMap` — so `statusMap` reads None via the dotted path while its
        # `{}` default lives in get_default_config() (asserted above). The scalar
        # leaves resolve to their literal defaults.
        self.assertIsNone(self.flowctl.get_config("tracker.perTracker.baseUrl"))
        self.assertIsNone(self.flowctl.get_config("tracker.perTracker.projectKey"))
        self.assertIsNone(self.flowctl.get_config("tracker.perTracker.authScheme"))
        self.assertIsNone(self.flowctl.get_config("tracker.perTracker.apiVersion"))
        self.assertTrue(self.flowctl.get_config("tracker.perTracker.sslVerify"))
        # Empty-dict leaf reads None via get_config (same as labelMap/priorityMap).
        self.assertIsNone(self.flowctl.get_config("tracker.perTracker.statusMap"))
        self.assertIsNone(self.flowctl.get_config("tracker.perTracker.labelMap"))


class JiraIdentifierValidatorTestCase(unittest.TestCase):
    """set-tracker-id identifier validation for Jira keys (R6-identity).

    Jira keys ARE the existing strict `KEY-N` form (`PROJ-123`), so this is
    regression coverage that they pass + the GitHub/reserved guards stay intact —
    NOT a validator rewrite.
    """

    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        subprocess.run(
            ["git", "init", "-q"], cwd=self.tmpdir, check=True, capture_output=True
        )
        self.flowctl = _load_flowctl("flowctl_jira_idval_under_test")
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

    # --- valid Jira KEY-N forms (stored as a resolvable display alias) -------

    def test_jira_key_identifier_accepted(self) -> None:
        # The headline: a Jira issue key stored as a resolvable display alias.
        spec_id = self._create_spec("Jira key")
        self._set_id(
            spec_id,
            "10042",  # immutable Jira issue id (durable dedupe key)
            identifier="PROJ-123",
            url="https://acme.atlassian.net/browse/PROJ-123",
        )
        state = self._state(spec_id)
        self.assertEqual(state["id"], "10042")
        # Persists the canonical STRIPPED display form (case preserved).
        self.assertEqual(state["identifier"], "PROJ-123")

    def test_jira_lowercase_key_identifier_accepted(self) -> None:
        # Bare lowercase `proj-123` is the same KEY-N form (resolution folds case).
        spec_id = self._create_spec("Jira lc key")
        self._set_id(spec_id, "10043", identifier="proj-123")
        self.assertEqual(self._state(spec_id)["identifier"], "proj-123")

    def test_jira_quoted_whitespace_stripped(self) -> None:
        # Validator returns the STRIPPED display form so the stored alias resolves.
        spec_id = self._create_spec("Jira ws")
        self._set_id(spec_id, "10044", identifier="  PROJ-7  ")
        self.assertEqual(self._state(spec_id)["identifier"], "PROJ-7")

    # --- invalid forms (rejected) -------------------------------------------

    def test_jira_zero_number_rejected(self) -> None:
        # `PROJ-0` is not a positive issue number.
        spec_id = self._create_spec("Jira zero")
        with self.assertRaises(SystemExit):
            self._set_id(spec_id, "j-z", identifier="PROJ-0")
        self.assertIsNone(self._state(spec_id)["id"])

    def test_jira_leading_zero_rejected(self) -> None:
        spec_id = self._create_spec("Jira leading zero")
        with self.assertRaises(SystemExit):
            self._set_id(spec_id, "j-lz", identifier="PROJ-007")
        self.assertIsNone(self._state(spec_id)["id"])

    def test_jira_slugged_key_rejected(self) -> None:
        # A slugged form is the resolver grammar, not a bare display key.
        spec_id = self._create_spec("Jira slug")
        with self.assertRaises(SystemExit):
            self._set_id(spec_id, "j-s", identifier="proj-123-fix")
        self.assertIsNone(self._state(spec_id)["id"])

    def test_jira_reserved_fn_key_rejected(self) -> None:
        # `FN-1` lowercases to key `fn`, which shadows the native scheme.
        spec_id = self._create_spec("Jira reserved")
        with self.assertRaises(SystemExit):
            self._set_id(spec_id, "j-fn", identifier="FN-1")
        self.assertIsNone(self._state(spec_id)["id"])

    # --- regressions: existing forms unchanged ------------------------------

    def test_github_reference_still_accepted(self) -> None:
        spec_id = self._create_spec("GH ref still ok")
        self._set_id(spec_id, "node-gh", identifier="#7")
        self.assertEqual(self._state(spec_id)["identifier"], "#7")

    def test_linear_handle_still_accepted(self) -> None:
        spec_id = self._create_spec("Linear still ok")
        self._set_id(spec_id, "uuid-wor", identifier="WOR-17")
        self.assertEqual(self._state(spec_id)["identifier"], "WOR-17")

    def test_malformed_reference_still_rejected(self) -> None:
        spec_id = self._create_spec("Bad ref")
        with self.assertRaises(SystemExit):
            self._set_id(spec_id, "node-bad", identifier="#abc")
        self.assertIsNone(self._state(spec_id)["id"])


class JiraResolverEndToEndTestCase(unittest.TestCase):
    """Resolver END-TO-END (R6-identity) — a green validator is NOT proof.

    fn-69 scar: GitLab `group/project#12` was ASSUMED to resolve and did NOT
    (`resolve_spec_id_arg`/`parse_any_id` accept only `fn-*` / `KEY-N`). A Jira
    key `PROJ-123` IS a `KEY-N`, so it SHOULD resolve like `WOR-17` — but we
    PROVE it through the real command surface (`show`, `start`, `resolve_task_arg`)
    rather than asserting it in prose.
    """

    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        subprocess.run(
            ["git", "init", "-q"], cwd=self.tmpdir, check=True, capture_output=True
        )
        self.flowctl = _load_flowctl("flowctl_jira_resolver_under_test")
        self.flow_dir = self.tmpdir / ".flow"
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

    def _create_tracker_spec(self, title: str, identifier: str) -> str:
        return self._call(
            func=self.flowctl.cmd_spec_create,
            title=title,
            branch=None,
            tracker_first=True,
            tracker_identifier=identifier,
        )["id"]

    def _add_task(self, spec_id: str, title: str) -> str:
        return self._call(
            func=self.flowctl.cmd_task_create,
            spec=spec_id,
            epic=None,
            title=title,
            deps=None,
            priority=None,
            acceptance_file=None,
        )["id"]

    # --- tracker-first mint (R6-identity) -----------------------------------

    def test_tracker_first_mints_clean_slug(self) -> None:
        # Jira IS KEY-N → tracker-first like Linear: `PROJ-123` mints a clean
        # `proj-123-...` canonical id (alnum-`-num`, no slugify hazard).
        canonical = self._create_tracker_spec("Fix login", "PROJ-123")
        self.assertTrue(
            canonical.startswith("proj-123-"),
            f"expected proj-123- canonical id, got {canonical!r}",
        )
        # The mint is the proof a Jira key is tracker-first capable (not just a
        # link-time display ref like GitHub/GitLab).
        self.assertNotIn("#", canonical)

    # --- SPEC resolution end-to-end -----------------------------------------

    def test_bare_handle_resolves_canonical(self) -> None:
        canonical = self._create_tracker_spec("Fix login", "PROJ-123")
        self.assertEqual(
            self.flowctl.expand_bare_spec_id(self.flow_dir, "proj-123"), canonical
        )

    def test_show_via_jira_key_uppercase(self) -> None:
        # The real `flowctl show PROJ-123` surface — uppercase, case-folded.
        canonical = self._create_tracker_spec("Fix login", "PROJ-123")
        res = self._call(func=self.flowctl.cmd_show, id="PROJ-123")
        self.assertEqual(res["id"], canonical)

    def test_show_via_jira_key_lowercase(self) -> None:
        canonical = self._create_tracker_spec("Fix login", "PROJ-123")
        res = self._call(func=self.flowctl.cmd_show, id="proj-123")
        self.assertEqual(res["id"], canonical)

    # --- TASK resolution end-to-end (the work/start command surface) --------

    def test_task_alias_canonicalizes(self) -> None:
        spec_id = self._create_tracker_spec("Fix login", "PROJ-123")
        self._add_task(spec_id, "Step one")
        # resolve_task_arg is what `work`/`start` route the task id through.
        self.assertEqual(
            self.flowctl.resolve_task_arg(self.flow_dir, "PROJ-123.1"),
            f"{spec_id}.1",
        )

    def test_start_via_jira_task_alias(self) -> None:
        # `work PROJ-123.M` / `start PROJ-123.M` — the REAL resolver command
        # surface (fn-69 scar). Prove it claims the linked spec's task, not just
        # that the validator was green.
        spec_id = self._create_tracker_spec("Fix login", "PROJ-123")
        self._add_task(spec_id, "Step one")
        started = self._call(
            func=self.flowctl.cmd_start, id="PROJ-123.1", note=None, force=False
        )
        self.assertEqual(started["status"], "in_progress")
        # The alias-driven write landed on the canonical task.
        shown = self._call(func=self.flowctl.cmd_show, id=f"{spec_id}.1")
        self.assertEqual(shown["status"], "in_progress")


class JiraReceiptTransportTestCase(unittest.TestCase):
    """`sync receipt --transport rest` round-trips (R2).

    `--transport` is free-form (no `choices`), so `rest` is accepted; assert it
    survives into the written receipt JSON (the Jira REST transport label).
    """

    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        subprocess.run(
            ["git", "init", "-q"], cwd=self.tmpdir, check=True, capture_output=True
        )
        self.flowctl = _load_flowctl("flowctl_jira_receipt_under_test")
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

    def test_receipt_accepts_rest_transport(self) -> None:
        spec_id = self._call(
            func=self.flowctl.cmd_spec_create, title="Jira receipt", branch=None
        )["id"]
        res = self._call(
            func=self.flowctl.cmd_sync_receipt,
            id=spec_id,
            status="pushed",
            transport="rest",
            tracker_id=None,
            event=None,
            note=None,
            merges_file=None,
        )
        receipt_path = Path(res["receipt"])
        self.assertTrue(receipt_path.exists())
        written = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(written["transport"], "rest")


class JiraCeremonyWiringTestCase(unittest.TestCase):
    """Discovery-ceremony prose wiring (R5) — presence/grep assertions.

    The ceremony is prose the host agent executes, so we assert the Jira sites
    are PRESENT (probe row, ASK option, config-writes, readiness branch), not an
    executable shape.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.steps = STEPS_MD.read_text(encoding="utf-8")
        cls.skill = SKILL_MD.read_text(encoding="utf-8")

    # --- probe table (R5) ---------------------------------------------------

    def test_steps_has_jira_rest_probe(self) -> None:
        # The REST signal: JIRA_BASE_URL + Cloud (email+api token) OR DC PAT.
        self.assertIn("JIRA_BASE_URL", self.steps)
        self.assertIn("JIRA_API_TOKEN", self.steps)
        self.assertIn("JIRA_EMAIL", self.steps)
        self.assertIn("JIRA_PAT", self.steps)

    def test_steps_jira_probe_has_no_mcp(self) -> None:
        # Jira is REST-only — the probe must explicitly say NO MCP (fn-70 decision).
        self.assertIn("NO MCP", self.steps)

    def test_skill_probe_table_has_jira_rest_row(self) -> None:
        self.assertIn("JIRA_BASE_URL", self.skill)
        self.assertIn("Jira REST", self.skill)
        # The old "out of scope / surface but don't offer" framing is gone.
        self.assertNotIn("out of scope here — surface but don't offer", self.skill)

    def test_probe_count_wording_updated_to_six(self) -> None:
        # The PROBE-count wording must read SIX (Linear MCP, LINEAR_API_KEY,
        # GitHub, GitLab, Jira REST). Scope the negative assertion to the probe
        # phrasing — steps.md legitimately says "four signals" elsewhere about
        # the RALPH autonomy-marker family, which is a DIFFERENT four and stays.
        self.assertIn("probes six signals", self.skill)
        self.assertIn("Probe these six signals", self.skill)
        self.assertIn("Probe the six signals", self.steps)
        self.assertNotIn("probes five signals", self.skill)
        self.assertNotIn("Probe these five signals", self.skill)
        self.assertNotIn("Probe the five signals", self.steps)

    # --- ASK option (R5) ----------------------------------------------------

    def test_steps_ask_offers_jira(self) -> None:
        # The tracker-choice question must offer jira alongside the others.
        self.assertIn("`jira`", self.steps)

    # --- config-write block (R5) --------------------------------------------

    def test_steps_config_write_emits_jira_keys(self) -> None:
        self.assertIn("tracker.perTracker.baseUrl", self.steps)
        self.assertIn("tracker.perTracker.projectKey", self.steps)
        self.assertIn("tracker.perTracker.authScheme", self.steps)
        self.assertIn("tracker.perTracker.apiVersion", self.steps)
        # tracker.type jira is offered as a write choice.
        self.assertIn("jira", self.steps)

    def test_skill_config_write_emits_jira_keys(self) -> None:
        self.assertIn("tracker.perTracker.baseUrl", self.skill)
        self.assertIn("tracker.perTracker.projectKey", self.skill)
        self.assertIn("tracker.perTracker.authScheme", self.skill)
        self.assertIn("tracker.perTracker.apiVersion", self.skill)

    # --- readiness ceremony branch (R5) -------------------------------------

    def test_steps_has_jira_readiness_branch(self) -> None:
        # A dedicated Jira readiness branch — a workflow STATUS NAME (like Linear,
        # not a label), validated against the project's statuses when creds are
        # present, else skip → no-op backlog lane.
        self.assertIn("/rest/api/", self.steps)
        self.assertIn("project/$PROJ_KEY/statuses", self.steps)
        self.assertIn("READY_OK", self.steps)
        self.assertIn("tracker.readyState", self.steps)

    def test_steps_jira_readiness_uses_persisted_auth_scheme(self) -> None:
        # rp-review fix: the readiness validation must branch on the CEREMONY-
        # PERSISTED authScheme (decided once, R5), NOT re-race which JIRA_* env
        # var happens to be set. Assert it reads the persisted config + branches
        # on cloud-basic / bearer-pat by name, and resolves baseUrl/projectKey
        # config-first (env baseUrl override only).
        self.assertIn("tracker.perTracker.authScheme", self.steps)
        self.assertIn("cloud-basic)", self.steps)
        self.assertIn("bearer-pat)", self.steps)
        self.assertIn("tracker.perTracker.projectKey", self.steps)
        self.assertIn("tracker.perTracker.baseUrl", self.steps)

    # --- tracker-first caveat (R6-identity) ---------------------------------

    def test_steps_phase2_caveat_says_jira_tracker_first(self) -> None:
        # Jira PROJ-123 IS KEY-N → tracker-first like Linear (distinct from
        # GitHub/GitLab flow-first-only). The Phase 2 caveat must say so.
        self.assertIn("Jira grabs go TRACKER-FIRST", self.steps)
        self.assertIn("PROJ-123", self.steps)


if __name__ == "__main__":
    unittest.main()
