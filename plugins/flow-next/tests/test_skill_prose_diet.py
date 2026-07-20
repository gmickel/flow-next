"""fn-110.2 skill-callsite diet — durable structural prose invariants.

Pins the round-trip diet so future edits cannot silently regress it:

  * land workflow Phase 0: exactly ONE `config get` invocation (the `land`
    subtree capture) — was 7 sequential per-key reads (R3).
  * plan steps.md: exactly ONE `config get` (the Step 0 root snapshot); the
    Route B create path contains no `spec set-branch` and no `task set-spec`
    invocation (R4), plus the committed before/after invocation-count fixture
    showing >=40% fewer flowctl calls on a 4-task all-frontmatter plan.
  * pilot: exactly ONE `config get` across SKILL.md + workflow.md +
    references/backlog-mode.md, located in SKILL.md; the other two files
    (and references/qa-stage.md) carry ZERO flowctl config calls (R5).
  * make-pr workflow Phase 0: exactly THREE bash fences (R6).
  * impl-review SKILL.md: exactly ONE `for arg in $ARGUMENTS` fence (R6).
  * plan-review: per-backend execution blocks single-sourced in workflow.md
    (SKILL.md has zero backend plan-review invocations); the Foreground rule
    and the fn-90 deterministic-cap sentence are byte-exact; no agent-side
    iteration counting is (re)introduced (R6).

All assertions run against the canonical files AND (where the invariant is
count-shaped and survives the sync rewrite) the codex mirror copies.
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PLUGIN = REPO / "plugins" / "flow-next"
SKILLS = PLUGIN / "skills"
MIRROR_SKILLS = PLUGIN / "codex" / "skills"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "plan_invocation_counts"

# Matches an actual `config get` INVOCATION ($FLOWCTL-prefixed, quoted or not),
# never a prose mention of the words "config get".
CONFIG_GET = re.compile(r'\$FLOWCTL"?\s+config get')

# Protected prose — byte-exact (R6). Any edit to these strings in the skill
# must be a deliberate decision that also updates this test.
FOREGROUND_RULE_BULLET = (
    "- **Foreground rule:** run every `flowctl <backend> plan-review` call as "
    "one **blocking foreground** Bash call with a generous timeout (10 minutes; "
    "verdicts typically land in 1–7) — never `run_in_background` + "
    "monitor/poll (a background completion does not reliably resume a subagent "
    "context)"
)
CAP_SENTENCE = (
    "**The cap is now ALSO enforced deterministically by flowctl (fn-90 R5): "
    "each `flowctl <backend> plan-review` dispatch increments a cumulative "
    "spec-scoped counter (`plan_review_rounds`) and REFUSES at "
    "`${MAX_REVIEW_ITERATIONS:-4}` with an `ESCALATE:` marker + exit 4 — "
    "the flowctl counter survives across fresh `/flow-next:plan-review` "
    "invocations, so a caller-side \"re-invoke until SHIP\" outer loop can no "
    "longer reset the cap by re-entering. This loop is INTERNAL — the "
    "caller (e.g. `/flow-next:plan`, pilot) invokes plan-review ONCE and acts "
    "on the terminal verdict; the flowctl counter resets ONLY on a SHIP "
    "verdict or an explicit re-plan (`flowctl spec reset-review-rounds "
    "<spec-id>`), never on a fresh invocation or a spec edit.**"
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def section(text: str, start: str, end: str) -> str:
    """Slice of text from the line starting `start` up to the line starting `end`."""
    lines = text.splitlines(keepends=True)
    out, active = [], False
    for line in lines:
        if line.startswith(start):
            active = True
        elif active and line.startswith(end):
            break
        if active:
            out.append(line)
    joined = "".join(out)
    assert joined, f"section {start!r}..{end!r} not found"
    return joined


def both_copies(rel: str):
    """Canonical file + its codex-mirror copy (mirror must exist)."""
    canonical = SKILLS / rel
    mirrored = MIRROR_SKILLS / rel
    assert canonical.exists(), f"missing canonical file: {rel}"
    assert mirrored.exists(), f"missing codex mirror copy: {rel}"
    return [canonical, mirrored]


class LandConfigDietTestCase(unittest.TestCase):
    def test_land_phase0_exactly_one_config_get(self):
        for path in both_copies("flow-next-land/workflow.md"):
            text = read(path)
            phase0 = section(text, "## Phase 0", "## Phase 1")
            self.assertEqual(
                len(CONFIG_GET.findall(phase0)), 1,
                f"{path}: land Phase 0 must make exactly ONE config get invocation",
            )
            # The one call is the subtree capture, and it is the only one anywhere.
            self.assertIn("config get land --json", phase0)
            self.assertEqual(len(CONFIG_GET.findall(text)), 1,
                             f"{path}: land workflow has stray config get calls")
            # The old bare cfg() helper (7 per-key startups) must not come back.
            # (lcfg() — the captured-subtree lookup — is the replacement and is fine.)
            self.assertNotRegex(text, r"(?<![A-Za-z_])cfg\(\)\s*\{",
                                f"{path}: per-key cfg() helper reintroduced")


class PlanDietTestCase(unittest.TestCase):
    def steps(self):
        return both_copies("flow-next-plan/steps.md")

    def test_plan_exactly_one_config_get(self):
        for path in self.steps():
            text = read(path)
            self.assertEqual(
                len(CONFIG_GET.findall(text)), 1,
                f"{path}: plan must make exactly ONE config get (the Step 0 root snapshot)",
            )
            self.assertIn("config get --json", text)

    def test_route_b_create_path_has_no_set_branch_or_set_spec(self):
        for path in self.steps():
            route_b = section(read(path), "**Route B", "## Step 6")
            self.assertNotIn("$FLOWCTL spec set-branch", route_b,
                             f"{path}: set-branch reintroduced on the create path")
            self.assertNotIn("$FLOWCTL task set-spec", route_b,
                             f"{path}: per-task set-spec reintroduced on the create path")
            # The one-call create must carry all three create-time flags.
            for flag in ("--description-file", "--acceptance-file", "--satisfies"):
                self.assertIn(flag, route_b, f"{path}: task create lost {flag}")

    def test_fixture_shows_at_least_40_percent_fewer_invocations(self):
        def count(name):
            lines = read(FIXTURES / name).splitlines()
            return len([ln for ln in lines if ln.strip() and not ln.startswith("#")])

        before, after = count("before.txt"), count("after.txt")
        self.assertGreater(before, after)
        # Integer math: (before - after) / before >= 0.40
        self.assertGreaterEqual(
            (before - after) * 100, 40 * before,
            f"plan fixture reduction below 40% ({before} -> {after})",
        )


class PilotSnapshotTestCase(unittest.TestCase):
    def test_exactly_one_config_call_located_in_skill_md(self):
        counts = {}
        for rel in ("SKILL.md", "workflow.md", "references/backlog-mode.md",
                    "references/qa-stage.md"):
            for path in both_copies(f"flow-next-pilot/{rel}"):
                key = (rel, "mirror" if MIRROR_SKILLS in path.parents else "canonical")
                counts[key] = len(CONFIG_GET.findall(read(path)))
        for variant in ("canonical", "mirror"):
            self.assertEqual(counts[("SKILL.md", variant)], 1,
                             f"pilot SKILL.md ({variant}) must own the ONE config call")
            for rel in ("workflow.md", "references/backlog-mode.md",
                        "references/qa-stage.md"):
                self.assertEqual(counts[(rel, variant)], 0,
                                 f"pilot {rel} ({variant}) must make zero config calls")

    def test_backlog_mode_has_zero_flowctl_config_calls(self):
        for path in both_copies("flow-next-pilot/references/backlog-mode.md"):
            self.assertNotRegex(read(path), r'\$FLOWCTL"?\s+config\b',
                                f"{path}: backlog-mode.md must be config-call-free")

    def test_snapshot_consumers_read_the_skill_owned_file(self):
        snapshot = ".flow/tmp/pilot-config-snapshot.json"
        for rel in ("SKILL.md", "workflow.md", "references/backlog-mode.md"):
            for path in both_copies(f"flow-next-pilot/{rel}"):
                self.assertIn(snapshot, read(path),
                              f"{path}: must reference the shared root snapshot file")


class MakePrFenceTestCase(unittest.TestCase):
    def test_phase0_has_exactly_three_bash_fences(self):
        for path in both_copies("flow-next-make-pr/workflow.md"):
            phase0 = section(read(path), "## Phase 0", "## Phase 1")
            self.assertEqual(
                phase0.count("```bash"), 3,
                f"{path}: make-pr Phase 0 must run as exactly THREE bash fences",
            )
            # §0.5 semantics intact: single show capture doubles as validation,
            # and the autonomous hard-error on open tasks survives.
            self.assertIn('SPEC_JSON=$("$FLOWCTL" show "$SPEC_ID" --json', phase0)
            self.assertIn("Autonomous context cannot open PRs for incomplete specs", phase0)
            # The old validation-only show must not come back.
            self.assertNotIn('show "$SPEC_ID" --json >/dev/null', phase0)


class ImplReviewArgFenceTestCase(unittest.TestCase):
    def test_single_argument_parse_fence(self):
        for path in both_copies("flow-next-impl-review/SKILL.md"):
            text = read(path)
            self.assertEqual(
                text.count("for arg in $ARGUMENTS"), 1,
                f"{path}: impl-review must parse $ARGUMENTS in exactly ONE fence",
            )
            # The merged fence still covers all three opt-in flags + Ralph block.
            for needle in ("--validate) VALIDATE=true", "--deep) DEEP=true",
                           "--interactive) INTERACTIVE=true",
                           "not compatible with Ralph mode"):
                self.assertIn(needle, text, f"{path}: merged arg fence lost {needle!r}")


class PlanReviewSingleSourceTestCase(unittest.TestCase):
    INVOKE = re.compile(r"^\$FLOWCTL (codex|copilot|cursor) plan-review", re.M)

    def test_backend_blocks_live_only_in_workflow_md(self):
        for skill_md in both_copies("flow-next-plan-review/SKILL.md"):
            self.assertEqual(
                len(self.INVOKE.findall(read(skill_md))), 0,
                f"{skill_md}: backend execution blocks must be single-sourced in workflow.md",
            )
        for workflow_md in both_copies("flow-next-plan-review/workflow.md"):
            backends = set(self.INVOKE.findall(read(workflow_md)))
            self.assertEqual(backends, {"codex", "copilot", "cursor"},
                             f"{workflow_md}: canonical backend blocks incomplete")

    def test_protected_prose_byte_exact(self):
        text = read(SKILLS / "flow-next-plan-review/SKILL.md")
        self.assertIn(FOREGROUND_RULE_BULLET, text,
                      "plan-review Foreground rule bullet drifted (must stay byte-exact)")
        self.assertIn(CAP_SENTENCE, text,
                      "fn-90 deterministic-cap sentence drifted (must stay byte-exact)")

    def test_no_agent_side_iteration_counting(self):
        for rel in ("flow-next-plan-review/SKILL.md", "flow-next-plan-review/workflow.md"):
            for path in both_copies(rel):
                self.assertNotIn("iteration counter in agent context", read(path),
                                 f"{path}: agent-side review counting reintroduced (fn-90)")


if __name__ == "__main__":
    unittest.main()
