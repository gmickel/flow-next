"""Unit tests for the /flow-next:land config surface (fn-60.2 R15, fn-65.1 R5).

`get_default_config()` carries a top-level `land` block so
`flowctl config get land.*` returns the spec defaults (NOT `null`) on a
fresh repo, WITHOUT any prior `config set`:

  * land.release                  → True
  * land.patienceMinutes          → 30
  * land.reviewSignal             → "silence"  (enum: silence | approve | <github-login>)
  * land.automatedReviewers       → ""         (csv; empty = `[bot]`-suffix rule only)
  * land.reviewTrigger            → ""         (one-shot draft review nudge; empty = never post)
  * land.ciFixBudget              → 3
  * land.cleanReviewCommentPattern → structured ERE (fn-65.1) — the
        silence-signal clean-review COMMENT path. CONTRACT:
        null/missing → workflow falls back to the built-in default;
        explicit ""  → comment scan DISABLED (the real off-switch,
                       distinct from the seeded default);
        other value  → used verbatim.
  * land.mergeVerdictCommand → ""  (fn-188) — the opt-in repo
        merge-verdict gate. CONTRACT: unset, null, AND "" all mean OFF
        (byte-for-byte today's behavior); any other value is a shell
        command run as the fail-closed merge gate of record. Deliberately
        NOT the null-vs-"" asymmetry of cleanReviewCommentPattern.
  * land.requestReviewers → ""  (fn-200, #359) — opt-in human reviewer
        request: csv of GitHub logins / `org/team` slugs and/or the
        literal `codeowners`. CONTRACT: unset, null, AND "" all mean OFF;
        one-shot per PR per head SHA; never gates a merge.

Plus: `config set` round-trips for the string enum and the integer knob
(set_config auto-coerces digits), the explicit-empty-disables case, the
no-clobber-of-siblings invariant, and the new top-level `land.*` namespace
does not clash with existing blocks. Static assertions over workflow.md
§2.6 back the comment-scan detection (no host-agent bash harness exists —
see CommentScanWorkflowStaticTestCase).
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

# fn-139.1: the tracker package sits beside flowctl.py; under a test module
# sys.path[0] is THIS directory, not scripts/, so it would not import.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_land_config_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class LandConfigDefaultsTestCase(unittest.TestCase):
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

    def _run_config_get_cli(self, key: str, *extra: str) -> dict:
        """Invoke cmd_config_get via the argparse namespace; capture JSON stdout."""
        ns = argparse.Namespace(key=key, json=True, raw="--raw" in extra)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.flowctl.cmd_config_get(ns)
        return json.loads(buf.getvalue())

    def _run_config_set_cli(self, key: str, value: str) -> dict:
        ns = argparse.Namespace(key=key, value=value, json=True)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.flowctl.cmd_config_set(ns)
        return json.loads(buf.getvalue())

    # ── Defaults: present in get_default_config() ────────────────────────

    def test_defaults_dict_has_land_block(self) -> None:
        defaults = self.flowctl.get_default_config()
        self.assertIn("land", defaults)
        self.assertEqual(
            defaults["land"],
            {
                "release": True,
                "patienceMinutes": 30,
                "reviewSignal": "silence",
                "automatedReviewers": "",
                "reviewTrigger": "",
                "ciFixBudget": 3,
                "cleanReviewCommentPattern": (
                    r"(Didn'?t find any( major)? issues"
                    r"|No( major)? issues found).*Reviewed commit"
                ),
                "mergeVerdictCommand": "",
                "requestReviewers": "",
            },
        )

    # ── Defaults: surfaced via `config get --json` on a FRESH repo ───────
    # No config.json on disk and no prior `config set` — the merge must
    # return the spec defaults, NOT null.

    def test_fresh_get_release_is_true(self) -> None:
        out = self._run_config_get_cli("land.release")
        self.assertIs(out["value"], True)

    def test_fresh_get_patience_minutes_is_30(self) -> None:
        out = self._run_config_get_cli("land.patienceMinutes")
        self.assertEqual(out["value"], 30)
        self.assertIsInstance(out["value"], int)

    def test_fresh_get_review_signal_is_silence(self) -> None:
        # The spec's quick-command check: `config get land.reviewSignal --json`
        # → "silence" on a fresh repo, not null.
        out = self._run_config_get_cli("land.reviewSignal")
        self.assertEqual(out["value"], "silence")

    def test_fresh_get_automated_reviewers_is_empty_csv(self) -> None:
        # Empty string (csv allowlist), NOT null — empty means the
        # `[bot]`-suffix rule alone identifies automated reviewers.
        out = self._run_config_get_cli("land.automatedReviewers")
        self.assertEqual(out["value"], "")
        self.assertIsNotNone(out["value"])

    def test_fresh_get_ci_fix_budget_is_3(self) -> None:
        out = self._run_config_get_cli("land.ciFixBudget")
        self.assertEqual(out["value"], 3)
        self.assertIsInstance(out["value"], int)

    # ── set round-trips (no new flowctl command needed) ──────────────────
    # set_config already takes arbitrary nested dot-paths; the only change
    # is the defaults block, so `set` + `get` round-trips with no whitelist.

    def test_set_review_signal_approve_round_trips(self) -> None:
        set_out = self._run_config_set_cli("land.reviewSignal", "approve")
        self.assertEqual(set_out["value"], "approve")
        get_out = self._run_config_get_cli("land.reviewSignal")
        self.assertEqual(get_out["value"], "approve")

    def test_set_review_signal_named_reviewer_round_trips(self) -> None:
        # The enum's third arm is an arbitrary GitHub login.
        self._run_config_set_cli("land.reviewSignal", "gmickel")
        get_out = self._run_config_get_cli("land.reviewSignal")
        self.assertEqual(get_out["value"], "gmickel")

    def test_set_patience_minutes_coerces_to_int(self) -> None:
        # set_config auto-coerces digit strings.
        self._run_config_set_cli("land.patienceMinutes", "45")
        get_out = self._run_config_get_cli("land.patienceMinutes")
        self.assertEqual(get_out["value"], 45)
        self.assertIsInstance(get_out["value"], int)

    def test_set_release_false_string_coerces_to_bool(self) -> None:
        self._run_config_set_cli("land.release", "false")
        get_out = self._run_config_get_cli("land.release")
        self.assertIs(get_out["value"], False)

    def test_set_one_land_key_keeps_sibling_defaults(self) -> None:
        # Writing one land.* key must not clobber the other seeded defaults
        # (deep_merge keeps the rest of the block).
        self._run_config_set_cli("land.reviewSignal", "approve")
        self.assertEqual(
            self._run_config_get_cli("land.ciFixBudget")["value"], 3
        )
        self.assertEqual(
            self._run_config_get_cli("land.patienceMinutes")["value"], 30
        )
        self.assertIs(self._run_config_get_cli("land.release")["value"], True)

    # ── Namespace coexistence ─────────────────────────────────────────────

    def test_land_block_does_not_clash_with_existing_blocks(self) -> None:
        defaults = self.flowctl.get_default_config()
        # land.* is its own top-level block, distinct from pipeline.* and
        # tracker.* — no shared keys leak across.
        self.assertIn("land", defaults)
        self.assertIn("pipeline", defaults)
        self.assertNotIn("release", defaults["pipeline"])
        self.assertNotIn("qa", defaults["land"])

    def test_setting_land_key_does_not_clobber_sibling_defaults(self) -> None:
        self._run_config_set_cli("land.reviewSignal", "approve")
        self.assertEqual(
            self._run_config_get_cli("pipeline.qa")["value"], "off"
        )

    # ── fn-65.1: land.cleanReviewCommentPattern (R5) ─────────────────────

    # The structured built-in default — kept in one place so the assertions
    # below and the workflow.md fallback literal stay in lockstep.
    EXPECTED_CLEAN_PATTERN = (
        r"(Didn'?t find any( major)? issues"
        r"|No( major)? issues found).*Reviewed commit"
    )

    def test_clean_review_pattern_seeded_default_present(self) -> None:
        # Seeded in get_default_config() and surfaced (NOT null) on a fresh
        # repo via the defaults merge.
        defaults = self.flowctl.get_default_config()
        self.assertEqual(
            defaults["land"]["cleanReviewCommentPattern"],
            self.EXPECTED_CLEAN_PATTERN,
        )
        out = self._run_config_get_cli("land.cleanReviewCommentPattern")
        self.assertEqual(out["value"], self.EXPECTED_CLEAN_PATTERN)
        self.assertIsNotNone(out["value"])
        self.assertNotEqual(out["value"], "")

    def test_clean_review_pattern_is_structured_not_bare(self) -> None:
        # The contract demands a STRUCTURED ERE: a clean phrase AND the
        # `Reviewed commit` marker, never a bare "no issues" match. Assert
        # both halves are present so a future edit can't silently weaken it
        # to a bare phrase.
        pat = self.flowctl.get_default_config()["land"]["cleanReviewCommentPattern"]
        self.assertIn("Reviewed commit", pat)
        self.assertTrue(
            ("find any" in pat) or ("issues found" in pat),
            "default must carry a clean-review phrase",
        )

    def test_clean_review_pattern_matches_real_codex_comment(self) -> None:
        # Behavioral anchor: the seeded ERE actually matches a real Codex
        # clean-review comment AND rejects a stale/no-clean comment. (Python
        # `re` is a reasonable proxy for the workflow's `grep -Ei`.)
        import re

        pat = self.flowctl.get_default_config()["land"]["cleanReviewCommentPattern"]
        rx = re.compile(pat, re.IGNORECASE)
        self.assertTrue(
            rx.search(
                "Codex Review: Didn't find any major issues. "
                "**Reviewed commit:** `8ff0e50f46`"
            )
        )
        self.assertTrue(rx.search("No issues found. Reviewed commit: deadbeef0"))
        # clean phrase but no marker → no match
        self.assertIsNone(rx.search("Didn't find any major issues here."))
        # marker but no clean phrase → no match
        self.assertIsNone(
            rx.search("Reviewed commit: 1234567 — requesting changes")
        )

    def test_fresh_get_clean_review_pattern_is_default_not_null(self) -> None:
        out = self._run_config_get_cli("land.cleanReviewCommentPattern")
        self.assertEqual(out["value"], self.EXPECTED_CLEAN_PATTERN)

    def test_set_clean_review_pattern_round_trips(self) -> None:
        custom = r"LGTM.*Reviewed commit"
        set_out = self._run_config_set_cli(
            "land.cleanReviewCommentPattern", custom
        )
        self.assertEqual(set_out["value"], custom)
        get_out = self._run_config_get_cli("land.cleanReviewCommentPattern")
        self.assertEqual(get_out["value"], custom)

    def test_explicit_empty_string_disables_distinct_from_default(self) -> None:
        # THE off-switch (R5): an explicit "" must read back as "" — NOT
        # silently coerced back to the seeded default. This is what lets a
        # user actually turn the comment path off; an "empty → default"
        # fallback would make the feature un-disableable.
        set_out = self._run_config_set_cli("land.cleanReviewCommentPattern", "")
        self.assertEqual(set_out["value"], "")
        get_out = self._run_config_get_cli("land.cleanReviewCommentPattern")
        self.assertEqual(get_out["value"], "")
        # explicitly distinct from the seeded structured default
        self.assertNotEqual(get_out["value"], self.EXPECTED_CLEAN_PATTERN)

    def test_set_clean_review_pattern_keeps_sibling_land_defaults(self) -> None:
        # Writing the new key must not clobber the other seeded land.* keys
        # (deep_merge keeps the rest of the block) — and vice-versa: setting
        # a sibling must not drop the clean-review default.
        self._run_config_set_cli("land.cleanReviewCommentPattern", "")
        self.assertEqual(
            self._run_config_get_cli("land.ciFixBudget")["value"], 3
        )
        self.assertEqual(
            self._run_config_get_cli("land.reviewSignal")["value"], "silence"
        )
        self.assertIs(self._run_config_get_cli("land.release")["value"], True)

    def test_set_sibling_keeps_clean_review_pattern_default(self) -> None:
        self._run_config_set_cli("land.reviewSignal", "approve")
        self.assertEqual(
            self._run_config_get_cli("land.cleanReviewCommentPattern")["value"],
            self.EXPECTED_CLEAN_PATTERN,
        )

    # ── fn-188: land.mergeVerdictCommand (R1) ────────────────────────────

    def test_merge_verdict_command_seeded_default_is_empty(self) -> None:
        # Seeded as "" (OFF) so a fresh repo behaves byte-for-byte as before
        # the gate existed — and surfaces as "" via the defaults merge, not
        # as a missing key.
        defaults = self.flowctl.get_default_config()
        self.assertEqual(defaults["land"]["mergeVerdictCommand"], "")

    def test_fresh_get_merge_verdict_command_is_empty_not_null(self) -> None:
        out = self._run_config_get_cli("land.mergeVerdictCommand")
        self.assertEqual(out["value"], "")
        self.assertIsNotNone(out["value"])

    def test_set_merge_verdict_command_round_trips(self) -> None:
        cmd = "scripts/merge-verdict.sh"
        set_out = self._run_config_set_cli("land.mergeVerdictCommand", cmd)
        self.assertEqual(set_out["value"], cmd)
        get_out = self._run_config_get_cli("land.mergeVerdictCommand")
        self.assertEqual(get_out["value"], cmd)

    def test_set_merge_verdict_command_empty_reads_back_empty(self) -> None:
        # All three off-states (unset / null / "") mean OFF — an explicit ""
        # must NOT be coerced into anything else. Unlike
        # cleanReviewCommentPattern, "" here is not a distinct mode; it is
        # simply the same OFF as unset.
        self._run_config_set_cli("land.mergeVerdictCommand", "make verdict")
        set_out = self._run_config_set_cli("land.mergeVerdictCommand", "")
        self.assertEqual(set_out["value"], "")
        self.assertEqual(
            self._run_config_get_cli("land.mergeVerdictCommand")["value"], ""
        )

    def test_set_merge_verdict_command_keeps_sibling_land_defaults(self) -> None:
        self._run_config_set_cli("land.mergeVerdictCommand", "make verdict")
        self.assertEqual(
            self._run_config_get_cli("land.ciFixBudget")["value"], 3
        )
        self.assertEqual(
            self._run_config_get_cli("land.reviewSignal")["value"], "silence"
        )
        self.assertIs(self._run_config_get_cli("land.release")["value"], True)
        self.assertEqual(
            self._run_config_get_cli("land.cleanReviewCommentPattern")["value"],
            self.EXPECTED_CLEAN_PATTERN,
        )

    def test_set_sibling_keeps_merge_verdict_command_default(self) -> None:
        self._run_config_set_cli("land.reviewSignal", "approve")
        self.assertEqual(
            self._run_config_get_cli("land.mergeVerdictCommand")["value"], ""
        )

    def test_docstring_lists_merge_verdict_command_key(self) -> None:
        import sys as _sys

        module_doc = _sys.modules[__name__].__doc__ or ""
        self.assertIn("mergeVerdictCommand", module_doc)
        self.assertIn("all mean OFF", module_doc)

    # ── fn-200: land.requestReviewers (R1, R3) ───────────────────────────

    def test_request_reviewers_seeded_default_is_empty(self) -> None:
        # Seeded "" (OFF) so the default tick is byte-for-byte unchanged
        # (R3) and the key surfaces via the defaults merge, not as missing.
        defaults = self.flowctl.get_default_config()
        self.assertEqual(defaults["land"]["requestReviewers"], "")

    def test_fresh_get_request_reviewers_is_empty_not_null(self) -> None:
        out = self._run_config_get_cli("land.requestReviewers")
        self.assertEqual(out["value"], "")
        self.assertIsNotNone(out["value"])

    def test_set_request_reviewers_round_trips_csv(self) -> None:
        csv = "alice,acme/platform,codeowners"
        set_out = self._run_config_set_cli("land.requestReviewers", csv)
        self.assertEqual(set_out["value"], csv)
        get_out = self._run_config_get_cli("land.requestReviewers")
        self.assertEqual(get_out["value"], csv)

    def test_set_request_reviewers_empty_reads_back_empty(self) -> None:
        # unset / null / "" all mean OFF — an explicit "" resets, never
        # coerced into anything else.
        self._run_config_set_cli("land.requestReviewers", "alice")
        set_out = self._run_config_set_cli("land.requestReviewers", "")
        self.assertEqual(set_out["value"], "")
        self.assertEqual(
            self._run_config_get_cli("land.requestReviewers")["value"], ""
        )

    def test_set_request_reviewers_keeps_sibling_land_defaults(self) -> None:
        self._run_config_set_cli("land.requestReviewers", "alice")
        self.assertEqual(
            self._run_config_get_cli("land.ciFixBudget")["value"], 3
        )
        self.assertEqual(
            self._run_config_get_cli("land.reviewSignal")["value"], "silence"
        )
        self.assertEqual(
            self._run_config_get_cli("land.mergeVerdictCommand")["value"], ""
        )

    def test_set_sibling_keeps_request_reviewers_default(self) -> None:
        self._run_config_set_cli("land.reviewSignal", "approve")
        self.assertEqual(
            self._run_config_get_cli("land.requestReviewers")["value"], ""
        )

    def test_docstring_lists_request_reviewers_key(self) -> None:
        import sys as _sys

        module_doc = _sys.modules[__name__].__doc__ or ""
        self.assertIn("requestReviewers", module_doc)
        self.assertIn("codeowners", module_doc)

    def test_docstring_lists_clean_review_pattern_key(self) -> None:
        # The module docstring is the human-facing key inventory; keep the
        # new key (and its contract verb) discoverable there.
        import sys as _sys

        module_doc = _sys.modules[__name__].__doc__ or ""
        self.assertIn("cleanReviewCommentPattern", module_doc)
        self.assertIn("DISABLED", module_doc)


class CommentScanWorkflowStaticTestCase(unittest.TestCase):
    """Static assertions over flow-next-land/workflow.md §2.6 (fn-65.1).

    Honest harness limitation: the clean-review COMMENT scan is host-agent
    BASH inside the skill workflow, not flowctl Python — there is no
    executable test harness for it (no `gh` API, no host agent in CI). So we
    pin the load-bearing invariants of the snippet by asserting the workflow
    PROSE/snippet contains them. These guard against silent regressions
    (e.g. the scan losing its `silence` gate, or the SHA empty-guard being
    dropped into a `==$var*`-on-empty footgun) that a behavioral test would
    otherwise catch.
    """

    @classmethod
    def setUpClass(cls) -> None:
        wf = (
            HERE.parent.parent
            / "skills"
            / "flow-next-land"
            / "workflow.md"
        )
        cls.text = wf.read_text(encoding="utf-8")
        # The §2.6 comment-scan region: from the silence-gated `if` to the
        # `issues/<n>/comments` GET. Slicing keeps the gate/guard assertions
        # scoped to the actual scan, not an incidental mention elsewhere.
        start = cls.text.find('if [[ "$REVIEW_SIGNAL" == "silence"')
        end = cls.text.find("issues/$PR_NUMBER/comments", start)
        assert start != -1 and end != -1, "comment-scan block not found in workflow.md"
        cls.scan = cls.text[start : end + 200]

    def test_comment_scan_uses_paginated_issue_comments_get(self) -> None:
        self.assertIn("--paginate", self.scan)
        self.assertIn("issues/$PR_NUMBER/comments", self.scan)
        # read-only GET (dry-run-safe) — never a POST/comment-create here
        self.assertNotIn("gh pr comment", self.scan)

    def test_comment_scan_gated_on_silence_signal(self) -> None:
        # The scan must be hard-gated on REVIEW_SIGNAL == silence (not run on
        # approve/<login>), AND on a non-empty pattern (explicit "" disables).
        self.assertIn('"$REVIEW_SIGNAL" == "silence"', self.scan)
        self.assertIn('-n "$CLEAN_REVIEW_PATTERN"', self.scan)

    def test_comment_scan_runs_before_draft_trigger(self) -> None:
        # Ordering invariant: the comment scan sets AUTO_REVIEW_CURRENT=1
        # which the draft-trigger branch reads, so the scan MUST appear
        # before the draft-trigger paragraph in the file.
        scan_pos = self.text.find('if [[ "$REVIEW_SIGNAL" == "silence"')
        trigger_pos = self.text.find("**Draft-PR review trigger")
        self.assertNotEqual(scan_pos, -1)
        self.assertNotEqual(trigger_pos, -1)
        self.assertLess(scan_pos, trigger_pos)

    def test_comment_scan_sha_guard_is_non_empty_and_min_length(self) -> None:
        # The SHA token must be empty-guarded AND min-length-guarded before
        # the prefix test — no `[[ $HEAD_OID == $token* ]]`-on-empty footgun.
        self.assertIn('-n "$token"', self.scan)
        self.assertIn("${#token} -ge 7", self.scan)
        # the prefix test compares the lowercased head against the token
        self.assertIn('"$HEAD_LC" == "$token"*', self.scan)
        # hex-token extraction with the documented ERE
        self.assertIn("[0-9a-fA-F]{7,40}", self.scan)

    def test_comment_scan_only_sets_never_resets_current(self) -> None:
        # Invariant: the scan only ever SETS AUTO_REVIEW_CURRENT=1, never
        # back to 0 (it must not clobber a reviews-API result).
        self.assertIn("AUTO_REVIEW_CURRENT=1", self.scan)
        self.assertNotIn("AUTO_REVIEW_CURRENT=0", self.scan)

    def test_comment_scan_sets_observability_vars(self) -> None:
        self.assertIn("AUTO_REVIEW_SOURCE=comment", self.scan)
        self.assertIn("AUTO_REVIEW_EVIDENCE=", self.scan)

    def test_cfg_read_distinguishes_null_from_empty(self) -> None:
        # The Phase 0 cfg read must guard ONLY the literal "null" (pre-seed
        # fallback to the built-in default) and NOT collapse "" into the
        # default — `-z`-guarding CLEAN_REVIEW_PATTERN would break the
        # off-switch.
        self.assertIn(
            'if [[ "$CLEAN_REVIEW_PATTERN" == "null" ]]; then', self.text
        )
        self.assertNotIn('-z "$CLEAN_REVIEW_PATTERN"', self.text)


class MergeVerdictGateWorkflowStaticTestCase(unittest.TestCase):
    """Static assertions over flow-next-land/workflow.md §2.9 (fn-188).

    Same honest harness limitation as CommentScanWorkflowStaticTestCase: the
    merge-verdict gate is host-agent BASH inside the skill workflow, not
    flowctl Python. Pin the load-bearing invariants of the section by
    asserting the prose/snippet carries them: the gate exists, it is
    fail-closed, `--dry-run` reports would-run instead of executing, and the
    context env-var names are the documented ones.
    """

    @classmethod
    def setUpClass(cls) -> None:
        wf = HERE.parent.parent / "skills" / "flow-next-land" / "workflow.md"
        cls.text = wf.read_text(encoding="utf-8")
        start = cls.text.find("### 2.9 — Repo merge-verdict gate")
        end = cls.text.find("### Dry-run stops here", start)
        assert start != -1 and end != -1, "§2.9 merge-verdict gate not found"
        cls.gate = cls.text[start:end]

    def test_gate_section_present_between_2_8_and_dry_run_stop(self) -> None:
        pos_28 = self.text.find("### 2.8 — Merge-state gates")
        pos_29 = self.text.find("### 2.9 — Repo merge-verdict gate")
        pos_dry = self.text.find("### Dry-run stops here")
        self.assertNotEqual(pos_28, -1)
        self.assertLess(pos_28, pos_29)
        self.assertLess(pos_29, pos_dry)
        self.assertIn("land.mergeVerdictCommand", self.gate)

    def test_gate_reads_command_off_the_shared_lcfg_capture(self) -> None:
        # No second `config get` probe — the key rides the Phase 0 subtree
        # read (test_skill_prose_diet pins exactly one config get).
        self.assertIn("MERGE_VERDICT_CMD=\"$(lcfg mergeVerdictCommand)\"", self.text)
        self.assertNotIn("config get land.mergeVerdictCommand", self.text)

    def test_gate_is_fail_closed(self) -> None:
        # Missing/unexecutable/timeout/signal all block, never skip.
        self.assertIn("600s tool", self.gate)
        for token in ("124", "127", "128+N"):
            self.assertIn(token, self.gate)

    def test_planned_action_is_assigned_by_the_gate_tree(self) -> None:
        # Both PR bots caught the unassigned-variable bypass: nothing set
        # PLANNED_ACTION, so the gate silently skipped. The assignment
        # instruction must exist between 2.8 and 2.9.
        self.assertIn("PLANNED_ACTION=<the action class planned above>", self.text)

    def test_merge_pins_the_judged_head(self) -> None:
        # TOCTOU: a push after the verdict must refuse at --match-head-commit,
        # not merge an unjudged commit under a refreshed HEAD_OID.
        self.assertIn('HEAD_OID="$MERGE_VERDICT_HEAD"', self.text)
        self.assertIn('MERGE_VERDICT_HEAD="$HEAD_OID"', self.gate)

    def test_gate_refuses_on_non_base_checkout(self) -> None:
        # The command string comes from the working tree's config: on a
        # non-base checkout it is the PR author's text - a self-approval
        # channel. The trust guard must refuse before executing.
        self.assertIn('git rev-parse --abbrev-ref HEAD)" != "$BASE_REF"', self.gate)
        self.assertIn("requires the base checkout", self.gate)

    def test_verdict_pair_is_per_pr_state(self) -> None:
        # Multi-PR ticks: the verdict pair rides each PR's classification
        # record; a later iteration must not clobber an earlier PR's pinned
        # head before 3.5 merges it.
        self.assertIn("MV_STALE_BASE", self.text)
        self.assertIn('HEAD_OID="$MERGE_VERDICT_HEAD"', self.text)

    def test_verdict_binds_head_and_base(self) -> None:
        # A base that moved since judgment (earlier PR merged in the same
        # tick) invalidates the verdict: RESOLVING re-tick, never a merge
        # against an unjudged target.
        self.assertIn("MERGE_VERDICT_BASE=", self.gate)
        self.assertIn('"$BASE_NOW" != "$MERGE_VERDICT_BASE"', self.text)
        # Base bound BEFORE execution; empty resolution refuses, not skips.
        base_bind = self.gate.index("MERGE_VERDICT_BASE=")
        cmd_exec = self.gate.index('bash -c "cd')
        self.assertLess(base_bind, cmd_exec)
        self.assertIn('-z "$MERGE_VERDICT_BASE"', self.gate)
        # Stale base structurally stops the merge (guard wraps gh pr merge).
        self.assertIn('"$MV_STALE_BASE" == 1', self.text)

    def test_gate_refusal_is_needs_human_not_blocked(self) -> None:
        # BLOCKED stays reserved for server-side merge refusals (3.5).
        self.assertIn("NEEDS_HUMAN`, action `none`", self.gate)
        self.assertIn("never `BLOCKED`", self.gate)

    def test_gate_dry_run_reports_would_run_and_never_executes(self) -> None:
        self.assertIn("MERGE_VERDICT=would-run", self.gate)
        self.assertIn('"$LAND_DRY_RUN" == 1', self.gate)
        # the dry-run stop restates it for the classification report
        self.assertIn("mergeVerdict=would-run", self.text)

    def test_gate_passes_context_as_env_vars_only(self) -> None:
        for var in (
            "FLOW_HEAD_SHA",
            "FLOW_BASE_REF",
            "FLOW_PR_NUMBER",
            "FLOW_SPEC_ID",
        ):
            self.assertIn(var, self.gate)
        # wrong-tree trap: the command must key on the PR head, not the tree
        self.assertIn("BASE checkout", self.gate)

    def test_gate_documents_all_three_off_states(self) -> None:
        self.assertIn('`null`, and `""` ALL mean OFF', self.gate)

    def test_phase4_evidence_block_carries_merge_verdict_field(self) -> None:
        self.assertIn("mergeVerdict=<green|refused|skipped|would-run>", self.text)


class RequestReviewersWorkflowStaticTestCase(unittest.TestCase):
    """Static assertions over flow-next-land/workflow.md §2.6b + §3.4b (fn-200).

    Same honest harness limitation as MergeVerdictGateWorkflowStaticTestCase:
    the human reviewer request is host-agent BASH inside the skill workflow,
    not flowctl Python (no stubbed `gh`). Pin the smallest distinctive tokens:
    the gate sits between §2.6 and §2.7 and is read-only, the action class
    lives in Phase 3 with the atomic claim before the ready flip, the config
    rides the single Phase 0 `lcfg` capture, and the report vocabulary exists.
    """

    @classmethod
    def setUpClass(cls) -> None:
        base = HERE.parent.parent
        cls.text = (base / "skills" / "flow-next-land" / "workflow.md").read_text(encoding="utf-8")
        cls.skill = (base / "skills" / "flow-next-land" / "SKILL.md").read_text(encoding="utf-8")
        cls.conduct = (base.parent.parent / "agent_docs" / "conduct" / "land.md").read_text(encoding="utf-8")
        g0 = cls.text.find("### 2.6b — Human reviewer request")
        g1 = cls.text.find("### 2.7 — CI-fix budget", g0)
        assert g0 != -1 and g1 != -1, "§2.6b not found"
        cls.gate = cls.text[g0:g1]
        p3 = cls.text.find("## Phase 3 — ACT")
        p4 = cls.text.find("## Phase 4 — REPORT", p3)
        assert p3 != -1 and p4 != -1
        cls.act = cls.text[p3:p4]
        a0 = cls.act.find("### 3.4b — `request-reviewers`")
        a1 = cls.act.find("### 3.5 — `merge`", a0)
        assert a0 != -1 and a1 != -1, "§3.4b not found inside Phase 3"
        cls.action = cls.act[a0:a1]

    def test_config_rides_the_single_lcfg_capture(self) -> None:
        self.assertIn('REQUEST_REVIEWERS="$(lcfg requestReviewers)"', self.text)
        self.assertNotIn("config get land.requestReviewers", self.text)

    def test_pr_state_capture_includes_author(self) -> None:
        self.assertIn("labels,commits,createdAt,author)", self.text)
        self.assertIn("PR_AUTHOR=", self.text)

    def test_ledger_schema_names_review_request_sha(self) -> None:
        self.assertIn("reviewRequestSha", self.text)
        self.assertIn('.[$pr].reviewRequestSha = $sha', self.action)

    def test_gate_is_between_2_6_and_2_7_and_read_only(self) -> None:
        pos_26 = self.text.find("### 2.6 — Review signal")
        pos_26b = self.text.find("### 2.6b — Human reviewer request")
        pos_27 = self.text.find("### 2.7 — CI-fix budget")
        self.assertLess(pos_26, pos_26b)
        self.assertLess(pos_26b, pos_27)
        for write in ("gh pr ready", "--add-reviewer", "mv \"$tmp\""):
            self.assertNotIn(write, self.gate)
        self.assertIn("PLANNED_ACTION=request-reviewers", self.gate)
        self.assertIn("review-request-claims", self.gate)

    def test_action_claims_atomically_before_ready_flip(self) -> None:
        self.assertIn("review-request-claims", self.action)
        claim = self.action.index('mkdir "$LEDGER_DIR/review-request-claims/')
        ready = self.action.index("gh pr ready")
        request = self.action.index("--add-reviewer")
        ledger = self.action.index(".[$pr].reviewRequestSha = $sha")
        self.assertLess(claim, ready)
        self.assertLess(ready, request)
        self.assertLess(request, ledger)
        # the PR author is filtered out before the call; codeowners never sent explicitly
        self.assertIn('"$t" == "$PR_AUTHOR"', self.action)
        self.assertIn('"$t" == "codeowners"', self.action)
        # claim dirs leave with the PR's ledger entry
        self.assertIn("review-request-claims/${PR_NUMBER}-", self.act[self.act.find("### 3.5"):])

    def test_report_vocabulary(self) -> None:
        self.assertIn(
            "reviewers=<requested|would-request|already:<sha8>|skipped:<reason>|failed:<reason>|off>",
            self.text,
        )
        self.assertIn("REVIEWERS_STATE=off", self.gate)
        self.assertIn("skipped:already-ready, no explicit logins", self.action)
        self.assertIn("failed:", self.action)
        self.assertIn("would-request", self.text[self.text.find("### Dry-run stops here"):])

    def test_skill_and_conduct_carry_the_key(self) -> None:
        self.assertIn("land.requestReviewers", self.skill)
        self.assertIn("request-reviewers", self.skill)
        self.assertIn("land.requestReviewers", self.conduct)


class MergeSeamWorkflowStaticTestCase(unittest.TestCase):
    """Static assertions over §3.5's `FLOW_PR_MERGE_CMD` seam (fn-194 R1, #337).

    Same harness limitation as the other workflow classes: the merge call is
    host-agent BASH inside the skill workflow, not flowctl Python. Pin the
    load-bearing invariants: the seam exists in the #277 shape, the fixed
    argument order survives it, the stderr-proxy requirement is stated (the
    RESOLVING-vs-BLOCKED split reads gh's stderr), no `--auto`/merge-queue,
    and the seam is env-only - never a `land.*` config key.
    """

    @classmethod
    def setUpClass(cls) -> None:
        wf = HERE.parent.parent / "skills" / "flow-next-land" / "workflow.md"
        cls.text = wf.read_text(encoding="utf-8")
        start = cls.text.find("# PR-merge seam (#337)")
        end = cls.text.find("### 3.6", start)
        assert start != -1 and end != -1, "§3.5 merge seam not found"
        cls.seam = cls.text[start:end]

    def test_seam_default_is_gh_pr_merge(self) -> None:
        self.assertIn('MERGE_CMD="${FLOW_PR_MERGE_CMD:-gh pr merge}"', self.text)

    def test_merge_call_goes_through_the_seam_unquoted(self) -> None:
        # Unquoted expansion: whitespace-split, never eval'd (#277 shape).
        self.assertIn(
            'MERGE_ERR="$($MERGE_CMD "$PR_NUMBER" --squash --delete-branch '
            '--match-head-commit "$HEAD_OID" 2>&1 >/dev/null)" || MERGE_RC=$?',
            self.text,
        )
        # The literal pre-seam call is gone - no ungoverned merge path.
        self.assertNotIn('$(gh pr merge "$PR_NUMBER" --squash', self.text)

    def test_contract_states_fixed_argument_order(self) -> None:
        self.assertIn(
            "$FLOW_PR_MERGE_CMD <pr> --squash --delete-branch --match-head-commit <sha>",
            self.seam,
        )
        self.assertIn("never eval'd", self.seam)

    def test_contract_requires_verbatim_stderr(self) -> None:
        # A wrapper that eats stderr converts benign head races into BLOCKED.
        self.assertIn("proxy gh's stderr VERBATIM", self.seam)
        self.assertIn("RESOLVING", self.seam)
        self.assertIn("BLOCKED", self.seam)

    def test_contract_forbids_auto_and_merge_queue(self) -> None:
        self.assertIn("never `--auto`, never merge-queue enrollment", self.seam)
        # The explicit-merge restatement outside the contract block stays.
        self.assertIn("always explicit, never `gh pr merge --auto`", self.seam)

    def test_contract_scopes_the_seam_to_the_merge_call(self) -> None:
        self.assertIn("THIS merge call ONLY", self.seam)
        self.assertIn("session identity", self.seam)
        # --delete-branch is a second permission a merge-only App may lack.
        self.assertIn("--delete-branch` needs a second permission", self.seam)

    def test_seam_is_env_only_never_a_config_key(self) -> None:
        self.assertIn("ENV ONLY", self.seam)
        self.assertNotIn("land.mergeCmd", self.text)
        self.assertNotIn("lcfg mergeCmd", self.text)


class CatchUpWorkflowStaticTestCase(unittest.TestCase):
    """Static assertions over §3.3's server-side catch-up (fn-194 R2, #342).

    The local rebase + `git push --force-with-lease` is gone: BEHIND and DIRTY
    both plan `catch-up`, executed as one `gh pr update-branch` call. Pin the
    invariants that regressions would quietly undo - land has no force-push
    path left (the #302 orphaned-evidence cause), GitHub owns the conflict
    decision (non-zero -> BLOCKED), the ledger sources the new head from the
    API because no local checkout exists, and the action class is spelled
    `catch-up` in every enumeration a reader keys on.
    """

    @classmethod
    def setUpClass(cls) -> None:
        wf = HERE.parent.parent / "skills" / "flow-next-land" / "workflow.md"
        cls.text = wf.read_text(encoding="utf-8")
        start = cls.text.find("### 3.3 — `catch-up`")
        end = cls.text.find("### 3.4", start)
        assert start != -1 and end != -1, "§3.3 catch-up section not found"
        cls.act = cls.text[start:end]
        cls.skill = (
            HERE.parent.parent / "skills" / "flow-next-land" / "SKILL.md"
        ).read_text(encoding="utf-8")

    def test_no_local_rebase_or_force_push_remains(self) -> None:
        # The executable forms, not the prose that explains their absence.
        self.assertNotIn("git push --force-with-lease", self.text)
        self.assertNotIn('git rebase "origin/$BASE_REF"', self.text)
        self.assertNotIn("git rebase --abort\n  git checkout", self.text)
        # The ci-fix path keeps the only `gh pr checkout` in the workflow.
        self.assertEqual(self.text.count('gh pr checkout "$PR_NUMBER"'), 1)

    def test_catch_up_is_one_server_side_update_branch_call(self) -> None:
        self.assertIn(
            'CATCHUP_ERR="$(gh pr update-branch "$PR_NUMBER" 2>&1 >/dev/null)"',
            self.act,
        )
        # Merge-based, never the rebase flag (which would reintroduce SHA rewrites).
        self.assertNotIn("update-branch --rebase", self.text)
        self.assertIn("never passes `--rebase`", self.act)

    def test_non_zero_catch_up_routes_to_blocked(self) -> None:
        # PR #350 review: non-zero classifies from stderr - conflict ->
        # BLOCKED, benign race/transient -> RESOLVING re-tick.
        self.assertIn("CATCHUP_ERR", self.act)
        self.assertIn("BLOCKED", self.act)
        self.assertIn("RESOLVING", self.act)
        # Repeated identical non-conflict failures escalate (PR #350 r2).
        self.assertIn("catch_up_fail", self.act)
        self.assertIn("catch_up_fail", self.act)  # ledger token (dedup: also below)
        self.assertIn("hand-resolution", self.act)

    def test_ledger_sources_new_head_from_the_api(self) -> None:
        # No local checkout exists to read the new head from.
        self.assertIn('gh pr view "$PR_NUMBER" --json headRefOid', self.act)
        self.assertIn("land_pushed_sha", self.act)
        self.assertIn("decision_at_push", self.act)

    def test_both_behind_and_dirty_plan_catch_up(self) -> None:
        gates = self.text[
            self.text.find("### 2.8 — Merge-state gates") : self.text.find("### 2.9")
        ]
        self.assertIn('`MERGE_STATE == "BEHIND"`: plan `catch-up`', gates)
        self.assertIn('`MERGE_STATE == "DIRTY"`: conflict path → plan `catch-up`', gates)
        self.assertNotIn("plan `rebase`", gates)

    def test_action_class_is_renamed_in_every_enumeration(self) -> None:
        self.assertIn(
            "(`merge`, `catch-up`, `ci-fix`, `resolve`, `label`, `resume-tail`, `request-reviewers`, `none`)",
            self.text,
        )
        self.assertIn(
            "action=<ci-fix|resolve|catch-up|merge|resume-tail|label|request-reviewers|none>", self.text
        )
        self.assertNotIn("mechanical rebase", self.skill)
        self.assertIn("server-side catch-up", self.skill)

    def test_force_push_removal_rationale_is_stated(self) -> None:
        self.assertIn("removes land's force-push capability", self.act)
        self.assertIn("#302", self.act)
        self.assertIn("Fork PRs", self.act)


class ReviewSignalOrderingStaticTestCase(unittest.TestCase):
    """§2.6/§2.7 evaluation order under `reviewSignal: approve` (fn-194 R4).

    The ambiguity this pins: whether §2.7's stale-approval detector is
    reachable under `approve` or shadowed by §2.6's earlier non-satisfaction.
    It is reachable - §2.6 assigns a provisional verdict and falls through -
    and the paragraph must keep saying so, because the durable label is what
    breaks the dismissal loop.
    """

    @classmethod
    def setUpClass(cls) -> None:
        wf = HERE.parent.parent / "skills" / "flow-next-land" / "workflow.md"
        cls.text = wf.read_text(encoding="utf-8")

    def test_ordering_paragraph_sits_between_2_6_and_2_7(self) -> None:
        pos_26 = self.text.find("### 2.6 — Review signal")
        pos_para = self.text.find("**§2.6 does not exit the gate tree")
        pos_27 = self.text.find("### 2.7 — CI-fix budget")
        self.assertNotEqual(pos_para, -1, "R4 ordering paragraph missing")
        self.assertLess(pos_26, pos_para)
        self.assertLess(pos_para, pos_27)

    def test_paragraph_states_the_detector_is_reachable(self) -> None:
        para = self.text[
            self.text.find("**§2.6 does not exit the gate tree") : self.text.find(
                "### 2.7 — CI-fix budget"
            )
        ]
        self.assertIn("REACHABLE under `approve`, never shadowed", para)
        self.assertIn("stale-approval dismissal loop detected", para)
        # §2.8 stays the one genuinely conditional gate - semantics unchanged.
        self.assertIn("§2.8", para)
        self.assertIn(
            "### 2.8 — Merge-state gates (only when the review signal is satisfied)",
            self.text,
        )


class PostMergeTailOrderStaticTestCase(unittest.TestCase):
    """§3.5's post-merge tail order (fn-194 R3, #345).

    The bug being pinned out: persisting the close FIRST meant one refused
    push (a base that only accepts pull requests refuses it permanently)
    skipped release-follow AND the tracker touchpoint after a real merge - the
    board stuck at In Review, which is the exact outcome the active-by-default
    `land.merged` projection exists to prevent. The tail now closes locally,
    runs release-follow and the touchpoint, and pushes last, with the rollback
    scoped to the push step alone.
    """

    @classmethod
    def setUpClass(cls) -> None:
        wf = HERE.parent.parent / "skills" / "flow-next-land" / "workflow.md"
        cls.text = wf.read_text(encoding="utf-8")
        start = cls.text.find("### 3.5 — `merge` + post-merge tail")
        end = cls.text.find("### 3.6", start)
        assert start != -1 and end != -1, "§3.5 section not found"
        cls.tail = cls.text[start:end]

    def test_tail_steps_are_numbered_in_the_new_order(self) -> None:
        close = self.tail.index("1. **Spec close")
        release = self.tail.index("2. **Release-follow**")
        tracker = self.tail.index("3. **Tracker touchpoint")
        persist = self.tail.index("4. **Persist —")
        self.assertLess(close, release)
        self.assertLess(release, tracker)
        self.assertLess(tracker, persist)

    def test_the_only_tail_push_comes_after_release_and_tracker(self) -> None:
        push = self.tail.index("git push || { git pull --rebase && git push; }")
        self.assertLess(self.tail.index("2. **Release-follow**"), push)
        self.assertLess(self.tail.index("3. **Tracker touchpoint"), push)
        # Exactly one push line in the tail (`git push || { ... && git push; }`)
        # - the close and the sync state ride it together.
        # 3 mentions: the persist push, the pull-rebase retry, and the
        # release-instructions ride-along note (PR #350 review).
        self.assertEqual(self.tail.count("git push"), 3)

    def test_close_step_commits_without_pushing(self) -> None:
        close = self.tail[
            self.tail.index("1. **Spec close") : self.tail.index("2. **Release-follow**")
        ]
        self.assertIn('git commit -m "chore(flow): close ${spec}', close)
        self.assertNotIn("git push", close)

    def test_tracker_sync_state_commit_does_not_push(self) -> None:
        tracker = self.tail[
            self.tail.index("3. **Tracker touchpoint") : self.tail.index("4. **Persist —")
        ]
        self.assertIn('git commit -m "chore(flow): sync state for ${spec}', tracker)
        self.assertNotIn("git push", tracker)

    def test_rollback_is_scoped_to_the_persist_step(self) -> None:
        persist = self.tail[self.tail.index("4. **Persist —") :]
        self.assertIn('git reset --hard "$TAIL_BASE_OID"', persist)
        self.assertIn("TAIL_BASE_OID=\"$(git rev-parse HEAD)\"", self.tail)
        self.assertIn("scoped to THIS step and skips NOTHING else", persist)
        self.assertIn("spec close not pushed", persist)
        # The old rollback target (one commit back) cannot express two commits.
        self.assertNotIn("git reset --hard HEAD^", self.text)

    def test_re_tick_safety_reasoning_is_stated_inline(self) -> None:
        persist = self.tail[self.tail.index("4. **Persist —") :]
        self.assertIn("idempotency probe", persist)
        self.assertIn("evidence=<merge-commit-sha>", persist)

    def test_release_and_tracker_preconditions_are_stated_at_the_close(self) -> None:
        close = self.tail[
            self.tail.index("1. **Spec close") : self.tail.index("2. **Release-follow**")
        ]
        self.assertIn("clean non-`.flow/` tree", close)
        self.assertIn("fresh GitHub `MERGED` probe", close)

    def test_resume_tail_prose_matches_the_new_order(self) -> None:
        resume = self.text[self.text.find("### 3.6 — `resume-tail`") :]
        self.assertIn(
            "spec close (local commit) → release-follow → tracker touchpoint → persist-push",
            resume,
        )


if __name__ == "__main__":
    unittest.main()
