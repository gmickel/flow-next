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

Plus: `config set` round-trips for the string enum and the integer knob
(set_config auto-coerces digits), the explicit-empty-disables case, the
no-clobber-of-siblings invariant, and the new top-level `land.*` namespace
does not clash with existing blocks. Static assertions over workflow.md
§2.6 back the comment-scan detection (no host-agent bash harness exists —
see CommentScanWorkflowStaticTestCase). Mirrors test_work_delegate_config.py.
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
        # land.* is its own top-level block, distinct from work.* and
        # tracker.* — no shared keys leak across.
        self.assertIn("land", defaults)
        self.assertIn("work", defaults)
        self.assertNotIn("release", defaults["work"])
        self.assertNotIn("delegate", defaults["land"])

    def test_setting_land_key_does_not_clobber_work_defaults(self) -> None:
        self._run_config_set_cli("land.reviewSignal", "approve")
        self.assertEqual(
            self._run_config_get_cli("work.delegateModel")["value"], "gpt-5.6-terra"
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


if __name__ == "__main__":
    unittest.main()
