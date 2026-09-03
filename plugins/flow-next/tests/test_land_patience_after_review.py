"""Static contract pins for `land.patienceMinutesAfterReview` (fn-219 R7-R9, R11).

Same honest harness limitation as CommentScanWorkflowStaticTestCase in
test_land_config.py: the silence-window re-anchor is host-agent BASH inside
the land skill workflow, not flowctl Python — there is no executable harness
for it (no `gh`, no host agent in CI). So the load-bearing tokens of the
contract are pinned on the CANONICAL files, sliced to the blocks they live in:

  * Phase 0 reads the key through the single `lcfg` capture (still exactly
    one `config get land --json`) and treats anything but a positive integer
    as off (R6 read side).
  * §2.6 records `REVIEW_EVENT_AT` as a running max across head-current
    reviews AND qualifying clean-review comments (the comment projection
    carries `.updated_at`) (R7).
  * The re-anchor block binds ONLY under the four conditions
    (`PATIENCE_AFTER_REVIEW`, `AUTO_REVIEW_CURRENT == 1`, `UNRESOLVED -eq 0`,
    a parseable `REVIEW_EVENT_AT`), sets `WINDOW_ANCHOR=review`, and rebinds
    `SILENCE_WINDOW_ELAPSED` — never `WINDOW_ELAPSED` (R7, R8).
  * The silence bullet reads `SILENCE_WINDOW_ELAPSED`; `approve`, §2.6b, and
    §2.7 keep `WINDOW_ELAPSED`; the merge flags are byte-for-byte (R8).
  * `WINDOW_ANCHOR=push` is initialized at the PR_STATE capture (the fn-200
    initializer discipline) and `anchor=<push|review>` is reported only when
    the key is configured (R9).

Pinned on the CANONICAL files AND their codex-mirror copies (the
`both_copies` pattern from test_skill_prose_diet.py) — fn-219.4 regenerated
the mirror once after every canonical prose task landed. The conduct
checklist has no mirror copy and stays canonical-only.
"""

from __future__ import annotations

import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
PLUGIN = HERE.parent.parent
LAND = PLUGIN / "skills" / "flow-next-land"
MIRROR_LAND = PLUGIN / "codex" / "skills" / "flow-next-land"
CONDUCT = PLUGIN.parent.parent / "agent_docs" / "conduct" / "land.md"

KEY = "patienceMinutesAfterReview"


def both_copies(rel: str) -> list[Path]:
    """Canonical land file + its codex-mirror copy (mirror must exist)."""
    canonical = LAND / rel
    mirrored = MIRROR_LAND / rel
    assert canonical.exists(), f"missing canonical file: {rel}"
    assert mirrored.exists(), f"missing codex mirror copy: {rel}"
    return [canonical, mirrored]


def _slice(text: str, start_marker: str, end_marker: str, pad: int = 0) -> str:
    start = text.find(start_marker)
    assert start != -1, f"marker not found: {start_marker!r}"
    end = text.find(end_marker, start)
    assert end != -1, f"end marker not found after start: {end_marker!r}"
    return text[start : end + pad]


