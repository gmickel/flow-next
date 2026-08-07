"""Cross-platform parity + autonomous-safety contract for fn-68.5 (R12; verifies R6/R7).

fn-68.5 is its OWN task because regenerating the Codex mirror exposes latent
canonical issues — memory ``mirror-regen-exposes-latent-canonical`` (fn-60 took
FOUR NEEDS_WORK rounds from one mirror regen). The mirror is the **rewrite** of
the Claude-native canonical; this test locks the load-bearing invariants of that
rewrite so a later edit to ``sync-codex.sh`` or the canonical pilot/tracker-sync
skills can't silently regress them.

Three families, all **prose contract** (the host agent IS the runtime — there is
no Python engine to unit-test; backlog mode is skill prose the agent executes):

  A. **Cross-platform mirror parity (R12).** ``sync-codex.sh`` regenerated the
     Codex mirror; the tracker-sync R14 Phase-0 autonomy fix, the pilot
     ``triage`` / ``ask`` stages, the ``ASKED`` verdict, and ``backlog-mode.md``
     all survive; ``AskUserQuestion`` is rewritten to the plain-text
     numbered-prompt form; ZERO Claude-native tool-name leakage in the mirror
     prose; the maintainer "regenerated in fn-68.5" breadcrumb is stripped; and
     — the defect this regen first exposed — the R2 numbered-prompt INSTRUCTION
     block is **never** injected into the pilot mirror (pilot only *negates*
     AskUserQuestion, so an injected "ask the user via plain text" block would
     contradict its autonomous-only contract).

  B. **/goal (Codex) driver parity.** The verdict tokens the transcript-blind
     ``/goal`` / ``/loop`` stop-clauses grep on survive verbatim in BOTH the
     canonical and the mirror: ``NO_WORK`` + ``DEFERRED_TO_LAND`` are present and
     grep-able (the loop-stop + land hand-off); ``ASKED`` is the durable park;
     ``TRIAGED`` is documented diagnostic / dry-run-only (never a live terminal).

  C. **Autonomous-safety invariants (verifies R6/R7).** Keyed on tokens, not
     sentences (prose-quality pins removed 2026-08-07 - judged via
     .flow/criteria.md G1, not grep): (1) never prompt — every
     ``AskUserQuestion`` mention in the pilot canonical is a NEGATION;
     (2) never merge / never invoke land — the ``assert_allowed_dispatch``
     allowlist survives in the mirror; (3) never author a spec — the
     ``assert_spec_write_allowed`` guard survives in the mirror; and (4) the
     ``FLOW_AUTONOMOUS`` export is scoped inside the backlog branch.

Run:
    python3 -m unittest plugins.flow-next.tests.test_pilot_backlog_mirror_safety -v
"""

from __future__ import annotations

import json
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN = REPO_ROOT / "plugins" / "flow-next"

# Canonical (Claude-native) pilot skill files.
PILOT = PLUGIN / "skills" / "flow-next-pilot"
PILOT_SKILL = PILOT / "SKILL.md"
PILOT_WORKFLOW = PILOT / "workflow.md"
PILOT_BACKLOG = PILOT / "references" / "backlog-mode.md"
PILOT_QA = PILOT / "references" / "qa-stage.md"
PILOT_LEDGER = REPO_ROOT / "optimization" / "reached-path" / "pilot-candidates.json"

# Canonical tracker-sync (carries the R14 Phase-0 fix from fn-68.2).
TS_STEPS = PLUGIN / "skills" / "flow-next-tracker-sync" / "steps.md"

# The regenerated Codex mirror — the rewrite this task locks.
MIRROR = PLUGIN / "codex" / "skills" / "flow-next-pilot"
MIRROR_SKILL = MIRROR / "SKILL.md"
MIRROR_WORKFLOW = MIRROR / "workflow.md"
MIRROR_BACKLOG = MIRROR / "references" / "backlog-mode.md"
MIRROR_TS_STEPS = (
    PLUGIN / "codex" / "skills" / "flow-next-tracker-sync" / "steps.md"
)

