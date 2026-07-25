"""Tracker-sync config defaults + activation predicate tests (fn-52.1, R1).

Asserts:
  * `get_default_config()` carries a `tracker` block with the documented
    shape: version + `enabled:false` + `type:null` + `provenance:null` +
    NESTED `perEvent` (so dotted-path get/set works) all defaulting `off` +
    perTracker + staleAfterHours + conflictTiebreak + readyState (fn-58,
    top-level scalar, default null).
  * The dotted-path API resolves a nested perEvent leaf
    (`tracker.perEvent.work.firstClaim`).
  * `deep_merge` preserves unknown keys under `tracker` (forward-compat) and
    falls back to defaults for unset keys.
  * The activation predicate `tracker_sync_active()` is VALUE-CHECKED:
      - absent raw config ⇒ inactive,
      - persisted `type: null` (even with a perEvent set) ⇒ inactive,
      - `type: ""` / unknown ⇒ inactive,
      - `enabled == true` ⇒ active,
      - `type ∈ {linear, github}` ⇒ active.

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -v
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_tracker_config_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class TrackerConfigTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        self.flowctl = _load_flowctl()
        flow_dir = self.tmpdir / ".flow"
        flow_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        os.chdir(self.prev_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_config(self, data: dict) -> None:
        (self.tmpdir / ".flow" / "config.json").write_text(
            json.dumps(data), encoding="utf-8"
        )

    # --- Defaults shape -----------------------------------------------------

    def test_default_config_has_tracker_block(self) -> None:
        cfg = self.flowctl.get_default_config()
        self.assertIn("tracker", cfg)
        t = cfg["tracker"]
        self.assertEqual(t["version"], 1)
        self.assertFalse(t["enabled"])
        self.assertIsNone(t["type"])
        self.assertIsNone(t["provenance"])
        self.assertEqual(t["staleAfterHours"], self.flowctl.TRACKER_DEFAULT_STALE_HOURS)
        self.assertEqual(t["conflictTiebreak"], "always-ask")
        # fn-58 (R3/R4): readiness projection knob — a single scalar at the
        # tracker TOP level (NOT under perTracker), default null (= off).
        self.assertIn("readyState", t)
        self.assertIsNone(t["readyState"])
        self.assertNotIn("readyState", t["perTracker"])

    def test_per_event_is_nested_and_defaults_off(self) -> None:
        t = self.flowctl.get_default_config()["tracker"]
        pe = t["perEvent"]
        # work.* is a nested object, NOT a flat literal key.
        self.assertIsInstance(pe["work"], dict)
        self.assertEqual(pe["work"]["firstClaim"], "off")
        self.assertEqual(pe["work"]["done"], "off")
        for leaf in ("capture", "interview", "plan", "makePr", "resolvePr", "completionReview"):
            self.assertEqual(pe[leaf], "off", f"{leaf} should default off")

    def test_dotted_path_resolves_nested_leaf(self) -> None:
        # No on-disk override → merged default resolves the nested leaf.
        self.assertEqual(
            self.flowctl.get_config("tracker.perEvent.work.firstClaim"), "off"
        )
        self.assertEqual(self.flowctl.get_config("tracker.perEvent.capture"), "off")
        # fn-58: a fresh repo reads a clean null for the readiness knob.
        self.assertIsNone(self.flowctl.get_config("tracker.readyState"))

    # --- config set null coercion (PR #170 review) ---------------------------

    def test_config_set_null_clears_ready_state(self) -> None:
        # Opt in: configure a readiness state, then clear it with the
        # documented off value `null`. The CLI delivers argv strings, so
        # set_config must coerce the literal "null" token to JSON null —
        # otherwise the string "null" persists and skill probes
        # (`jq -r '.value // empty'`) see a configured state named "null".
        self.flowctl.set_config("tracker.readyState", "Ready")
        on_disk = json.loads(
            (self.tmpdir / ".flow" / "config.json").read_text(encoding="utf-8")
        )
        self.assertEqual(on_disk["tracker"]["readyState"], "Ready")
        self.assertEqual(self.flowctl.get_config("tracker.readyState"), "Ready")

        self.flowctl.set_config("tracker.readyState", "null")
        on_disk = json.loads(
            (self.tmpdir / ".flow" / "config.json").read_text(encoding="utf-8")
        )
        self.assertIn("readyState", on_disk["tracker"])
        self.assertIsNone(on_disk["tracker"]["readyState"])  # real JSON null
        # `config get` round-trips to None (merged read path).
        self.assertIsNone(self.flowctl.get_config("tracker.readyState"))

    def test_config_set_null_is_case_insensitive(self) -> None:
        # Same .lower() treatment as the true/false coercion.
        self.flowctl.set_config("tracker.readyState", "NULL")
        on_disk = json.loads(
            (self.tmpdir / ".flow" / "config.json").read_text(encoding="utf-8")
        )
        self.assertIsNone(on_disk["tracker"]["readyState"])

    def test_config_set_coerces_json_object(self) -> None:
        # The CLI delivers argv strings; a JSON-object value (e.g. the Jira
        # tracker.perTracker.statusMap the discovery ceremony derives) must be
        # PARSED, not stored as a string — else the adapter cannot read it as an
        # object (PR #183). Ids stay strings (rename-stable), matching jira.md.
        sm = '{"in-progress": {"id": "3"}, "in-review": {"name": "In Review"}, "done": {"id": "10001"}}'
        self.flowctl.set_config("tracker.perTracker.statusMap", sm)
        on_disk = json.loads(
            (self.tmpdir / ".flow" / "config.json").read_text(encoding="utf-8")
        )
        stored = on_disk["tracker"]["perTracker"]["statusMap"]
        self.assertIsInstance(stored, dict)  # a real object, NOT a string
        self.assertEqual(stored["done"]["id"], "10001")  # id preserved as a string
        self.assertEqual(stored["in-review"]["name"], "In Review")

    def test_config_set_keeps_malformed_json_as_string(self) -> None:
        # A value that looks like JSON but doesn't parse falls through to the
        # literal string (surfaced downstream), never silently mangled.
        self.flowctl.set_config("tracker.perTracker.statusMap", "{not valid json")
        on_disk = json.loads(
            (self.tmpdir / ".flow" / "config.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            on_disk["tracker"]["perTracker"]["statusMap"], "{not valid json"
        )

    # --- Forward-compat -----------------------------------------------------

    def test_unknown_key_under_tracker_survives_round_trip(self) -> None:
        self._write_config({"tracker": {"myCustomKey": "hello"}})
        # Unknown key preserved (deep_merge keeps it), unset keys fall to default.
        self.assertEqual(self.flowctl.get_config("tracker.myCustomKey"), "hello")
        self.assertFalse(self.flowctl.get_config("tracker.enabled"))
        self.assertEqual(self.flowctl.get_config("tracker.conflictTiebreak"), "always-ask")

    def test_deep_merge_preserves_unknown_keys(self) -> None:
        merged = self.flowctl.deep_merge(
            self.flowctl.get_default_config(), {"tracker": {"futureKnob": 7}}
        )
        self.assertEqual(merged["tracker"]["futureKnob"], 7)
        # Existing defaults untouched.
        self.assertFalse(merged["tracker"]["enabled"])

    # --- Activation predicate (value-checked) -------------------------------

    def test_activation_inactive_when_absent(self) -> None:
        # No config file at all.
        self.assertFalse(self.flowctl.tracker_sync_active())

    def test_activation_inactive_for_persisted_type_null_with_per_event(self) -> None:
        # The critical regression: a default type:null persisted by an
        # unrelated write (plus a perEvent set) must read INACTIVE — NOT
        # dispatched to an adapter.
        self._write_config(
            {"tracker": {"type": None, "perEvent": {"capture": "reconcile"}}}
        )
        self.assertFalse(self.flowctl.tracker_sync_active())

    def test_activation_inactive_for_empty_or_unknown_type(self) -> None:
        self._write_config({"tracker": {"type": ""}})
        self.assertFalse(self.flowctl.tracker_sync_active())
        # `asana` is a genuinely-unsupported tracker type (jira became a real
        # type in fn-70, so it now activates — see test_activation_active_for_known_type).
        self._write_config({"tracker": {"type": "asana"}})
        self.assertFalse(self.flowctl.tracker_sync_active())

    def test_activation_active_when_enabled_true(self) -> None:
        self._write_config({"tracker": {"enabled": True, "type": None}})
        self.assertTrue(self.flowctl.tracker_sync_active())

    def test_activation_active_for_known_type(self) -> None:
        for ttype in ("linear", "github", "gitlab", "jira", "Linear", "GITHUB", "Jira"):
            self._write_config({"tracker": {"enabled": False, "type": ttype}})
            self.assertTrue(
                self.flowctl.tracker_sync_active(), f"type={ttype} should activate"
            )

    # --- tracker.specIds (fn-134.2 / R6 / R9) --------------------------------

    def test_default_spec_ids_is_flow_string_enum(self) -> None:
        t = self.flowctl.get_default_config()["tracker"]
        self.assertEqual(t["specIds"], "flow")
        self.assertIsInstance(t["specIds"], str)
        self.assertNotIsInstance(t["specIds"], bool)

    def test_merged_read_defaults_to_flow_when_unset(self) -> None:
        # No on-disk key → merged default "flow".
        self.assertEqual(self.flowctl.get_config("tracker.specIds"), "flow")

    def test_spec_ids_write_rejects_invalid(self) -> None:
        """WRITE contract: config set rejects anything outside flow|tracker."""
        import argparse
        import io
        from contextlib import redirect_stderr, redirect_stdout

        # Materialize a minimal config so ensure_flow_exists / set path works.
        self.flowctl.set_config("tracker.enabled", False)
        for bad in ("yes", "true", "on", "fn", "github", "TRACKER", ""):
            ns = argparse.Namespace(key="tracker.specIds", value=bad, json=True)
            buf = io.StringIO()
            err = io.StringIO()
            with redirect_stdout(buf), redirect_stderr(err):
                with self.assertRaises(SystemExit) as ctx:
                    self.flowctl.cmd_config_set(ns)
            self.assertNotEqual(ctx.exception.code, 0, bad)
            out = buf.getvalue() + err.getvalue()
            self.assertTrue(
                "Invalid tracker.specIds" in out or "Expected one of" in out,
                f"bad={bad!r} out={out!r}",
            )

    def test_spec_ids_write_accepts_flow_and_tracker(self) -> None:
        import argparse
        import io
        from contextlib import redirect_stdout

        self.flowctl.set_config("tracker.enabled", False)
        for good in ("flow", "tracker"):
            ns = argparse.Namespace(key="tracker.specIds", value=good, json=True)
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.flowctl.cmd_config_set(ns)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["value"], good)
            on_disk = json.loads(
                (self.tmpdir / ".flow" / "config.json").read_text(encoding="utf-8")
            )
            self.assertEqual(on_disk["tracker"]["specIds"], good)

    def test_spec_ids_read_fail_closed_to_flow(self) -> None:
        """READ contract: malformed on-disk value fails closed to 'flow'."""
        for bad in (True, False, "yes", "on", "fn", "TRACKER", 1, None):
            self._write_config({"tracker": {"specIds": bad}})
            self.assertEqual(
                self.flowctl.get_config("tracker.specIds"),
                "flow",
                f"malformed {bad!r} must fail closed to flow",
            )
        # Only the literal "tracker" activates.
        self._write_config({"tracker": {"specIds": "tracker"}})
        self.assertEqual(self.flowctl.get_config("tracker.specIds"), "tracker")
        self._write_config({"tracker": {"specIds": "flow"}})
        self.assertEqual(self.flowctl.get_config("tracker.specIds"), "flow")

    def test_spec_ids_unset_detectable_after_init(self) -> None:
        """R9: init does NOT materialize tracker.specIds — raw probe is null."""
        import argparse
        import io
        from contextlib import redirect_stdout

        # Fresh init via cmd_init.
        (self.tmpdir / ".flow").mkdir(parents=True, exist_ok=True)
        ns = argparse.Namespace(json=True)
        with redirect_stdout(io.StringIO()):
            self.flowctl.cmd_init(ns)
        on_disk = json.loads(
            (self.tmpdir / ".flow" / "config.json").read_text(encoding="utf-8")
        )
        self.assertNotIn(
            "specIds",
            on_disk.get("tracker", {}),
            "materialized default would break setup unset-detection",
        )
        # Raw probe: absent → sentinel / None via --raw path.
        raw = self.flowctl._get_config_from_file("tracker.specIds")
        self.assertIs(raw, self.flowctl._CONFIG_RAW_SENTINEL)
        # Merged read still returns the default.
        self.assertEqual(self.flowctl.get_config("tracker.specIds"), "flow")

    def test_spec_ids_explicit_flow_survives_as_set(self) -> None:
        """Answered 'flow' must stay distinguishable from unset (raw non-null)."""
        self.flowctl.set_config("tracker.specIds", "flow")
        raw = self.flowctl._get_config_from_file("tracker.specIds")
        self.assertEqual(raw, "flow")
        self.assertIsNot(raw, self.flowctl._CONFIG_RAW_SENTINEL)


class SyntheticTrackerMintTestCase(unittest.TestCase):
    """fn-134.2 / R14: synthetic gh/gl minting + reservation + preflight."""

    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        import subprocess

        subprocess.run(
            ["git", "init", "-q"], cwd=self.tmpdir, check=True, capture_output=True
        )
        self.flowctl = _load_flowctl()
        self.flow_dir = self.tmpdir / ".flow"
        import argparse
        import io
        from contextlib import redirect_stdout

        with redirect_stdout(io.StringIO()):
            self.flowctl.cmd_init(argparse.Namespace(json=True))

    def tearDown(self) -> None:
        os.chdir(self.prev_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _call(self, func, **kwargs) -> dict:
        import argparse
        import io
        from contextlib import redirect_stdout

        kwargs.setdefault("json", True)
        ns = argparse.Namespace(**kwargs)
        buf = io.StringIO()
        with redirect_stdout(buf):
            func(ns)
        out = buf.getvalue().strip()
        return json.loads(out) if out else {}

    def _create(self, title: str, **kw) -> dict:
        return self._call(
            self.flowctl.cmd_spec_create,
            title=title,
            branch=kw.get("branch"),
            tracker_first=kw.get("tracker_first", False),
            tracker_identifier=kw.get("tracker_identifier"),
        )

    def test_github_mints_gh_slug(self) -> None:
        self.flowctl.set_config("tracker.type", "github")
        res = self._create(
            "Fix login", tracker_first=True, tracker_identifier="#123"
        )
        self.assertEqual(res["id"], "gh-123-fix-login")
        self.assertEqual(res["tracker_identifier"], "#123")
        # Bare alias resolves like wor-17.
        expanded = self.flowctl.expand_bare_spec_id(self.flow_dir, "gh-123")
        self.assertEqual(expanded, "gh-123-fix-login")

    def test_gitlab_mints_gl_slug_from_project_iid(self) -> None:
        self.flowctl.set_config("tracker.type", "gitlab")
        res = self._create(
            "Pipeline fix",
            tracker_first=True,
            tracker_identifier="group/subgroup/project#456",
        )
        # Project-scoped iid 456 — never an opaque global id.
        self.assertEqual(res["id"], "gl-456-pipeline-fix")
        self.assertEqual(res["tracker_identifier"], "group/subgroup/project#456")
        expanded = self.flowctl.expand_bare_spec_id(self.flow_dir, "gl-456")
        self.assertEqual(expanded, "gl-456-pipeline-fix")

    def test_linear_native_gh_key_no_synthesis(self) -> None:
        """Linear team key GH is unchanged — no synthesis, no reservation."""
        self.flowctl.set_config("tracker.type", "linear")
        res = self._create(
            "From linear", tracker_first=True, tracker_identifier="GH-99"
        )
        self.assertEqual(res["id"], "gh-99-from-linear")
        self.assertEqual(res["tracker_identifier"], "GH-99")

    def test_github_reserves_gh_prefix_at_create(self) -> None:
        import io
        from contextlib import redirect_stderr

        self.flowctl.set_config("tracker.type", "github")
        with self.assertRaises(SystemExit):
            with redirect_stderr(io.StringIO()):
                self._create(
                    "Native key",
                    tracker_first=True,
                    tracker_identifier="GH-123",
                )

    def test_github_reserves_gh_prefix_at_link(self) -> None:
        import io
        from contextlib import redirect_stderr

        self.flowctl.set_config("tracker.type", "github")
        # Flow-first spec, then try to link with reserved GH-N.
        res = self._create("Plain")
        with self.assertRaises(SystemExit):
            with redirect_stderr(io.StringIO()):
                self._call(
                    self.flowctl.cmd_sync_set_tracker_id,
                    id=res["id"],
                    tracker_id="uuid-1",
                    identifier="GH-55",
                    url=None,
                    force=False,
                )

    def test_mixed_historical_store_preflight_refuses_collision(self) -> None:
        """gh-123 from Linear predate + re-point to GitHub must not silent-collide."""
        import argparse
        import io
        from contextlib import redirect_stdout

        # Historical Linear-keyed GH mint.
        self.flowctl.set_config("tracker.type", "linear")
        historical = self._create(
            "Old linear", tracker_first=True, tracker_identifier="GH-123"
        )
        self.assertEqual(historical["id"], "gh-123-old-linear")

        # Re-point to GitHub and try to mint issue 123.
        self.flowctl.set_config("tracker.type", "github")
        buf = io.StringIO()
        with self.assertRaises(SystemExit):
            with redirect_stdout(buf):
                self.flowctl.cmd_spec_create(
                    argparse.Namespace(
                        title="New github issue",
                        branch=None,
                        tracker_first=True,
                        tracker_identifier="#123",
                        json=True,
                    )
                )
        payload = json.loads(buf.getvalue())
        self.assertFalse(payload.get("success", True))
        msg = payload.get("error", "")
        self.assertIn("Refusing to mint", msg)
        self.assertIn("gh-123-old-linear", msg)

    def test_hash_n_alias_does_not_block_an_unrelated_native_mint(self) -> None:
        """A stored `#123` must not collide with a native `WOR-123` mint.

        Found by PR review on #241. The `#N` display form belongs only to a
        synthetic gh/gl mint, where `gh-123` and `#123` name the same issue.
        A repo that used GitHub flow-first and later re-pointed to Linear has
        old specs stored as `#123`; those must not block an unrelated
        `WOR-123`, which is a different tracker issue entirely.
        """
        import argparse
        import io
        from contextlib import redirect_stdout

        # Flow-first spec linked to GitHub issue 123 (display-only identifier).
        self.flowctl.set_config("tracker.type", "github")
        flow_first = self._create("Old github linked")
        self.flowctl.cmd_sync_set_tracker_id(
            argparse.Namespace(
                id=flow_first["id"], tracker_id="I_1", identifier="#123",
                url="https://example/123", json=True,
            )
        )

        # Re-point to Linear and mint the unrelated WOR-123.
        self.flowctl.set_config("tracker.type", "linear")
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.flowctl.cmd_spec_create(
                argparse.Namespace(
                    title="Unrelated linear issue", branch=None,
                    tracker_first=True, tracker_identifier="WOR-123", json=True,
                )
            )
        payload = json.loads(buf.getvalue())
        self.assertTrue(
            payload.get("success"),
            f"WOR-123 must not be blocked by an unrelated stored #123: {payload}",
        )
        self.assertEqual(payload["id"], "wor-123-unrelated-linear-issue")

    def test_native_gh_keyed_tracker_is_not_treated_as_synthetic(self) -> None:
        """A Linear project legitimately keyed `GH` mints natively (PR #241).

        The first fix gated on the key string, so `gh-123` looked synthetic even
        when tracker.type was linear - and an unrelated historical `#123` blocked
        it. The gate must confirm tracker.type is the GitHub/GitLab source.
        """
        import argparse
        import io
        from contextlib import redirect_stdout

        self.flowctl.set_config("tracker.type", "github")
        flow_first = self._create("Old github linked")
        self.flowctl.cmd_sync_set_tracker_id(
            argparse.Namespace(
                id=flow_first["id"], tracker_id="I_1", identifier="#123",
                url="https://example/123", json=True,
            )
        )

        # Linear team whose native key happens to be GH.
        self.flowctl.set_config("tracker.type", "linear")
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.flowctl.cmd_spec_create(
                argparse.Namespace(
                    title="Native gh keyed", branch=None, tracker_first=True,
                    tracker_identifier="GH-123", json=True,
                )
            )
        payload = json.loads(buf.getvalue())
        self.assertTrue(
            payload.get("success"),
            f"native GH-123 must not be blocked by an unrelated stored #123: {payload}",
        )

    def test_gitlab_project_qualified_ref_collides_with_a_gl_mint(self) -> None:
        """A stored `group/project#12` must block minting `gl-12` (PR #241).

        The stored reference never equals a bare alias, so preflight missed it
        and a duplicate local spec was written before the UUID attach noticed.
        """
        import argparse
        import io
        from contextlib import redirect_stdout

        self.flowctl.set_config("tracker.type", "gitlab")
        flow_first = self._create("Already linked gitlab")
        self.flowctl.cmd_sync_set_tracker_id(
            argparse.Namespace(
                id=flow_first["id"], tracker_id="I_gl", identifier="group/project#12",
                url="https://example/12", json=True,
            )
        )

        buf = io.StringIO()
        with self.assertRaises(SystemExit):
            with redirect_stdout(buf):
                self.flowctl.cmd_spec_create(
                    argparse.Namespace(
                        title="Duplicate gitlab mint", branch=None,
                        tracker_first=True, tracker_identifier="group/project#12",
                        json=True,
                    )
                )
        payload = json.loads(buf.getvalue())
        self.assertFalse(payload.get("success", True))
        self.assertIn("Refusing to mint", payload.get("error", ""))

    def test_parse_issue_ref_for_mint_shapes(self) -> None:
        self.assertEqual(
            self.flowctl.parse_issue_ref_for_mint("#123"), (123, "#123")
        )
        self.assertEqual(
            self.flowctl.parse_issue_ref_for_mint("owner/repo#9"),
            (9, "owner/repo#9"),
        )
        self.assertEqual(
            self.flowctl.parse_issue_ref_for_mint("group/sub/project#456"),
            (456, "group/sub/project#456"),
        )
        self.assertEqual(
            self.flowctl.parse_issue_ref_for_mint("42"), (42, "#42")
        )
        for bad in ("#0", "#01", "WOR-17", "", None, "a//b#1"):
            self.assertIsNone(self.flowctl.parse_issue_ref_for_mint(bad), bad)


if __name__ == "__main__":
    unittest.main()