class _Slices:
    """The pinned blocks of one workflow copy, sliced by their markers."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.text = path.read_text(encoding="utf-8")
        self.phase0 = _slice(self.text, "## Phase 0", "## Phase 1")
        self.phase2_top = _slice(
            self.text, "## Phase 2 — GATE", "### 2.1 — Durable-label skip"
        )
        self.reviews_loop = _slice(
            self.text, "AUTO_REVIEW_PRESENT=0", "pulls/$PR_NUMBER/reviews", pad=120
        )
        self.scan = _slice(
            self.text,
            'if [[ "$REVIEW_SIGNAL" == "silence"',
            "issues/$PR_NUMBER/comments",
            pad=200,
        )
        self.anchor = _slice(
            self.text, "SILENCE_WINDOW_ELAPSED=$WINDOW_ELAPSED", "**Draft-PR review trigger"
        )
        signals = _slice(self.text, "Signal evaluation (only reached", "### 2.6b")
        self.silence_bullet = _slice(signals, "- **`silence`**", "- **`approve`**")
        self.approve_bullet = _slice(signals, "- **`approve`**", "- **`<github-login>`**")
        self.s26b = _slice(self.text, "### 2.6b — Human reviewer request", "### 2.7 — CI-fix budget")
        self.s27 = _slice(self.text, "### 2.7 — CI-fix budget", "### 2.8 — Merge-state gates")
        self.report = _slice(self.text, "## Phase 4 — REPORT", "Compute the tick verdict")
        self.dry_run = _slice(self.text, "### Dry-run stops here", "## Phase 3 — ACT")


class PatienceAfterReviewWorkflowStaticTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.copies = [_Slices(path) for path in both_copies("workflow.md")]

    # ── R6 read side: single lcfg capture, positive-integer-only ─────────

    def test_key_rides_the_single_lcfg_capture(self) -> None:
        for s in self.copies:
            with self.subTest(copy=s.path):
                self.assertIn(f'PATIENCE_AFTER_REVIEW="$(lcfg {KEY})"', s.phase0)
                self.assertNotIn(f"config get land.{KEY}", s.text)
                self.assertEqual(s.text.count("config get land --json"), 1)

    def test_off_states_are_anything_but_a_positive_integer(self) -> None:
        for s in self.copies:
            with self.subTest(copy=s.path):
                self.assertIn('=~ ^[1-9][0-9]*$ ]] || PATIENCE_AFTER_REVIEW=""', s.phase0)

    def test_phase0_read_executes_off_states_and_bounds_overflow(self) -> None:
        for s in self.copies:
            with self.subTest(copy=s.path):
                # Executable: run the Phase 0 read line with a stubbed lcfg for each
                # off state and for on values, including one beyond bash's signed
                # range — every positive integer is ON (the schema is unbounded); the
                # §2.6 fence is what handles overflow (see the anchor matrix test).
                import subprocess
                line = next(
                    l for l in s.phase0.splitlines()
                    if l.startswith('PATIENCE_AFTER_REVIEW="$(lcfg patienceMinutesAfterReview)"')
                )
                cases = {
                    "null": "", "": "", "0": "", "abc": "", "-5": "", "15": "15",
                    "999999": "999999", "1000000": "1000000",
                    "9223372036854775808": "9223372036854775808",
                }
                for raw, want in cases.items():
                    script = f"lcfg() {{ printf '%s\\n' {raw!r}; }}\n{line}\nprintf '%s' \"$PATIENCE_AFTER_REVIEW\""
                    out = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
                    self.assertEqual(out, want, f"raw={raw!r}")

        # ── R7: review-event max across reviews + qualifying comments ────────

    def test_review_event_initialized_and_maxed_in_head_current_branch(self) -> None:
        for s in self.copies:
            with self.subTest(copy=s.path):
                self.assertIn("REVIEW_EVENT_AT=", s.reviews_loop)
                fold = '[[ "$submitted" > "$REVIEW_EVENT_AT" ]] && REVIEW_EVENT_AT="$submitted"'
                self.assertIn(fold, s.reviews_loop)
                # the fold sits inside the head-current branch, after AUTO_REVIEW_CURRENT=1
                self.assertLess(s.reviews_loop.index("AUTO_REVIEW_CURRENT=1"), s.reviews_loop.index(fold))

    def test_comment_projection_carries_updated_at_as_second_field(self) -> None:
        for s in self.copies:
            with self.subTest(copy=s.path):
                self.assertIn("[.user.login, .updated_at, (.body", s.scan)
                self.assertIn("read -r login updated body", s.scan)
                fold = '[[ "$updated" > "$REVIEW_EVENT_AT" ]] && REVIEW_EVENT_AT="$updated"'
                self.assertIn(fold, s.scan)
                # folded on the qualifying match only — after the evidence set, before the break
                self.assertLess(s.scan.index("AUTO_REVIEW_SOURCE=comment"), s.scan.index(fold))
                self.assertLess(s.scan.index(fold), s.scan.index("break", s.scan.index(fold)))

        # ── R7/R8: the four-condition re-anchor rebinds only the silence conjunct ──

    def test_anchor_block_binds_under_the_four_conditions(self) -> None:
        for s in self.copies:
            with self.subTest(copy=s.path):
                # silence-only: approve/<login> gates consume the push window, so the
                # binding-anchor report must never claim `review` under them
                self.assertIn('"$REVIEW_SIGNAL" == "silence" && -n "$PATIENCE_AFTER_REVIEW"', s.anchor)
                self.assertIn('-n "$PATIENCE_AFTER_REVIEW"', s.anchor)
                self.assertIn('AUTO_REVIEW_CURRENT" == 1', s.anchor)
                self.assertIn('"$UNRESOLVED" -eq 0', s.anchor)
                self.assertIn('-n "$REVIEW_EVENT_AT"', s.anchor)
                self.assertIn("fromdateiso8601", s.anchor)
                self.assertIn("WINDOW_ANCHOR=review", s.anchor)
                self.assertIn(
                    "SILENCE_WINDOW_ELAPSED=$(( REVIEW_AGE_MIN >= PATIENCE_AFTER_REVIEW ? 1 : 0 ))",
                    s.anchor,
                )

    def test_anchor_block_executes_signal_and_condition_matrix(self) -> None:
        for s in self.copies:
            with self.subTest(copy=s.path):
                # Executable: run the re-anchor fence with stubbed inputs. Only the
                # silence signal with every condition met rebinds; approve/<login>,
                # open threads, a stale review, and an unparseable timestamp stay push.
                import subprocess
                start = s.anchor.find("SILENCE_WINDOW_ELAPSED=$WINDOW_ELAPSED")
                end = s.anchor.find("```", start)
                fence = s.anchor[start:end]
                base = dict(REVIEW_SIGNAL="silence", PATIENCE_AFTER_REVIEW="10", AUTO_REVIEW_CURRENT="1",
                            UNRESOLVED="0", REVIEW_EVENT_AT="2026-01-01T00:00:00Z",
                            NOW_EPOCH=str(1767225600 + 20 * 60), WINDOW_ELAPSED="0", WINDOW_ANCHOR="push")
                cases = [
                    ({}, "review|1"),
                    ({"NOW_EPOCH": str(1767225600 + 5 * 60)}, "review|0"),
                    ({"REVIEW_SIGNAL": "approve"}, "push|0"),
                    ({"REVIEW_SIGNAL": "somelogin"}, "push|0"),
                    ({"PATIENCE_AFTER_REVIEW": ""}, "push|0"),
                    ({"AUTO_REVIEW_CURRENT": "0"}, "push|0"),
                    ({"UNRESOLVED": "2"}, "push|0"),
                    ({"REVIEW_EVENT_AT": "not-a-date"}, "push|0"),
                    ({"REVIEW_EVENT_AT": ""}, "push|0"),
                    # beyond bash's signed range: rebinds, never elapsed (no wrap-to-elapsed)
                    ({"PATIENCE_AFTER_REVIEW": "9223372036854775808"}, "review|0"),
                    ({"PATIENCE_AFTER_REVIEW": "999999999999999999"}, "review|0"),
                ]
                for override, want in cases:
                    env = {**base, **override}
                    prelude = "".join(f"{k}={v!r}\n" for k, v in env.items())
                    script = prelude + fence + '\nprintf "%s|%s" "$WINDOW_ANCHOR" "$SILENCE_WINDOW_ELAPSED"'
                    res = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
                    self.assertEqual(res.returncode, 0, f"{override}: {res.stderr}")
                    self.assertEqual(res.stdout, want, f"{override}")

    def test_anchor_block_never_rebinds_the_push_window(self) -> None:
        for s in self.copies:
            with self.subTest(copy=s.path):
                # WINDOW_ELAPSED is READ (the default) but never assigned here.
                self.assertIn("SILENCE_WINDOW_ELAPSED=$WINDOW_ELAPSED", s.anchor)
                self.assertNotIn("\nWINDOW_ELAPSED=", s.anchor)
                self.assertNotIn(" WINDOW_ELAPSED=", s.anchor)
                # per-tick memory: no ledger write in the block
                for write in ('mv "$tmp"', "REVIEW_EVENT_AT = ", "triggerSha"):
                    self.assertNotIn(write, s.anchor)

    def test_anchor_block_sits_after_comment_scan_before_draft_trigger(self) -> None:
        for s in self.copies:
            with self.subTest(copy=s.path):
                scan_pos = s.text.find('if [[ "$REVIEW_SIGNAL" == "silence"')
                anchor_pos = s.text.find("SILENCE_WINDOW_ELAPSED=$WINDOW_ELAPSED")
                trigger_pos = s.text.find("**Draft-PR review trigger")
                self.assertLess(scan_pos, anchor_pos)
                self.assertLess(anchor_pos, trigger_pos)

    def test_only_the_silence_bullet_reads_the_rebound_window(self) -> None:
        for s in self.copies:
            with self.subTest(copy=s.path):
                self.assertIn("SILENCE_WINDOW_ELAPSED == 1", s.silence_bullet)
                # reason names the binding anchor when the key is configured (both
                # forms), and keeps today's bare reason when unset
                self.assertIn("<AGE_MIN>/<PATIENCE_MIN>m, anchor=push)", s.silence_bullet)
                self.assertIn("<REVIEW_AGE_MIN>/<PATIENCE_AFTER_REVIEW>m, anchor=review)", s.silence_bullet)
                self.assertIn("patience window open (<AGE_MIN>/<PATIENCE_MIN>m)`", s.silence_bullet)
                self.assertNotIn("SILENCE_WINDOW_ELAPSED", s.approve_bullet)
                self.assertIn("WINDOW_ELAPSED == 1", s.approve_bullet)
                self.assertIn('[[ "$WINDOW_ELAPSED" == 1 ]]', s.s26b)
                self.assertNotIn("SILENCE_WINDOW_ELAPSED", s.s26b)
                self.assertNotIn("SILENCE_WINDOW_ELAPSED", s.s27)

    def test_push_anchor_computation_unchanged(self) -> None:
        for s in self.copies:
            with self.subTest(copy=s.path):
                self.assertIn("WINDOW_ELAPSED=$(( AGE_MIN >= PATIENCE_MIN ? 1 : 0 ))", s.text)

        # ── R8: merge flags byte-for-byte ────────────────────────────────────

    def test_merge_flags_unchanged(self) -> None:
        for s in self.copies:
            with self.subTest(copy=s.path):
                self.assertIn(
                    'MERGE_ERR="$($MERGE_CMD "$PR_NUMBER" --squash --delete-branch '
                    '--match-head-commit "$HEAD_OID" 2>&1 >/dev/null)" || MERGE_RC=$?',
                    s.text,
                )
                self.assertNotIn("gh pr merge --auto ", s.text.replace("never `gh pr merge --auto`", ""))

        # ── R9: initializer discipline + anchor= only when configured ────────

    def test_window_anchor_initialized_at_pr_state_capture(self) -> None:
        for s in self.copies:
            with self.subTest(copy=s.path):
                self.assertIn("WINDOW_ANCHOR=push", s.phase2_top)
                self.assertLess(s.phase2_top.index('PR_STATE="$(gh pr view'), s.phase2_top.index("WINDOW_ANCHOR=push"))
                # `review` is assigned in exactly one place: the re-anchor block
                self.assertEqual(s.text.count("WINDOW_ANCHOR=review"), 1)

    def test_report_names_anchor_only_when_configured(self) -> None:
        for s in self.copies:
            with self.subTest(copy=s.path):
                # the unconfigured line is byte-for-byte
                self.assertIn("window=<AGE_MIN>/<PATIENCE_MIN>m\n", s.report)
                self.assertIn("anchor=<push|review>", s.report)
                self.assertIn("anchor=push", s.report)
                self.assertIn("anchor=<push|review>", s.dry_run)


class PatienceAfterReviewSurfacesStaticTestCase(unittest.TestCase):
    def test_skill_md_names_the_key_as_a_silence_only_refinement(self) -> None:
        for path in both_copies("SKILL.md"):
            skill = path.read_text(encoding="utf-8")
            self.assertIn(f"`land.{KEY}`", skill, path)
            unattended = skill[skill.find("## Unattended runs"):]
            self.assertIn(f"land.{KEY}", unattended, path)

    def test_conduct_checklist_carries_the_item(self) -> None:
        conduct = CONDUCT.read_text(encoding="utf-8")
        self.assertIn(f"land.{KEY}", conduct)
        self.assertIn("anchor=push", conduct)


if __name__ == "__main__":
    unittest.main()
