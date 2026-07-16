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

  C. **Autonomous-safety invariants (verifies R6/R7).** Under the autonomy marker
     (``FLOW_AUTONOMOUS=1`` / ``mode:autonomous``) backlog mode (1) never reaches
     an interactive prompt — every ``AskUserQuestion`` mention in the pilot
     canonical is a NEGATION, and the mirror rewrite preserves the negation;
     (2) never merges / never invokes land — the ``assert_allowed_dispatch``
     allowlist hard-excludes land/merge/resolve and survives in the mirror;
     (3) never authors a spec — the ``assert_spec_write_allowed`` guard
     hard-exits on a specless subject and survives in the mirror; and (4) the
     gate-off (ready) path is byte-identical — no ``FLOW_AUTONOMOUS`` export, no
     backlog-mode.md load.

Run:
    python3 -m unittest plugins.flow-next.tests.test_pilot_backlog_mirror_safety -v
"""

from __future__ import annotations

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
        self.assertIn("triage", self.m_skill.lower())
        self.assertIn("ask", self.m_skill.lower())
        # The stage values line names triage/ask as backlog-only stages.
        self.assertRegex(
            self.m_skill,
            r"`triage`\s*/\s*`ask`.*backlog mode only",
            "the mirror must document triage/ask as backlog-only stages",
        )
        # The async-question valve phase survives in the mirror workflow.
        self.assertIn("Phase 3.5", self.m_workflow)
        self.assertRegex(
            self.m_workflow,
            r"Phase 3\.5 — ASK",
            "the mirror workflow must carry the Phase 3.5 ASK valve",
        )

    def test_mirror_carries_asked_verdict_and_grammar(self) -> None:
        """The ASKED durable-park verdict survives in the mirror grammar."""
        self.assertIn("ASKED", self.m_skill)
        self.assertRegex(
            self.m_skill,
            r"`ASKED <id> \(<n>\)`.*durable park",
            "the mirror must document ASKED as a durable park",
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

    def test_maintainer_breadcrumb_stripped_from_mirror(self) -> None:
        """The 'Codex mirror is regenerated in fn-68.5 — keep this file
        Claude-native' maintainer breadcrumb is self-contradictory inside the
        already-rewritten mirror; sync-codex.sh must strip it from BOTH the
        backlog-mode and tracker-sync mirror."""
        for fname, text in (
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
        # And the breadcrumb DOES survive in canonical (it is human-useful there).
        self.assertIn("Codex mirror is regenerated in fn-68.5", self.pilot_backlog)
        self.assertIn("Codex mirror is regenerated in **fn-68.5**", self.ts_steps)

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
            self.m_skill,
            r"PILOT_VERDICT=<ADVANCED\|ASKED\|NO_WORK\|DEFERRED_TO_LAND\|BLOCKED\|NEEDS_HUMAN>",
            "the mirror must carry the full live PILOT_VERDICT grammar line",
        )

    def test_triaged_is_diagnostic_dry_run_only_in_mirror(self) -> None:
        """TRIAGED is documented diagnostic / dry-run-only — never a live
        terminal — so a live tick always lands on a state-changing verdict and an
        item can never re-select forever (R10). The mirror must preserve this."""
        self.assertRegex(
            self.m_skill,
            r"`TRIAGED <id> <class>` is DIAGNOSTIC / dry-run ONLY",
            "the mirror must keep TRIAGED diagnostic/dry-run-only",
        )
        # The live grammar line must NOT include TRIAGED as a terminal verb.
        live_line = next(
            ln
            for ln in self.m_skill.splitlines()
            if "Live backlog grammar" in ln
        )
        self.assertNotIn("TRIAGED", live_line.split("`ADVANCED")[0] + "ADVANCED")
        self.assertRegex(
            live_line,
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
        negation_cue = re.compile(
            r"never reach|never an interactive|is forbidden|never asks? interactively"
            r"|no (?:code )?path reaches|never reachable|keep this file\s+Claude-native"
            r"|Claude-native \(`AskUserQuestion`"
            # prompt-suppression phrasings are also negations ("can't hang on an
            # AskUserQuestion", "suppresses all prompts so the loop can't hang"):
            r"|can'?t hang on|cannot hang on|suppress(?:es)? all prompts",
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
        """The no-prompt invariant survives the rewrite: the mirror states the
        plain-text numbered prompt is never reached / forbidden on the tick
        path — the rewritten negation, not an injected ask."""
        joined = self.m_skill + "\n" + self.m_workflow
        self.assertRegex(
            joined,
            r"`plain-text numbered prompt` is never reached"
            r"|never an interactive `plain-text numbered prompt`"
            r"|`plain-text numbered prompt` is forbidden",
            "the mirror must preserve pilot's never-prompt negation",
        )

    def test_never_merge_allowlist_survives_in_mirror(self) -> None:
        """Invariant #1 (never merge / never invoke land — R6) is an ENFORCING
        bash allowlist that survives in the mirror: the dispatch allowlist names
        only the pipeline + tracker-surface ops, and land/merge/resolve hard-exit
        to NEEDS_HUMAN."""
        self.assertIn("assert_allowed_dispatch", self.m_workflow)
        # The allowlist names the sanctioned stage skills only.
        self.assertRegex(
            self.m_workflow,
            r"/flow-next:plan\|/flow-next:plan-review\|/flow-next:work"
            r"\|/flow-next:qa\|/flow-next:make-pr\)\s*return 0",
            "the dispatch allowlist must whitelist only the pipeline stages",
        )
        # land / merge / resolve are named as the forbidden targets that never
        # reach return 0.
        self.assertRegex(
            self.m_workflow,
            r"/flow-next:land.*gh pr merge.*never reaches the allowlist"
            r"|never merges/lands/resolves",
            "the mirror must state land/merge/resolve never reach the allowlist",
        )
        # The forbidden block restates never-merge/never-land.
        self.assertRegex(
            self.m_skill,
            r"Never merging / never invoking land",
            "the mirror Forbidden block must restate never-merge/never-land",
        )

    def test_never_author_guard_survives_in_mirror(self) -> None:
        """Invariant #2 (never author a spec) is an ENFORCING guard that survives
        in the mirror: a specless subject hard-exits rather than writing a
        stub."""
        self.assertIn("assert_spec_write_allowed", self.m_workflow)
        self.assertRegex(
            self.m_workflow,
            r"backlog mode never authors specs",
            "the mirror must keep the never-author hard-exit message",
        )
        # The Forbidden block + boundaries restate never-author.
        self.assertRegex(
            self.m_skill,
            r"Never authoring a spec",
            "the mirror Forbidden block must restate never-author",
        )
        self.assertRegex(
            self.m_backlog,
            r"[Nn]ever authors? a spec",
            "the mirror backlog-mode boundaries must restate never-author",
        )

    def test_gate_off_ready_path_is_byte_identical(self) -> None:
        """Invariant: with the gate OFF (ready mode) the path is byte-identical —
        no FLOW_AUTONOMOUS export, backlog-mode.md never loaded. The canonical
        AND the mirror both state this, and both scope the autonomy export inside
        the backlog branch."""
        for label, text in (
            ("canonical", self.pilot_workflow),
            ("mirror", self.m_workflow),
        ):
            with self.subTest(where=label):
                self.assertRegex(
                    text,
                    r"[Rr]eady mode is byte-for-byte unchanged",
                    f"{label}: the gate-off byte-identical claim must be stated",
                )
                # The export is scoped to the backlog branch (the ready branch is
                # a bare ':' no-op that does NOT export FLOW_AUTONOMOUS).
                self.assertRegex(
                    text,
                    r"FLOW_AUTONOMOUS is NOT exported",
                    f"{label}: ready mode must NOT export FLOW_AUTONOMOUS",
                )

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
