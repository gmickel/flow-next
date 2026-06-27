"""Unit tests for the fn-68.1 pilot backlog-mode flowctl SUBSTRATE (R1/R8/R9).

Three thin, judgment-free additions to flowctl — pure enumeration + storage:

  1. ``pilot.autonomy`` config default — a SCALAR string-enum (ready|backlog)
     seeded ``"ready"`` in ``get_default_config()`` as a sibling to
     ``pipeline.qa``. STRICT positive read (the pilot gate activates ONLY on
     the literal ``"backlog"``; a coerced bool ``true`` must NOT activate). The
     force-gate is the SIBLING key ``pilot.gateClasses`` (a list) — NOT a
     ``pilot.autonomy.gate`` sub-path (a scalar + a list cannot share the
     ``pilot.autonomy`` dot-path; review finding #2).

  2. ``ready --all`` — a NEW spec-level eligibility-FACTS mode (distinct from
     the existing task-within-spec ``ready --spec``). Returns
     ``{id, ready, readySignal, blockedBy, hasSpec}`` — ``ready`` is the LOCAL
     fn-58 boolean, ``readySignal ∈ {local, none}``. NO ``triageClass`` /
     completeness / judgment field (that read is the host skill's).

  3. ``pilot-log append`` / ``summary`` — a FROZEN decision-log CLI writing
     ``{tick, id, action, stage, costTokens}`` rows under ``.flow/pilot-runs/``
     (sync-runs-style; NEVER a ``receipts/`` path the ralph-guard validates).
     ``--id`` accepts an OPAQUE id (spec id OR bare tracker key), safe-filename
     normalized, never forced through ``resolve_spec_id_arg``.

  4. ``pilot-runs/`` added to the auto-gitignore patterns + an existing
     ``.flow/.gitignore`` is upgraded in place.

Pure-stdlib unittest; mirrors test_pipeline_qa_config.py / test_flow_gitignore.py.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve()
PLUGIN_DIR = HERE.parent.parent                 # plugins/flow-next
REPO_ROOT = PLUGIN_DIR.parent.parent            # repo root
FLOWCTL_PY = PLUGIN_DIR / "scripts" / "flowctl.py"
DOGFOOD_FLOWCTL_PY = REPO_ROOT / ".flow" / "bin" / "flowctl.py"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_pilot_backlog_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class _FlowctlTmpRepo(unittest.TestCase):
    """Shared setUp: a throwaway repo with an initialized .flow/ + cwd chdir."""

    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        self.flowctl = _load_flowctl()
        # init materializes .flow/ structure + config.json + .gitignore.
        self._run(self.flowctl.cmd_init, json=True)

    def tearDown(self) -> None:
        os.chdir(self.prev_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run(self, func, **ns_kwargs) -> dict:
        """Invoke a cmd_* with an argparse namespace; capture JSON stdout."""
        ns = argparse.Namespace(**ns_kwargs)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            func(ns)
        out = buf.getvalue().strip()
        return json.loads(out) if out else {}

    def _config_get(self, key: str) -> dict:
        return self._run(self.flowctl.cmd_config_get, key=key, json=True, raw=False)

    def _config_set(self, key: str, value: str) -> dict:
        return self._run(self.flowctl.cmd_config_set, key=key, value=value, json=True)

    def _read_config(self) -> dict:
        return json.loads(
            (self.tmpdir / ".flow" / "config.json").read_text(encoding="utf-8")
        )


# ── 1. pilot.* config default ──────────────────────────────────────────────


class PilotAutonomyConfigTestCase(_FlowctlTmpRepo):
    def test_defaults_dict_has_pilot_block(self) -> None:
        defaults = self.flowctl.get_default_config()
        self.assertIn("pilot", defaults)
        self.assertEqual(defaults["pilot"], {"autonomy": "ready", "gateClasses": []})

    def test_fresh_autonomy_is_ready_string_not_bool(self) -> None:
        out = self._config_get("pilot.autonomy")
        self.assertEqual(out["value"], "ready")
        # SCALAR string-enum, never a bool.
        self.assertNotIsInstance(out["value"], bool)

    def test_gateclasses_is_sibling_list_not_subpath(self) -> None:
        # The force-gate is the SIBLING `pilot.gateClasses` (a list), NOT
        # `pilot.autonomy.gate` — a scalar and a list cannot share the
        # `pilot.autonomy` dot-path (finding #2).
        out = self._config_get("pilot.gateClasses")
        self.assertEqual(out["value"], [])
        # `autonomy` stays a scalar; there is no `.gate` sub-path under it.
        self.assertEqual(self._config_get("pilot.autonomy")["value"], "ready")

    def test_strict_positive_read_backlog_only(self) -> None:
        # The pilot gate is `value == "backlog"`. Default "ready" → OFF.
        self.assertNotEqual(self._config_get("pilot.autonomy")["value"], "backlog")
        # Literal "backlog" → ON.
        self._config_set("pilot.autonomy", "backlog")
        self.assertEqual(self._config_get("pilot.autonomy")["value"], "backlog")

    def test_bool_true_does_not_activate(self) -> None:
        # A coerced bool `true` must NOT read as the activating "backlog"
        # (memory docs-activation-command-for-string-enum).
        self._config_set("pilot.autonomy", "true")
        value = self._config_get("pilot.autonomy")["value"]
        self.assertNotEqual(value, "backlog")
        # The strict gate predicate is False on `true`.
        self.assertFalse(value == "backlog")

    def test_fresh_init_materializes_pilot_block(self) -> None:
        # Like work.*/land.*/pipeline.* (NOT in _INIT_UNMATERIALIZED_BLOCKS),
        # init persists the pilot block into config.json.
        self.assertEqual(
            self._read_config().get("pilot"),
            {"autonomy": "ready", "gateClasses": []},
        )

    def test_init_upgrade_adds_pilot_block(self) -> None:
        config_path = self.tmpdir / ".flow" / "config.json"
        config_path.write_text(json.dumps({"memory": {"enabled": True}}), encoding="utf-8")
        self._run(self.flowctl.cmd_init, json=True)
        self.assertEqual(
            self._read_config().get("pilot"),
            {"autonomy": "ready", "gateClasses": []},
        )

    def test_user_set_value_survives_init_rerun(self) -> None:
        self._config_set("pilot.autonomy", "backlog")
        self._run(self.flowctl.cmd_init, json=True)
        self.assertEqual(self._config_get("pilot.autonomy")["value"], "backlog")

    def test_pilot_block_does_not_clash_with_siblings(self) -> None:
        self._config_set("pilot.autonomy", "backlog")
        # Setting pilot.* leaves the other top-level blocks intact.
        self.assertEqual(self._config_get("work.delegateModel")["value"], "gpt-5.5")
        self.assertEqual(self._config_get("pipeline.qa")["value"], "off")
        self.assertEqual(self._config_get("pilot.gateClasses")["value"], [])


# ── 2. ready --all spec-level eligibility facts ────────────────────────────


class ReadyAllTestCase(_FlowctlTmpRepo):
    def _spec_create(self, title: str) -> str:
        out = self._run(
            self.flowctl.cmd_spec_create,
            title=title,
            branch=None,
            tracker_first=False,
            tracker_identifier=None,
            json=True,
        )
        return out["id"]

    def _ready_all(self) -> dict:
        return self._run(self.flowctl.cmd_ready, all=True, json=True, spec=None, epic=None)

    def test_empty_backlog(self) -> None:
        out = self._ready_all()
        self.assertTrue(out["success"])
        self.assertEqual(out["specs"], [])
        self.assertEqual(out["count"], 0)

    def test_facts_shape_and_no_judgment_field(self) -> None:
        sid = self._spec_create("Alpha")
        out = self._ready_all()
        row = next(r for r in out["specs"] if r["id"] == sid)
        self.assertEqual(
            set(row.keys()), {"id", "ready", "readySignal", "blockedBy", "hasSpec"}
        )
        # No judgment/triage field leaks from flowctl.
        self.assertNotIn("triageClass", row)
        self.assertNotIn("completeness", row)
        # hasSpec is always True for a real local spec record.
        self.assertTrue(row["hasSpec"])

    def test_local_ready_flag_and_signal(self) -> None:
        sid = self._spec_create("Alpha")
        # Not ready by default.
        row = next(r for r in self._ready_all()["specs"] if r["id"] == sid)
        self.assertFalse(row["ready"])
        self.assertEqual(row["readySignal"], "none")
        # Flip the local fn-58 flag.
        self._run(self.flowctl.cmd_spec_ready, id=sid, json=True)
        row = next(r for r in self._ready_all()["specs"] if r["id"] == sid)
        self.assertTrue(row["ready"])
        self.assertEqual(row["readySignal"], "local")

    def test_blocked_by_spec_deps(self) -> None:
        a = self._spec_create("Alpha base")
        b = self._spec_create("Beta dep on alpha")
        self._run(self.flowctl.cmd_spec_add_dep, epic=b, depends_on=a, json=True)
        rows = {r["id"]: r for r in self._ready_all()["specs"]}
        self.assertEqual(rows[b]["blockedBy"], [a])
        self.assertEqual(rows[a]["blockedBy"], [])

    def test_all_branch_ignores_spec_arg_and_leaves_task_ready_intact(self) -> None:
        # The --all branch is distinct: it does not require/resolve --spec.
        out = self._run(
            self.flowctl.cmd_ready, all=True, json=True, spec="fn-does-not-exist", epic=None
        )
        self.assertTrue(out["success"])
        self.assertIn("specs", out)

    def test_task_level_ready_unchanged(self) -> None:
        # Without --all the command is the task-within-spec mode (regression).
        sid = self._spec_create("Alpha")
        self._run(
            self.flowctl.cmd_task_create, spec=sid, epic=None, title="task one",
            deps=None, acceptance_file=None, priority=None, json=True,
        )
        out = self._run(self.flowctl.cmd_ready, all=False, json=True, spec=sid, epic=None)
        self.assertEqual(out["spec"], sid)
        self.assertEqual([t["id"] for t in out["ready"]], [f"{sid}.1"])


# ── 3. pilot-log append / summary ──────────────────────────────────────────


class PilotLogTestCase(_FlowctlTmpRepo):
    def _append(self, **kw) -> dict:
        ns_kw = dict(id=None, action=None, stage=None, cost_tokens=None, json=True)
        ns_kw.update(kw)
        return self._run(self.flowctl.cmd_pilot_log_append, **ns_kw)

    def _summary(self) -> dict:
        return self._run(self.flowctl.cmd_pilot_log_summary, json=True)

    def test_append_writes_row_under_pilot_runs(self) -> None:
        out = self._append(id="fn-68", action="triaged", stage="plan", cost_tokens=1500)
        self.assertTrue(out["success"])
        self.assertIn(".flow/pilot-runs/", out["row"].replace(os.sep, "/"))
        # Guard-safe: never a receipts/ path.
        self.assertNotIn("receipts/", out["row"].replace(os.sep, "/"))

    def test_row_schema(self) -> None:
        self._append(id="fn-68", action="triaged", stage="plan", cost_tokens=1500)
        rows = self._summary()["rows"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(
            set(rows[0].keys()), {"tick", "id", "action", "stage", "costTokens"}
        )
        self.assertEqual(rows[0]["id"], "fn-68")
        self.assertEqual(rows[0]["action"], "triaged")
        self.assertEqual(rows[0]["stage"], "plan")
        self.assertEqual(rows[0]["costTokens"], 1500)

    def test_opaque_tracker_key_id_not_resolved(self) -> None:
        # A bare tracker key (tracker-only item, no spec) must be accepted
        # verbatim — NEVER forced through resolve_spec_id_arg.
        out = self._append(id="WOR-17", action="needs-human", stage="-")
        self.assertTrue(out["success"])
        self.assertEqual(out["id"], "WOR-17")
        rows = self._summary()["rows"]
        self.assertEqual(rows[0]["id"], "WOR-17")

    def test_stage_dash_and_empty_normalize_to_null(self) -> None:
        self._append(id="fn-68", action="asked", stage="-")
        self._append(id="fn-69", action="asked", stage="")
        rows = {r["id"]: r for r in self._summary()["rows"]}
        self.assertIsNone(rows["fn-68"]["stage"])
        self.assertIsNone(rows["fn-69"]["stage"])

    def test_cost_tokens_optional(self) -> None:
        out = self._append(id="fn-68", action="advanced", stage="work")
        self.assertIsNone(out["costTokens"])
        self.assertIsNone(self._summary()["rows"][0]["costTokens"])

    def test_per_id_monotonic_tick(self) -> None:
        self._append(id="fn-68", action="triaged", stage="plan")
        self._append(id="fn-68", action="advanced", stage="work")
        self._append(id="WOR-17", action="blocked", stage="-")
        rows = self._summary()["rows"]
        fn68 = sorted(r["tick"] for r in rows if r["id"] == "fn-68")
        wor = [r["tick"] for r in rows if r["id"] == "WOR-17"]
        self.assertEqual(fn68, [1, 2])
        self.assertEqual(wor, [1])

    def test_invalid_action_rejected(self) -> None:
        # The frozen enum is validated. cmd_pilot_log_append error_exits (the
        # argparse `choices` also guards the CLI surface).
        with self.assertRaises(SystemExit):
            self._append(id="fn-68", action="frobnicate", stage="plan")

    def test_summary_empty_when_no_rows(self) -> None:
        out = self._summary()
        self.assertTrue(out["success"])
        self.assertEqual(out["rows"], [])
        self.assertEqual(out["count"], 0)

    def test_summary_ordered_by_id_then_tick(self) -> None:
        self._append(id="fn-70", action="triaged", stage="plan")
        self._append(id="fn-68", action="advanced", stage="work")
        self._append(id="fn-68", action="triaged", stage="plan")
        rows = self._summary()["rows"]
        keys = [(r["id"], r["tick"]) for r in rows]
        self.assertEqual(keys, sorted(keys, key=lambda k: (str(k[0]), k[1])))

    def test_slug_colliding_ids_keep_distinct_per_id_ticks(self) -> None:
        # Two DISTINCT raw ids that normalize to the same filename slug must
        # NOT share a tick counter (review finding #1) — tick is per stored id,
        # not per slug. "a/b" and "a-b" both slug to "a-b".
        self._append(id="a/b", action="triaged", stage="plan")
        self._append(id="a/b", action="advanced", stage="work")
        self._append(id="a-b", action="triaged", stage="plan")
        rows = self._summary()["rows"]
        ab_slash = sorted(r["tick"] for r in rows if r["id"] == "a/b")
        ab_dash = sorted(r["tick"] for r in rows if r["id"] == "a-b")
        self.assertEqual(ab_slash, [1, 2])
        self.assertEqual(ab_dash, [1])  # own counter, not 3

    def test_summary_tolerates_malformed_non_int_tick(self) -> None:
        # A hand-edited/corrupt row carrying a non-int tick must not crash the
        # summary sort with a str-vs-int TypeError (review finding #2).
        self._append(id="fn-1", action="triaged", stage="plan")  # valid tick=1
        run_dir = self.tmpdir / ".flow" / "pilot-runs"
        (run_dir / "pilot-fn-1-x-bad.json").write_text(
            json.dumps({"tick": "x", "id": "fn-1", "action": "asked",
                        "stage": None, "costTokens": None}),
            encoding="utf-8",
        )
        out = self._summary()  # must not raise
        self.assertTrue(out["success"])
        self.assertEqual(out["count"], 2)
        # Both rows present; the malformed one sorts as tick 0 (coerced view).
        self.assertEqual({r["tick"] for r in out["rows"]}, {1, "x"})

    def test_id_slug_blocks_path_and_linkify_hazards(self) -> None:
        # Path-traversal / separator chars collapse to '-'; leading dots are
        # stripped (no hidden files). The id field stays verbatim.
        slug = self.flowctl._pilot_log_id_slug("../../etc/passwd")
        self.assertNotIn("/", slug)
        self.assertNotIn("..", slug)
        self.assertFalse(slug.startswith("."))
        self.assertEqual(self.flowctl._pilot_log_id_slug(""), "unknown")
        # Case is preserved for tracker keys.
        self.assertEqual(self.flowctl._pilot_log_id_slug("WOR-17"), "WOR-17")


# ── 4. gitignore: pilot-runs/ pattern + existing-file upgrade ──────────────


class PilotRunsGitignoreTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.flowctl = _load_flowctl()

    def test_pilot_runs_in_pattern_set(self) -> None:
        self.assertIn("pilot-runs/", self.flowctl.FLOW_GITIGNORE_AUTO_PATTERNS)

    def test_existing_managed_gitignore_upgraded_in_place(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            flow_dir.mkdir()
            # An older managed block WITHOUT pilot-runs/, plus user content.
            stale_block = "\n".join(
                [
                    self.flowctl.FLOW_GITIGNORE_AUTO_HEADER,
                    ".checkpoint-*.json",
                    "receipts/",
                    "sync-runs/",
                    self.flowctl.FLOW_GITIGNORE_AUTO_FOOTER,
                ]
            )
            (flow_dir / ".gitignore").write_text(
                stale_block + "\n\nuser-pattern-Z\n", encoding="utf-8"
            )
            self.assertTrue(self.flowctl._ensure_flow_gitignore(flow_dir))
            content = (flow_dir / ".gitignore").read_text(encoding="utf-8")
            self.assertIn("pilot-runs/", content)
            self.assertIn("user-pattern-Z", content)  # user content preserved
            # Idempotent after the upgrade.
            self.assertFalse(self.flowctl._ensure_flow_gitignore(flow_dir))


# ── 5. byte-identical dual-copy invariant ──────────────────────────────────


class DualCopyInvariantTestCase(unittest.TestCase):
    def test_two_copies_byte_identical(self) -> None:
        self.assertEqual(
            FLOWCTL_PY.read_bytes(),
            DOGFOOD_FLOWCTL_PY.read_bytes(),
            "scripts/flowctl.py and .flow/bin/flowctl.py must be byte-identical",
        )


if __name__ == "__main__":
    unittest.main()
