"""Cross-platform parity + autonomous-safety contract for the unattended driver
(`flow --auto`, formerly pilot; originally fn-68.5, R12; verifies R6/R7).

fn-68.5 was its OWN task because regenerating the Codex mirror exposes latent
canonical issues (fn-60 took FOUR NEEDS_WORK rounds from one mirror regen). The mirror is the **rewrite** of
the Claude-native canonical; this test locks the load-bearing invariants of that
rewrite so a later edit to ``sync-codex.sh`` or the canonical flow/tracker-sync
skills can't silently regress them.

The driver now lives in ``skills/flow-next-flow/auto.md`` (the single
always-loaded-under---auto file that replaced pilot's SKILL.md + workflow.md)
with ``references/backlog-mode.md`` and ``references/qa-stage.md`` beside it;
``skills/flow-next-pilot/SKILL.md`` is a one-release deprecation stub. Where
this file distinguished SKILL.md from workflow.md, both resolve to auto.md.

Three families, all **prose contract** (the host agent IS the runtime — there is
no Python engine to unit-test; backlog mode is skill prose the agent executes):

  A. **Cross-platform mirror parity (R12).** ``sync-codex.sh`` regenerated the
     Codex mirror; the tracker-sync R14 Phase-0 autonomy fix and
     ``backlog-mode.md`` survive, every ``--auto`` file has a mirror, and ZERO
     Claude-native tool-name leakage reaches the mirror prose.

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

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN = REPO_ROOT / "plugins" / "flow-next"

# Canonical (Claude-native) driver files: auto.md plus its two gated references.
FLOW = PLUGIN / "skills" / "flow-next-flow"
PILOT_SKILL = FLOW / "auto.md"
PILOT_WORKFLOW = FLOW / "auto.md"
PILOT_BACKLOG = FLOW / "references" / "backlog-mode.md"
PILOT_QA = FLOW / "references" / "qa-stage.md"
# The files a `--auto` run can load, relative to the flow skill dir; every one
# needs a mirror counterpart.
AUTO_ROUTED_FILES = ("auto.md", "references/backlog-mode.md", "references/qa-stage.md")

# Canonical tracker-sync (carries the R14 Phase-0 fix from fn-68.2).
TS_STEPS = PLUGIN / "skills" / "flow-next-tracker-sync" / "steps.md"

# The regenerated Codex mirror — the rewrite this task locks.
MIRROR = PLUGIN / "codex" / "skills" / "flow-next-flow"
MIRROR_SKILL = MIRROR / "auto.md"
MIRROR_WORKFLOW = MIRROR / "auto.md"
MIRROR_BACKLOG = MIRROR / "references" / "backlog-mode.md"
MIRROR_TS_STEPS = (
    PLUGIN / "codex" / "skills" / "flow-next-tracker-sync" / "steps.md"
)


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
        cls.ts_steps = _read(TS_STEPS)
        cls.m_skill = _read(MIRROR_SKILL)
        cls.m_workflow = _read(MIRROR_WORKFLOW)
        cls.m_backlog = _read(MIRROR_BACKLOG)
        cls.m_ts_steps = _read(MIRROR_TS_STEPS)
        cls.m_pilot_files = (cls.m_skill, cls.m_backlog)

    # ── A. Cross-platform mirror parity (R12) ──────────────────────────────

    def test_mirror_backlog_reference_exists(self) -> None:
        """sync-codex.sh mirrored references/backlog-mode.md (the agentic
        SELECT/TRIAGE/ASK workflow) — it is loaded only in backlog mode."""
        self.assertTrue(
            MIRROR_BACKLOG.exists(),
            "backlog-mode.md must be mirrored into the Codex flow skill",
        )

    def test_canonical_routes_backlog_grammar_behind_mode_gate(self) -> None:
        """Ready mode carries only common grammar; selected backlog mode loads
        the direct reference containing the extended grammar."""
        self.assertIn(
            "](references/backlog-mode.md)",
            self.pilot_skill,
            "the selected backlog route must require the direct reference",
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

    def test_mirror_carries_tracker_sync_r14_phase0_fix(self) -> None:
        """The R14 Phase-0 autonomy-marker fix (fn-68.2) survives in the
        tracker-sync mirror: the full marker family is recognized and folds into
        the single UNATTENDED gate."""
        for token in (
            "FLOW_AUTONOMOUS",
            "AUTONOMOUS",
            "mode:autonomous",
        ):
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.m_ts_steps,
                    f"tracker-sync mirror must recognize {token!r} (R14 parity)",
                )
        # The single gate line carries the markers.
        gate_window = self.m_ts_steps.split("UNATTENDED=0", 1)[1][:600]
        for token in ("FLOW_AUTONOMOUS", "mode:autonomous"):
            with self.subTest(gate=token):
                self.assertIn(token, gate_window)

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
            ("auto.md", self.m_skill),
            ("backlog-mode.md", self.m_backlog),
        ):
            for tok in forbidden:
                with self.subTest(file=fname, token=tok):
                    self.assertNotIn(
                        tok,
                        text,
                        f"{fname}: Claude-native {tok!r} leaked into the mirror",
                    )

    def test_mirror_driver_carries_no_injected_ask_block(self) -> None:
        """sync-codex.sh injects its plain-text ask block at a prose ask site.
        No file a `--auto` run loads may carry it: a negated ask mention (the
        Forbidden list) mis-read as an ask site told unattended Codex runs to
        stop and wait for the user. The marker is read from the generator so
        the check follows the real transform."""
        script = (REPO_ROOT / "scripts" / "sync-codex.sh").read_text(encoding="utf-8")
        match = re.search(r"INSTRUCTION = \(\s*'(\*\*[^*]+\*\*)", script)
        self.assertIsNotNone(match, "sync-codex.sh must define the R2 INSTRUCTION")
        marker = match.group(1)
        for rel in AUTO_ROUTED_FILES:
            with self.subTest(file=rel):
                self.assertNotIn(marker, _read(MIRROR / rel))

    def test_mirror_is_present_for_every_canonical_pilot_file(self) -> None:
        """Structural parity: every file a `--auto` run can load, plus the
        pilot deprecation stub, has a mirror counterpart (no silently-dropped
        file)."""
        missing = [rel for rel in AUTO_ROUTED_FILES if not (MIRROR / rel).is_file()]
        self.assertFalse(
            missing,
            f"canonical --auto files with no mirror: {missing}",
        )

    # ── B. /goal (Codex) driver parity ─────────────────────────────────────

    def test_stopclause_verbs_present_in_canonical_and_mirror(self) -> None:
        """NO_WORK + DEFERRED_TO_LAND are the grep-able stop-clause / land
        hand-off verbs — present VERBATIM in both canonical and mirror so a
        transcript-blind /goal or /loop driver can key on them."""
        for label, text in (
            ("canonical auto.md", self.pilot_skill),
            ("mirror auto.md", self.m_skill),
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

    # ── C. Autonomous-safety invariants (verifies R6/R7) ───────────────────

    def test_never_merge_allowlist_survives_in_mirror(self) -> None:
        """Invariant #1 (never merge / never invoke land — R6) is an ENFORCING
        bash allowlist that survives in the mirror: the dispatch allowlist names
        only the pipeline + tracker-surface ops, and land/merge/resolve hard-exit
        to NEEDS_HUMAN."""
        # Prose-quality restatement pins removed 2026-08-07 - judged via
        # .flow/criteria.md G1, not grep. The ENFORCING bash allowlist is the
        # guard that stays pinned.
        self.assertIn('case "$DISPATCH_TARGET" in', self.m_workflow)
        # The allowlist names the sanctioned stage skills only.
        self.assertRegex(
            self.m_workflow,
            r"/flow-next:plan\|/flow-next:plan-review\|/flow-next:work"
            r"\|/flow-next:qa\|/flow-next:make-pr\)\s*:",
            "the dispatch allowlist must whitelist only the pipeline stages",
        )

    def test_never_author_guard_survives_in_mirror(self) -> None:
        """Invariant #2 (never author a spec) is an ENFORCING guard that survives
        in the mirror: a specless subject hard-exits rather than writing a
        stub."""
        # The guard runs inline in the Phase 3.5 block (a shell function defined
        # in an earlier block would not survive the tool-call boundary).
        self.assertIn('[ ! -f "$SPEC_PATH" ]', self.m_workflow)

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