MIRROR_SKILLS_DIR = PLUGIN / "codex" / "skills"

# The R2 numbered-prompt INSTRUCTION block sync-codex.sh injects into skills that
# genuinely ask the user. Its presence in a pilot mirror file is the defect.
R2_INSTRUCTION_SENTINEL = "Render the options below as a"


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


class PilotBacklogMirrorSafety(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        required = [
            PILOT_SKILL,
            PILOT_WORKFLOW,
            PILOT_BACKLOG,
            PILOT_QA,
            PILOT_LEDGER,
            TS_STEPS,
            MIRROR_SKILL,
            MIRROR_WORKFLOW,
            MIRROR_BACKLOG,
            MIRROR_TS_STEPS,
        ]
        for p in required:
            assert p.exists(), f"required file missing (run sync-codex.sh?): {p}"
        cls.pilot_skill = _read(PILOT_SKILL)
        cls.pilot_workflow = _read(PILOT_WORKFLOW)
        cls.pilot_backlog = _read(PILOT_BACKLOG)
        cls.pilot_qa = _read(PILOT_QA)
        cls.pilot_ledger = json.loads(_read(PILOT_LEDGER))
        cls.ts_steps = _read(TS_STEPS)
        cls.m_skill = _read(MIRROR_SKILL)
        cls.m_workflow = _read(MIRROR_WORKFLOW)
        cls.m_backlog = _read(MIRROR_BACKLOG)
        cls.m_ts_steps = _read(MIRROR_TS_STEPS)
        cls.m_pilot_files = (cls.m_skill, cls.m_workflow, cls.m_backlog)

    # ── A. Cross-platform mirror parity (R12) ──────────────────────────────

    def test_mirror_backlog_reference_exists(self) -> None:
        """sync-codex.sh mirrored references/backlog-mode.md (the agentic
        SELECT/TRIAGE/ASK workflow) — it is loaded only in backlog mode."""
        self.assertTrue(
            MIRROR_BACKLOG.exists(),
            "backlog-mode.md must be mirrored into the Codex pilot skill",
        )

    def test_mirror_carries_triage_and_ask_stages(self) -> None:
        """The new leftward stages survive the rewrite in the pilot mirror."""
        mirror_route = self.m_skill + "\n" + self.m_backlog
        self.assertIn("triage", mirror_route.lower())
        self.assertIn("ask", mirror_route.lower())
        # The async-question valve phase survives in the mirror workflow.
        self.assertIn("Phase 3.5", self.m_workflow)
        self.assertRegex(
            self.m_workflow,
            r"Phase 3\.5 — ASK",
            "the mirror workflow must carry the Phase 3.5 ASK valve",
        )

    def test_mirror_carries_asked_verdict_and_grammar(self) -> None:
        """The ASKED durable-park verdict survives in the mirror grammar."""
        mirror_route = self.m_skill + "\n" + self.m_backlog
        self.assertIn("ASKED", mirror_route)
        self.assertIn(
            "`ASKED <id> (<n>)`",
            mirror_route,
            "the mirror must carry the ASKED grammar token",
        )

    def test_canonical_routes_backlog_grammar_behind_mode_gate(self) -> None:
        """Ready mode carries only common grammar; selected backlog mode loads
        the direct reference containing the extended grammar."""
        self.assertNotIn(
            "### Backlog-mode verdict grammar",
            self.pilot_skill,
            "backlog-only grammar must not stay always-loaded in SKILL.md",
        )
        self.assertIn(
            "read [references/backlog-mode.md]",
            self.pilot_skill,
            "the selected backlog route must require the direct reference",
        )
        self.assertIn(
            "execute its backlog-only setup, then continue with `workflow.md` Phase 1",
            self.pilot_skill,
            "the selected backlog route must explicitly continue into the workflow",
        )
        self.assertIn(
            "PILOT_VERDICT=<ADVANCED|NO_WORK|DEFERRED_TO_LAND|BLOCKED|NEEDS_HUMAN>",
            self.pilot_skill,
            "the ready root must retain the complete common terminal grammar",
        )
        self.assertNotIn(
            "PILOT_VERDICT=<ADVANCED|ASKED|",
            self.pilot_skill,
            "ASKED is backlog-only and belongs in the gated reference",
        )
        self.assertIn(
            "PILOT_VERDICT=<ADVANCED|ASKED|NO_WORK|DEFERRED_TO_LAND|BLOCKED|NEEDS_HUMAN>",
            self.pilot_backlog,
            "the selected reference must retain the full live backlog grammar",
        )
        self.assertRegex(
            self.pilot_backlog,
            r"`TRIAGED <id> <class>` is DIAGNOSTIC / dry-run ONLY",
            "the selected reference must retain the diagnostic-only split",
        )

    def test_pilot_candidate_ledger_matches_live_routed_files(self) -> None:
        """The independent Pilot ledger is hash-addressed and its reached-path
        improvement is reproducible from the canonical routed files."""
        ledger = self.pilot_ledger
        self.assertEqual("pilot", ledger["cluster"])
        self.assertEqual("B1", ledger["lineage"]["baseline"])
        self.assertEqual([], ledger["discards"])
        candidate = ledger["candidates"][0]
        self.assertEqual("keep", candidate["verdict"])

        # Prose-quality pins removed 2026-08-07 - judged via .flow/criteria.md
        # G1, not grep. (Live-file hash/char freeze and size ratchet removed
        # earlier for the same reason; deliberate-change protection lives in
        # test_prompt_text_pinned.py.) The QA classification grammar tokens
        # stay pinned:
        self.assertIn(
            "No PR exists: classify `qa` when `QA_STAGE_ENABLED=1` "
            "**and** `QA_FRESH=0`",
            self.pilot_workflow,
            "workflow.md must still own the QA-stage classification decision",
        )

    def test_mirror_carries_tracker_sync_r14_phase0_fix(self) -> None:
        """The R14 Phase-0 autonomy-marker fix (fn-68.2) survives in the
        tracker-sync mirror: the full marker family is recognized and folds into
        the single RALPH gate."""
        for token in (
            "FLOW_RALPH",
            "REVIEW_RECEIPT_PATH",
            "FLOW_AUTONOMOUS",
            "mode:autonomous",
        ):
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.m_ts_steps,
                    f"tracker-sync mirror must recognize {token!r} (R14 parity)",
                )
        # The single gate line carries all four markers.
        gate_window = self.m_ts_steps.split("RALPH=0", 1)[1][:600]
        for token in ("FLOW_AUTONOMOUS", "mode:autonomous"):
            with self.subTest(gate=token):
                self.assertIn(token, gate_window)

    def test_no_r2_block_before_tracker_sync_phase0_invariant(self) -> None:
        """THE second defect this regen exposed (impl-review r1): the R2 ask
        INSTRUCTION block was injected directly BEFORE the tracker-sync Phase-0
        autonomy invariant ('Under RALPH=1 NO code path may reach ...'). That
        contradicts R14 (under the marker tracker-sync queues/defers, never
        prompts). The block belongs at the GENUINE Phase-1 discovery ASK (where
        the human IS prompted to enable the bridge), never at the Phase-0
        autonomy invariant. Assert ordering: if an R2 block exists at all, it
        comes AFTER the Phase-0 invariant line."""
        invariant_idx = self.m_ts_steps.find(
            "Autonomy parity is a hard invariant"
        )
        self.assertNotEqual(
            invariant_idx, -1,
            "the tracker-sync mirror must carry the Phase-0 autonomy invariant",
        )
        first_r2 = self.m_ts_steps.find(R2_INSTRUCTION_SENTINEL)
        if first_r2 != -1:
            self.assertGreater(
                first_r2,
                invariant_idx,
                "the R2 ask block must NOT precede the Phase-0 autonomy "
                "invariant — it belongs at the genuine Phase-1 discovery ask "
                "(under the autonomy marker tracker-sync never prompts — R14)",
            )
        # And the autonomy invariant itself must NOT be immediately preceded by
        # the R2 block (the precise defect site): no R2 sentinel in the 600 chars
        # before the invariant.
        window_before = self.m_ts_steps[max(0, invariant_idx - 600):invariant_idx]
        self.assertNotIn(
            R2_INSTRUCTION_SENTINEL,
            window_before,
            "the R2 ask block must not sit immediately before the Phase-0 "
            "autonomy invariant (R14: that path never prompts)",
        )

    def test_mirror_has_no_claude_native_tool_leakage(self) -> None:
        """ZERO Claude-native tool names leak into the mirror PROSE. The
        DROID_PLUGIN_ROOT/CLAUDE_PLUGIN_ROOT plugin.json FALLBACK chain is the
        ONE sanctioned cross-platform shell form (the sync validator allows it),
        so this scan targets the tool-name tokens specifically."""
        forbidden = (
            "AskUserQuestion",
            "ToolSearch",
            "request_user_input",
        )
        for fname, text in (
            ("SKILL.md", self.m_skill),
            ("workflow.md", self.m_workflow),
            ("backlog-mode.md", self.m_backlog),
        ):
            for tok in forbidden:
                with self.subTest(file=fname, token=tok):
                    self.assertNotIn(
                        tok,
                        text,
                        f"{fname}: Claude-native {tok!r} leaked into the mirror",
                    )

    def test_mirror_rewrites_ask_to_numbered_prompt(self) -> None:
        """Where canonical pilot says `AskUserQuestion`, the mirror says the
        plain-text numbered-prompt form (the fn-45 rewrite)."""
        self.assertIn("plain-text numbered prompt", self.m_skill)
        self.assertIn("plain-text numbered prompt", self.m_workflow)

    def test_historical_maintainer_breadcrumb_is_absent(self) -> None:
        """The fn-68.5 mirror breadcrumb was task-local and is now stale."""
        for fname, text in (
            ("canonical pilot/backlog-mode.md", self.pilot_backlog),
            ("canonical tracker-sync/steps.md", self.ts_steps),
            ("pilot/backlog-mode.md", self.m_backlog),
            ("tracker-sync/steps.md", self.m_ts_steps),
        ):
            with self.subTest(file=fname):
                self.assertNotIn(
                    "Codex mirror is regenerated",
                    text,
                    f"{fname}: the maintainer breadcrumb must be stripped",
                )
                self.assertNotIn(
                    "do NOT regenerate the mirror here",
                    text,
                    f"{fname}: the breadcrumb tail must be stripped",
                )

    def test_no_r2_instruction_block_injected_into_pilot_mirror(self) -> None:
        """THE defect this regen exposed: pilot ONLY negates AskUserQuestion
        ('never reached', 'is forbidden', 'never an interactive') — so the R2
        'Ask the user via plain text. Render the options ...' INSTRUCTION block
        must NEVER be injected into any pilot mirror file. An injected block in
        pilot's Forbidden section / Phase-3.5 async valve directly contradicts
        the autonomous, surface-don't-block contract (R14)."""
        for fname, text in (
            ("SKILL.md", self.m_skill),
            ("workflow.md", self.m_workflow),
            ("backlog-mode.md", self.m_backlog),
        ):
            with self.subTest(file=fname):
                self.assertNotIn(
                    R2_INSTRUCTION_SENTINEL,
                    text,
                    f"{fname}: the R2 ask-instruction block must NOT be injected "
                    "into a pilot mirror file (pilot never asks — it negates)",
                )

    def test_mirror_is_present_for_every_canonical_pilot_file(self) -> None:
        """Structural parity: every canonical pilot markdown file has a mirror
        counterpart (no silently-dropped file)."""
        canon = {
            p.relative_to(PILOT)
            for p in PILOT.rglob("*.md")
        }
        mirror = {
            p.relative_to(MIRROR)
            for p in MIRROR.rglob("*.md")
        }
        missing = canon - mirror
        self.assertFalse(
            missing,
            f"canonical pilot files with no mirror: {sorted(map(str, missing))}",
        )

    # ── B. /goal (Codex) driver parity ─────────────────────────────────────

    def test_stopclause_verbs_present_in_canonical_and_mirror(self) -> None:
        """NO_WORK + DEFERRED_TO_LAND are the grep-able stop-clause / land
        hand-off verbs — present VERBATIM in both canonical and mirror so a
        transcript-blind /goal or /loop driver can key on them."""
        for label, text in (
            ("canonical SKILL", self.pilot_skill),
            ("mirror SKILL", self.m_skill),
        ):
            for verb in ("NO_WORK", "DEFERRED_TO_LAND"):
                with self.subTest(where=label, verb=verb):
                    self.assertIn(
                        verb,
                        text,
                        f"{label}: {verb} must stay grep-able for the driver",
                    )

    def test_primary_verdict_grammar_line_intact_in_mirror(self) -> None:
        """The single terminal PILOT_VERDICT grammar line (the one /goal reads)
        survives the rewrite with the full live verb set, ASKED included."""
        self.assertRegex(
            self.m_skill + "\n" + self.m_backlog,
            r"PILOT_VERDICT=<ADVANCED\|ASKED\|NO_WORK\|DEFERRED_TO_LAND\|BLOCKED\|NEEDS_HUMAN>",
            "the mirror must carry the full live PILOT_VERDICT grammar line",
        )

    def test_triaged_is_diagnostic_dry_run_only_in_mirror(self) -> None:
        """TRIAGED is documented diagnostic / dry-run-only — never a live
        terminal — so a live tick always lands on a state-changing verdict and an
        item can never re-select forever (R10). The mirror must preserve this."""
        mirror_route = self.m_skill + "\n" + self.m_backlog
        self.assertRegex(
            mirror_route,
            r"`TRIAGED <id> <class>` is DIAGNOSTIC / dry-run ONLY",
            "the mirror must keep TRIAGED diagnostic/dry-run-only",
        )
        # The live grammar line must NOT include TRIAGED as a terminal verb.
        live_line = next(
            ln
            for ln in mirror_route.splitlines()
            if "Live backlog grammar" in ln
        )
        self.assertNotIn("TRIAGED", live_line.split("`ADVANCED")[0] + "ADVANCED")
        self.assertRegex(
            mirror_route,
            r"`TRIAGED` is NOT a live terminal",
            "the live grammar must explicitly exclude TRIAGED as a terminal",
        )

    def test_goal_driver_examples_key_on_no_work(self) -> None:
        """The documented /goal stop-clause example keys on PILOT_VERDICT=NO_WORK
        — present in both canonical and mirror."""
        for label, text in (
            ("canonical", self.pilot_skill),
            ("mirror", self.m_skill),
        ):
            with self.subTest(where=label):
                self.assertRegex(
                    text,
                    r"/goal keep running /flow-next:pilot until it prints "
                    r"PILOT_VERDICT=NO_WORK",
                    f"{label}: the /goal stop-clause example must survive",
                )

    # ── C. Autonomous-safety invariants (verifies R6/R7) ───────────────────

    def test_every_ask_mention_in_pilot_canonical_is_a_negation(self) -> None:
        """No-prompt invariant at the SOURCE: every AskUserQuestion mention in
        the pilot canonical files is a NEGATION (never reached / forbidden /
        never interactive / no path reaches) — pilot genuinely never asks. (The
        one non-prose mention allowed is the maintainer breadcrumb's
        'keep this file Claude-native (`AskUserQuestion`, `Task`)'.)"""
        # Prose-quality pins removed 2026-08-07 - judged via .flow/criteria.md
        # G1, not grep: the cue list is reduced to minimal negation tokens
        # rather than full sentence spellings.
        negation_cue = re.compile(
            r"\bnever\b|\bforbidden\b|can'?t|\bcannot\b|suppress"
            r"|no (?:code )?path|Claude-native",
            re.IGNORECASE,
        )
        for fname, text in (
            ("SKILL.md", self.pilot_skill),
            ("workflow.md", self.pilot_workflow),
            ("backlog-mode.md", self.pilot_backlog),
        ):
            for ln in text.splitlines():
                if "AskUserQuestion" not in ln:
                    continue
                with self.subTest(file=fname, line=ln.strip()[:70]):
                    self.assertTrue(
                        negation_cue.search(ln),
                        f"{fname}: a non-negation AskUserQuestion mention would "
                        f"mean pilot asks interactively — line: {ln.strip()!r}",
                    )

    def test_mirror_preserves_the_never_prompt_negation(self) -> None:
        """The no-prompt invariant survives the rewrite: every mirror mention
        of the rewritten prompt form carries a negation cue — the rewritten
        negation, not an injected ask. (Keyed on tokens, not sentences.)"""
        negation_cue = re.compile(
            r"\bnever\b|\bforbidden\b|can'?t|\bcannot\b|suppress"
            r"|no (?:code )?path",
            re.IGNORECASE,
        )
        for fname, text in (
            ("SKILL.md", self.m_skill),
            ("workflow.md", self.m_workflow),
        ):
            for ln in text.splitlines():
                if "plain-text numbered prompt" not in ln:
                    continue
                with self.subTest(file=fname, line=ln.strip()[:70]):
                    self.assertTrue(
                        negation_cue.search(ln),
                        f"{fname}: non-negation prompt mention — pilot must "
                        f"never ask — line: {ln.strip()!r}",
                    )

    def test_never_merge_allowlist_survives_in_mirror(self) -> None:
        """Invariant #1 (never merge / never invoke land — R6) is an ENFORCING
        bash allowlist that survives in the mirror: the dispatch allowlist names
        only the pipeline + tracker-surface ops, and land/merge/resolve hard-exit
        to NEEDS_HUMAN."""
        # Prose-quality restatement pins removed 2026-08-07 - judged via
        # .flow/criteria.md G1, not grep. The ENFORCING bash allowlist is the
        # guard that stays pinned.
        self.assertIn("assert_allowed_dispatch", self.m_workflow)
        # The allowlist names the sanctioned stage skills only.
        self.assertRegex(
            self.m_workflow,
            r"/flow-next:plan\|/flow-next:plan-review\|/flow-next:work"
            r"\|/flow-next:qa\|/flow-next:make-pr\)\s*return 0",
            "the dispatch allowlist must whitelist only the pipeline stages",
        )

    def test_never_author_guard_survives_in_mirror(self) -> None:
        """Invariant #2 (never author a spec) is an ENFORCING guard that survives
        in the mirror: a specless subject hard-exits rather than writing a
        stub."""
        # Prose-quality restatement pins removed 2026-08-07 - judged via
        # .flow/criteria.md G1, not grep. The ENFORCING guard + its hard-exit
        # message are what stay pinned.
        self.assertIn("assert_spec_write_allowed", self.m_workflow)
        self.assertRegex(
            self.m_workflow,
            r"backlog mode never authors specs",
            "the mirror must keep the never-author hard-exit message",
        )

    # Gate-off "byte-for-byte" prose pins removed 2026-08-07 - judged via
    # .flow/criteria.md G1, not grep; the structural scoping check below is
    # the enforcing guard.

    def test_autonomy_export_is_scoped_to_backlog_branch(self) -> None:
        """The FLOW_AUTONOMOUS export lives INSIDE the `if ... = backlog` branch
        (mirror), so ready mode incurs zero side effects."""
        # Slice from the backlog-branch open to the next phase header.
        branch = self.m_workflow.split('!= "backlog"', 1)
        self.assertEqual(
            len(branch), 2, "the mirror must carry the backlog-gate branch"
        )
        after = branch[1].split("## Phase 1", 1)[0]
        self.assertIn(
            "export FLOW_AUTONOMOUS=1",
            after,
            "the autonomy export must live inside the backlog-gate branch",
        )


if __name__ == "__main__":
    unittest.main()
