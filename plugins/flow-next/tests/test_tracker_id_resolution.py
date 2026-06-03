"""Tracker-key identity & id resolution (fn-52.10, R16).

Covers the three grammars, spec + task resolution through the shared
canonicalizers, candidate-set ambiguity, the central `resolve_task_arg`
canonicalizer (alias never persisted), the case rule, and mixed-format
total-order sorting.

Grammar / sort tests are pure-function (no flow dir). Resolution / command
tests use an in-process flow dir + the real command handlers.

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
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_tracker_res_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()


# ── Grammar (pure) ─────────────────────────────────────────────────────────


class GrammarTestCase(unittest.TestCase):
    def test_alias_grammar(self) -> None:
        self.assertTrue(flowctl.is_spec_id("wor-17"))
        self.assertTrue(flowctl.is_task_id("wor-17.3"))
        parsed = flowctl.parse_any_id("wor-17")
        self.assertEqual(parsed, ("tracker", "wor", 17, None))
        parsed_task = flowctl.parse_any_id("wor-17.3")
        self.assertEqual(parsed_task, ("tracker", "wor", 17, 3))

    def test_canonical_grammar(self) -> None:
        self.assertTrue(flowctl.is_spec_id("wor-17-fix-login"))
        self.assertTrue(flowctl.is_task_id("wor-17-fix-login.2"))
        self.assertEqual(
            flowctl.parse_any_id("wor-17-fix-login"), ("tracker", "wor", 17, None)
        )
        self.assertEqual(
            flowctl.parse_any_id("wor-17-fix-login.2"), ("tracker", "wor", 17, 2)
        )

    def test_fn_reserved_and_resolved_first(self) -> None:
        # `fn` is the native scheme — never reported as a tracker key.
        self.assertEqual(flowctl.parse_any_id("fn-5")[0], "fn")
        self.assertEqual(flowctl.parse_any_id("fn-5-slug.3"), ("fn", "fn", 5, 3))
        # A tracker key literally named `fn` is rejected at the grammar layer
        # (the native branch claims it; the tracker regexes exclude it).
        self.assertIsNotNone(flowctl.parse_any_id("fn-5"))
        # parse_id stays fn-only (None for tracker ids).
        self.assertEqual(flowctl.parse_id("wor-17"), (None, None))
        self.assertEqual(flowctl.parse_id("fn-5-slug.3"), (5, 3))

    def test_reject_reserved_tracker_key(self) -> None:
        with self.assertRaises(SystemExit):
            with redirect_stderr(io.StringIO()):
                flowctl.reject_reserved_tracker_key("FN-17")
        # A non-fn key is accepted (no raise).
        flowctl.reject_reserved_tracker_key("WOR-17")
        flowctl.reject_reserved_tracker_key(None)

    def test_non_ids(self) -> None:
        for bad in ("", None, "not an id", "wor", "-17", "wor-", "WOR-17"):
            # Upper-case is NOT a canonical on-disk id (ids are lowercase).
            self.assertIsNone(flowctl.parse_any_id(bad), bad)

    def test_spec_id_from_task_preserves_form(self) -> None:
        self.assertEqual(flowctl.spec_id_from_task("wor-17-fix.3"), "wor-17-fix")
        self.assertEqual(flowctl.spec_id_from_task("wor-17.3"), "wor-17")
        self.assertEqual(flowctl.spec_id_from_task("fn-5-x.3"), "fn-5-x")


# ── Mixed-format sort (pure) ───────────────────────────────────────────────


class MixedSortTestCase(unittest.TestCase):
    def test_mixed_set_no_typeerror_and_stable_order(self) -> None:
        ids = ["wor-17-login", "fn-10", "abc-3-foo", "fn-2"]
        # No TypeError on the mixed fn-* + tracker set.
        ordered = sorted(ids, key=flowctl.id_sort_key)
        # Documented order: native fn first (by number), then tracker keys
        # lexicographically (abc < wor), then by number.
        self.assertEqual(ordered, ["fn-2", "fn-10", "abc-3-foo", "wor-17-login"])

    def test_unparseable_sorts_last(self) -> None:
        ordered = sorted(["wor-1", "zzz-not-an-id-token!", "fn-1"], key=flowctl.id_sort_key)
        self.assertEqual(ordered[0], "fn-1")
        self.assertEqual(ordered[-1], "zzz-not-an-id-token!")

    def test_task_num_total_order(self) -> None:
        ordered = sorted(
            ["wor-17.10", "wor-17.2", "wor-17.1"], key=flowctl.id_sort_key
        )
        self.assertEqual(ordered, ["wor-17.1", "wor-17.2", "wor-17.10"])


# ── Resolution + command surface ───────────────────────────────────────────


class ResolutionTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        subprocess.run(
            ["git", "init", "-q"], cwd=self.tmpdir, check=True, capture_output=True
        )
        self.flowctl = _load_flowctl()
        self.flow_dir = self.tmpdir / ".flow"
        self._call("init")

    def tearDown(self) -> None:
        os.chdir(self.prev_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _call(self, func_name: str = None, *, func=None, **kwargs) -> dict:
        kwargs.setdefault("json", True)
        ns = argparse.Namespace(**kwargs)
        handler = func or getattr(self.flowctl, f"cmd_{func_name}")
        buf = io.StringIO()
        with redirect_stdout(buf):
            handler(ns)
        out = buf.getvalue().strip()
        return json.loads(out) if out else {}

    def _create_tracker_spec(self, title: str, identifier: str) -> str:
        res = self._call(
            func=self.flowctl.cmd_spec_create,
            title=title,
            branch=None,
            tracker_first=True,
            tracker_identifier=identifier,
        )
        return res["id"]

    def _create_flow_spec(self, title: str) -> str:
        return self._call(
            func=self.flowctl.cmd_spec_create,
            title=title,
            branch=None,
            tracker_first=False,
            tracker_identifier=None,
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

    def _set_tracker(
        self, spec_id: str, uuid: str, identifier: str, *, force: bool = False
    ) -> None:
        # `force` allows deliberately assigning a duplicate UUID (the dup-id
        # guard from fn-52.1 otherwise refuses it) for the dedupe scenarios.
        self._call(
            func=self.flowctl.cmd_sync_set_tracker_id,
            id=spec_id,
            tracker_id=uuid,
            identifier=identifier,
            url=None,
            force=force,
        )

    # --- SPEC resolution ----------------------------------------------------

    def test_bare_handle_resolves_canonical_prefix(self) -> None:
        canonical = self._create_tracker_spec("Fix login", "WOR-17")
        self.assertEqual(
            self.flowctl.expand_bare_spec_id(self.flow_dir, "wor-17"), canonical
        )

    def test_full_canonical_resolves_directly(self) -> None:
        self._create_tracker_spec("Fix login", "WOR-17")
        self.assertEqual(
            self.flowctl.expand_bare_spec_id(self.flow_dir, "wor-17-fix-login"),
            "wor-17-fix-login",
        )

    def test_show_via_bare_handle(self) -> None:
        canonical = self._create_tracker_spec("Fix login", "WOR-17")
        res = self._call(func=self.flowctl.cmd_show, id="wor-17")
        self.assertEqual(res["id"], canonical)

    def test_case_insensitive_handle(self) -> None:
        canonical = self._create_tracker_spec("Fix login", "WOR-17")
        # Resolution is case-insensitive on the alias index; the on-disk id is
        # lowercase, so resolve via the alias index path (flow-first spec).
        flow_id = self._create_flow_spec("Plain flow")
        self._set_tracker(flow_id, "uuid-up", "WOR-99")
        self.assertEqual(
            self.flowctl.expand_bare_spec_id(self.flow_dir, "wor-99"), flow_id
        )
        # Confirm the display identifier kept its case.
        data = json.loads(
            self.flowctl.find_spec_json_path(self.flow_dir, flow_id).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(data["tracker"]["identifier"], "WOR-99")
        self.assertEqual(canonical, "wor-17-fix-login")

    def test_alias_index_resolves_flow_first_spec(self) -> None:
        flow_id = self._create_flow_spec("Plain flow")
        self._set_tracker(flow_id, "uuid-1", "WOR-42")
        # bare handle `wor-42` has no canonical-prefix spec; the alias index
        # (flow-first spec carrying tracker.identifier=WOR-42) resolves it.
        self.assertEqual(
            self.flowctl.expand_bare_spec_id(self.flow_dir, "wor-42"), flow_id
        )

    # --- TASK resolution ----------------------------------------------------

    def test_task_alias_canonicalizes(self) -> None:
        spec_id = self._create_tracker_spec("Fix login", "WOR-17")
        self._add_task(spec_id, "Step one")
        # resolve_task_arg expands wor-17.1 → wor-17-fix-login.1.
        self.assertEqual(
            self.flowctl.resolve_task_arg(self.flow_dir, "wor-17.1"),
            "wor-17-fix-login.1",
        )

    def test_start_done_via_task_alias(self) -> None:
        spec_id = self._create_tracker_spec("Fix login", "WOR-17")
        self._add_task(spec_id, "Step one")
        started = self._call(func=self.flowctl.cmd_start, id="wor-17.1", note=None, force=False)
        self.assertEqual(started["status"], "in_progress")
        # Show via canonical reflects the alias-driven write.
        shown = self._call(func=self.flowctl.cmd_show, id="wor-17-fix-login.1")
        self.assertEqual(shown["status"], "in_progress")

    def test_dep_add_persists_canonical_not_alias(self) -> None:
        spec_id = self._create_tracker_spec("Fix login", "WOR-17")
        self._add_task(spec_id, "Step one")
        self._add_task(spec_id, "Step two")
        # dep add via aliases → canonical persisted in depends_on.
        self._call(
            func=self.flowctl.cmd_dep_add,
            task="wor-17.2",
            depends_on="wor-17.1",
        )
        data = json.loads(
            (self.flow_dir / "tasks" / "wor-17-fix-login.2.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(data["depends_on"], ["wor-17-fix-login.1"])
        # The alias form is NEVER persisted.
        self.assertNotIn("wor-17.1", data["depends_on"])

    def test_task_create_deps_persist_canonical(self) -> None:
        spec_id = self._create_tracker_spec("Fix login", "WOR-17")
        self._add_task(spec_id, "Step one")
        res = self._call(
            func=self.flowctl.cmd_task_create,
            spec="wor-17",  # bare handle for the spec
            epic=None,
            title="Step two",
            deps="wor-17.1",  # alias dep
            priority=None,
            acceptance_file=None,
        )
        self.assertEqual(res["id"], "wor-17-fix-login.2")
        self.assertEqual(res["depends_on"], ["wor-17-fix-login.1"])

    # --- Ambiguity (candidate-set) -----------------------------------------

    def test_same_uuid_dedupes_to_canonical(self) -> None:
        # A tracker-first canonical AND a flow-first spec sharing the same UUID
        # → one logical issue → dedupe to the canonical tracker-key id.
        canonical = self._create_tracker_spec("Fix login", "WOR-17")
        self._set_tracker(canonical, "uuid-shared", "WOR-17")
        flow_id = self._create_flow_spec("Echo of login")
        self._set_tracker(flow_id, "uuid-shared", "WOR-17", force=True)
        resolved = self.flowctl.expand_bare_spec_id(self.flow_dir, "wor-17")
        self.assertEqual(resolved, canonical)

    def test_distinct_uuid_is_ambiguous(self) -> None:
        canonical = self._create_tracker_spec("Fix login", "WOR-17")
        self._set_tracker(canonical, "uuid-a", "WOR-17")
        flow_id = self._create_flow_spec("Different issue")
        self._set_tracker(flow_id, "uuid-b", "WOR-17")
        with self.assertRaises(SystemExit):
            with redirect_stderr(io.StringIO()):
                self.flowctl.expand_bare_spec_id(self.flow_dir, "wor-17")

    def test_two_flow_first_same_identifier_ambiguous(self) -> None:
        a = self._create_flow_spec("Spec A")
        b = self._create_flow_spec("Spec B")
        self._set_tracker(a, "uuid-a", "WOR-77")
        self._set_tracker(b, "uuid-b", "WOR-77")
        with self.assertRaises(SystemExit):
            with redirect_stderr(io.StringIO()):
                self.flowctl.expand_bare_spec_id(self.flow_dir, "wor-77")

    def test_local_repull_same_uuid_no_duplicate(self) -> None:
        # Boundary: one team per repo → a re-pull of the same issue dedups via
        # the tracker UUID. Two flow-first specs with the SAME uuid resolve to
        # one target (no ambiguous error).
        a = self._create_flow_spec("Pulled once")
        b = self._create_flow_spec("Pulled again")
        self._set_tracker(a, "uuid-same", "WOR-88")
        self._set_tracker(b, "uuid-same", "WOR-88", force=True)
        resolved = self.flowctl.expand_bare_spec_id(self.flow_dir, "wor-88")
        self.assertIn(resolved, {a, b})

    # --- Case rule (uppercase handle) — review-cycle additions --------------

    def test_casefold_handle_helper(self) -> None:
        self.assertEqual(self.flowctl.casefold_handle("WOR-17"), "wor-17")
        self.assertEqual(self.flowctl.casefold_handle("WOR-17.3"), "wor-17.3")
        # Native + already-lowercase pass through unchanged.
        self.assertEqual(self.flowctl.casefold_handle("fn-1"), "fn-1")
        self.assertEqual(self.flowctl.casefold_handle("wor-17"), "wor-17")
        self.assertIsNone(self.flowctl.casefold_handle(None))

    def test_show_via_uppercase_handle(self) -> None:
        canonical = self._create_tracker_spec("Fix login", "WOR-17")
        res = self._call(func=self.flowctl.cmd_show, id="WOR-17")
        self.assertEqual(res["id"], canonical)

    def test_start_via_uppercase_task_handle(self) -> None:
        spec_id = self._create_tracker_spec("Fix login", "WOR-17")
        self._add_task(spec_id, "Step one")
        started = self._call(
            func=self.flowctl.cmd_start, id="WOR-17.1", note=None, force=False
        )
        self.assertEqual(started["status"], "in_progress")
        self.assertEqual(started["id"], "wor-17-fix-login.1")

    def test_expand_bare_spec_id_uppercase(self) -> None:
        canonical = self._create_tracker_spec("Fix login", "WOR-17")
        self.assertEqual(
            self.flowctl.expand_bare_spec_id(self.flow_dir, "WOR-17"), canonical
        )

    # --- cmd_next / cmd_tasks enumeration — review-cycle additions ----------

    def test_next_sees_tracker_spec(self) -> None:
        spec_id = self._create_tracker_spec("Fix login", "WOR-17")
        self._add_task(spec_id, "Step one")
        res = self._call(
            func=self.flowctl.cmd_next,
            specs_file=None,
            epics_file=None,
            require_plan_review=False,
            require_completion_review=False,
        )
        # `next` surfaces the tracker spec's task (not filtered out by fn regex).
        self.assertNotEqual(res.get("status"), "done")
        blob = json.dumps(res)
        self.assertIn("wor-17-fix-login", blob)

    def test_tasks_unfiltered_lists_tracker_tasks(self) -> None:
        spec_id = self._create_tracker_spec("Fix login", "WOR-17")
        self._add_task(spec_id, "Step one")
        self._create_flow_spec("Plain flow")  # fn-1
        # No --spec filter → must include the tracker-key task.
        res = self._call(
            func=self.flowctl.cmd_tasks, spec=None, epic=None, status=None
        )
        ids = [t["id"] for t in res["tasks"]]
        self.assertIn("wor-17-fix-login.1", ids)

    def test_tasks_scoped_by_tracker_handle(self) -> None:
        spec_id = self._create_tracker_spec("Fix login", "WOR-17")
        self._add_task(spec_id, "Step one")
        res = self._call(
            func=self.flowctl.cmd_tasks, spec="wor-17", epic=None, status=None
        )
        ids = [t["id"] for t in res["tasks"]]
        self.assertEqual(ids, ["wor-17-fix-login.1"])

    # --- task set-deps + spec deps via handle — review-cycle additions ------

    def test_task_set_deps_via_aliases(self) -> None:
        spec_id = self._create_tracker_spec("Fix login", "WOR-17")
        self._add_task(spec_id, "Step one")
        self._add_task(spec_id, "Step two")
        res = self._call(
            func=self.flowctl.cmd_task_set_deps,
            task_id="wor-17.2",
            deps="wor-17.1",
        )
        # Canonical task + canonical dep persisted; no alias leakage.
        self.assertEqual(res["task"], "wor-17-fix-login.2")
        data = json.loads(
            (self.flow_dir / "tasks" / "wor-17-fix-login.2.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(data["depends_on"], ["wor-17-fix-login.1"])

    def test_spec_add_dep_cross_spec_via_handle(self) -> None:
        tracker_id = self._create_tracker_spec("Fix login", "WOR-17")
        flow_id = self._create_flow_spec("Other work")  # fn-1-other-work
        # spec add-dep wor-17 fn-1 → resolves both, persists canonical ids.
        res = self._call(
            func=self.flowctl.cmd_spec_add_dep,
            epic="wor-17",
            depends_on=flow_id,
        )
        self.assertEqual(res["id"], tracker_id)
        self.assertIn(flow_id, res["depends_on_epics"])
        # rm via handle removes it again.
        rm = self._call(
            func=self.flowctl.cmd_spec_rm_dep,
            epic="wor-17",
            depends_on=flow_id,
        )
        self.assertNotIn(flow_id, rm["depends_on_epics"])

    # --- reserved key rejected at LINK time — review-cycle addition ---------

    def test_set_tracker_id_rejects_reserved_fn_identifier(self) -> None:
        flow_id = self._create_flow_spec("Plain flow")
        with self.assertRaises(SystemExit):
            with redirect_stderr(io.StringIO()):
                self._set_tracker(flow_id, "uuid-x", "FN-17")

    def test_set_tracker_id_rejects_slugged_identifier(self) -> None:
        # Round-2: link-time identifier validation is strict (bare key only).
        flow_id = self._create_flow_spec("Plain flow")
        with self.assertRaises(SystemExit):
            with redirect_stderr(io.StringIO()):
                self._set_tracker(flow_id, "uuid-x", "WOR-17-slugged")

    # --- uppercase spec/task setters — round-2 additions --------------------

    def test_set_title_via_uppercase_handle(self) -> None:
        # `set-title WOR-17 ...` must reach the no-rename branch (resolve, not
        # error pre-gate). The spec is tracker-keyed → title-only update.
        self._create_tracker_spec("Fix login", "WOR-17")
        res = self._call(
            func=self.flowctl.cmd_spec_set_title,
            id="WOR-17",
            title="New tracker title",
        )
        self.assertEqual(res["id"], "wor-17-fix-login")
        self.assertFalse(res["renamed"])

    def test_set_plan_review_status_via_uppercase_handle(self) -> None:
        self._create_tracker_spec("Fix login", "WOR-17")
        res = self._call(
            func=self.flowctl.cmd_spec_set_plan_review_status,
            id="WOR-17",
            status="ship",
        )
        self.assertEqual(res["id"], "wor-17-fix-login")
        self.assertEqual(res["plan_review_status"], "ship")

    def test_set_branch_via_uppercase_handle(self) -> None:
        self._create_tracker_spec("Fix login", "WOR-17")
        res = self._call(
            func=self.flowctl.cmd_spec_set_branch,
            id="WOR-17",
            branch="feature/login",
        )
        self.assertEqual(res["id"], "wor-17-fix-login")
        self.assertEqual(res["branch_name"], "feature/login")

    def test_sync_get_state_via_uppercase_handle(self) -> None:
        self._create_tracker_spec("Fix login", "WOR-17")
        res = self._call(func=self.flowctl.cmd_sync_get_state, id="WOR-17")
        self.assertEqual(res["id"], "wor-17-fix-login")
        # tracker.identifier carries the display form set at create.
        self.assertEqual(res["tracker"]["identifier"], "WOR-17")

    def test_set_plan_via_uppercase_handle(self, ) -> None:
        import tempfile as _tf
        self._create_tracker_spec("Fix login", "WOR-17")
        with _tf.NamedTemporaryFile("w", suffix=".md", delete=False) as fh:
            fh.write("# wor-17-fix-login Fix login\n\n## Overview\nbody\n")
            plan_path = fh.name
        res = self._call(
            func=self.flowctl.cmd_spec_set_plan, id="WOR-17", file=plan_path
        )
        self.assertEqual(res["id"], "wor-17-fix-login")

    # --- task section setters via alias — round-2 additions -----------------

    def test_task_set_description_via_alias(self) -> None:
        import tempfile as _tf
        spec_id = self._create_tracker_spec("Fix login", "WOR-17")
        self._add_task(spec_id, "Step one")
        with _tf.NamedTemporaryFile("w", suffix=".md", delete=False) as fh:
            fh.write("new description body\n")
            desc_path = fh.name
        # Alias `wor-17.1` must canonicalize to wor-17-fix-login.1 before IO.
        res = self._call(
            func=self.flowctl.cmd_task_set_description,
            id="wor-17.1",
            file=desc_path,
        )
        self.assertEqual(res["id"], "wor-17-fix-login.1")
        body = (
            self.flow_dir / "tasks" / "wor-17-fix-login.1.md"
        ).read_text(encoding="utf-8")
        self.assertIn("new description body", body)

    def test_task_reset_via_alias(self) -> None:
        spec_id = self._create_tracker_spec("Fix login", "WOR-17")
        self._add_task(spec_id, "Step one")
        self._call(
            func=self.flowctl.cmd_start, id="wor-17.1", note=None, force=False
        )
        self._call(
            func=self.flowctl.cmd_block,
            id="wor-17.1",
            reason_file=self._write_tmp("blocked: needs X"),
        )
        res = self._call(
            func=self.flowctl.cmd_task_reset,
            task_id="wor-17.1",
            cascade=False,
        )
        self.assertTrue(res["success"])

    def _write_tmp(self, text: str) -> str:
        import tempfile as _tf
        with _tf.NamedTemporaryFile("w", suffix=".md", delete=False) as fh:
            fh.write(text)
            return fh.name

    # --- validate --all enumeration + whitespace identifier — round-3 -------

    def test_validate_all_sees_tracker_spec(self) -> None:
        spec_id = self._create_tracker_spec("Fix login", "WOR-17")
        self._add_task(spec_id, "Step one")
        self._create_flow_spec("Plain flow")  # fn-1
        res = self._call(
            func=self.flowctl.cmd_validate, spec=None, epic=None, all=True
        )
        blob = json.dumps(res)
        # Tracker-key spec is enumerated by `validate --all` (not fn-regex skipped).
        self.assertIn("wor-17-fix-login", blob)
        self.assertTrue(res.get("valid", res.get("success")))

    def test_validate_all_native_collision_ignores_tracker(self) -> None:
        # A tracker spec must never trip the native fn-N collision check.
        self._create_tracker_spec("Fix login", "WOR-1")  # wor-1-...
        self._create_flow_spec("Plain")  # fn-1-...
        res = self._call(
            func=self.flowctl.cmd_validate, spec=None, epic=None, all=True
        )
        # No "Spec ID collision: fn-1" despite a wor-1 + fn-1 coexisting.
        self.assertNotIn("collision", json.dumps(res).lower())

    def test_link_stores_stripped_identifier(self) -> None:
        # Quoted whitespace in the identifier must not persist an unresolvable
        # alias — the stored display is stripped, and the handle still resolves.
        flow_id = self._create_flow_spec("Plain flow")
        self._set_tracker(flow_id, "uuid-w", "  WOR-55  ")
        data = json.loads(
            self.flowctl.find_spec_json_path(self.flow_dir, flow_id).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(data["tracker"]["identifier"], "WOR-55")
        self.assertEqual(
            self.flowctl.expand_bare_spec_id(self.flow_dir, "wor-55"), flow_id
        )


if __name__ == "__main__":
    unittest.main()
