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
  * plan-review: common orchestration + exactly one selected backend workflow;
    none/export stay backend-cold; the Foreground rule and the fn-90
    deterministic-cap sentence are byte-exact; no agent-side iteration
    counting is (re)introduced (R6).

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
    "**The cap is enforced deterministically by flowctl:** every dispatch "
    "reserves a\nspec-scoped round before launch. SHIP / NEEDS_WORK / "
    "MAJOR_RETHINK consume it;\na no-verdict transport failure is durably "
    "recorded and refunded. At\n`${MAX_REVIEW_ITERATIONS:-4}` verdict rounds, "
    "flowctl refuses with `ESCALATE:`\nand exit 4. More than "
    "`${MAX_REVIEW_TRANSPORT_FAILURES:-2}` consecutive\nno-verdict failures "
    "stop separately with `TRANSPORT_UNHEALTHY` + exit 5.\nCallers invoke "
    "plan-review once and act on its terminal result. The verdict\ncounter "
    "resets only on SHIP or an explicit re-plan, never on an edit, fresh\n"
    "invocation, or transport failure.**"
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
            # Explicit status-branch capture: `|| echo '{}'` would APPEND to partial
            # JSON a failing flowctl printed, yielding two documents per jq lookup.
            self.assertIn("if ! LAND_CFG=", phase0,
                          f"{path}: land capture must use the explicit status branch")
            self.assertNotRegex(
                phase0, r'LAND_CFG="\$\([^)]*\|\|',
                f"{path}: appending-fallback LAND_CFG capture reintroduced")
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

    def test_plan_optional_routes_load_one_level_references_after_gates(self):
        steps = read(SKILLS / "flow-next-plan/steps.md")
        cases = (
            ("## Step 6.5", "## Step 7", "tracker.perEvent.plan",
             "references/tracker-projection.md"),
            ("## Step 7", "## Step 8", "review mode is `none`",
             "references/selected-review.md"),
            ("## Step 8.5", None, "artifacts.html.enabled",
             "references/html-render-lens.md"),
        )
        for start, end, gate, reference in cases:
            body = section(steps, start, end) if end else steps[steps.index(start):]
            self.assertIn(gate, body)
            self.assertIn(reference, body)
            self.assertLess(body.index(gate), body.index(reference),
                            f"{reference}: reference must follow its route gate")
            root = SKILLS / "flow-next-plan"
            path = root / reference
            self.assertTrue(path.is_file(), f"missing routed reference: {path}")
            # References remain exactly one directory level under the skill root.
            self.assertEqual(len(path.relative_to(root).parts), 2)

    def test_plan_optional_details_are_cold_in_steps(self):
        steps = read(SKILLS / "flow-next-plan/steps.md")
        for detail in (
            "Never create one tracker issue per task",
            "lavish-axi \"$(pwd)/.flow/artifacts",
            "Repeat until review returns `Ship`",
        ):
            self.assertNotIn(detail, steps)
        for rel, detail in (
            ("references/tracker-projection.md", "Never create one tracker issue per task"),
            ("references/html-render-lens.md", "lavish-axi \"$(pwd)/.flow/artifacts"),
            ("references/selected-review.md", "Repeat until review returns `Ship`"),
        ):
            self.assertIn(detail, read(SKILLS / "flow-next-plan" / rel))

    def test_plan_bad_examples_are_short_anti_pattern_anchors(self):
        examples = read(SKILLS / "flow-next-plan/examples.md")
        epic_bad = section(examples, "### ❌ BAD: Epic", "### ✅ GOOD: Epic")
        task_bad = section(examples, "### ❌ BAD: Task", "### ✅ GOOD: Task")
        for name, bad in (("epic", epic_bad), ("task", task_bad)):
            code_lines = [
                line for line in bad.splitlines()
                if line and not line.startswith(("###", "```", "\\`\\`\\`", "**", "- "))
            ]
            self.assertLessEqual(len(code_lines), 12,
                                 f"{name} BAD anchor regrew into an implementation dump")
        self.assertNotIn("Bun.spawn", task_bad)
        self.assertNotIn("process.kill", task_bad)

    def test_plan_holdout_keeps_subject_and_answer_key_separate(self):
        holdout = REPO / "optimization" / "plan" / "holdout"
        subject = read(holdout / "input.md")
        oracle = read(holdout / "oracle.md")
        self.assertIn("no-code permit-intake architecture", subject)
        self.assertIn("H10 — review route", oracle)
        self.assertNotIn("H1 — no implementation leakage", subject)


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

    def test_dry_run_terminals_remove_the_snapshot(self):
        # Dry-run leaves no persistent scratch state. The CENTRAL rule lives in
        # SKILL.md's verdict contract (EVERY dry-run terminal removes the
        # snapshot — same "at every terminal" pattern as SETUP_STALE), and the
        # two fenced/inline dry-run terminals in workflow.md carry it verbatim.
        rm_expr = ('rm -f "${TMPDIR:-/tmp}/flow-pilot-config-'
                   "$(git rev-parse --show-toplevel 2>/dev/null | cksum | cut -d' ' -f1).json\"")
        for path in both_copies("flow-next-pilot/SKILL.md"):
            text = read(path)
            self.assertIn("Dry-run snapshot cleanup.", text,
                          f"{path}: verdict-contract cleanup rule missing")
            self.assertIn(rm_expr, text,
                          f"{path}: verdict-contract rule must carry the rm line")
        for path in both_copies("flow-next-pilot/workflow.md"):
            self.assertGreaterEqual(
                read(path).count(rm_expr), 2,
                f"{path}: dry-run terminals must remove the config snapshot")

    def test_backlog_mode_has_zero_flowctl_config_calls(self):
        for path in both_copies("flow-next-pilot/references/backlog-mode.md"):
            self.assertNotRegex(read(path), r'\$FLOWCTL"?\s+config\b',
                                f"{path}: backlog-mode.md must be config-call-free")

    def test_snapshot_consumers_recompute_the_deterministic_path(self):
        # The snapshot lives under ${TMPDIR} (never repo-controlled .flow/tmp —
        # autonomous symlink safety + dry-run mutates nothing in the repo) at a
        # deterministic repo-hash-keyed path each fence recomputes identically.
        snapshot_expr = (
            'PILOT_CFG_SNAPSHOT="${TMPDIR:-/tmp}/flow-pilot-config-'
            '$(git rev-parse --show-toplevel 2>/dev/null | cksum | cut -d\' \' -f1).json"'
        )
        for rel in ("SKILL.md", "workflow.md", "references/backlog-mode.md"):
            for path in both_copies(f"flow-next-pilot/{rel}"):
                text = read(path)
                self.assertIn(snapshot_expr, text,
                              f"{path}: must recompute the deterministic snapshot path")
                self.assertNotIn(".flow/tmp/pilot-config", text,
                                 f"{path}: snapshot must not live under repo-controlled .flow/tmp")


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
            # Interactive asks happen OUTSIDE fences: the fence exits with a
            # NEED_INPUT marker and is re-run with the value preset (a Bash call
            # cannot pause for AskUserQuestion).
            self.assertIn("NEED_INPUT:", phase0,
                          f"{path}: interactive-ask exemption marker missing")


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
    BACKENDS = ("codex", "copilot", "cursor", "host", "rp")

    def test_backend_blocks_live_only_in_selected_workflows(self):
        skill_dir = SKILLS / "flow-next-plan-review"
        self.assertEqual(self.INVOKE.findall(read(skill_dir / "SKILL.md")), [])
        self.assertEqual(self.INVOKE.findall(read(skill_dir / "workflow.md")), [])
        for backend in ("codex", "copilot", "cursor"):
            path = skill_dir / f"workflow-{backend}.md"
            self.assertEqual(
                self.INVOKE.findall(read(path)),
                [backend],
                f"{path}: must contain exactly its selected backend dispatch",
            )

    def test_router_lists_every_backend_once_and_keeps_none_export_cold(self):
        skill = read(SKILLS / "flow-next-plan-review/SKILL.md")
        for backend in self.BACKENDS:
            link = f"[workflow-{backend}.md](workflow-{backend}.md)"
            self.assertEqual(skill.count(link), 1, f"router drift for {backend}")
        self.assertIn("`BACKEND=none` and explicit\n`--review=export`", skill)
        common = read(SKILLS / "flow-next-plan-review/workflow.md")
        self.assertIn("Load no backend file", common)
        self.assertIn("Do not resolve or load any configured\nbackend", common)

    def test_codex_mirror_is_b1_or_regenerated_split(self):
        """Parallel workers defer mirror regen; integrated tree must be split."""
        mirror = MIRROR_SKILLS / "flow-next-plan-review"
        if (mirror / "workflow-codex.md").exists():
            for backend in self.BACKENDS:
                self.assertTrue((mirror / f"workflow-{backend}.md").is_file())
            self.assertEqual(self.INVOKE.findall(read(mirror / "workflow.md")), [])
        else:
            # The conductor owns the combined sync. Before that sync, the
            # isolated worker must leave the known B1 monolith untouched.
            self.assertEqual(
                set(self.INVOKE.findall(read(mirror / "workflow.md"))),
                {"codex", "copilot", "cursor"},
            )

    def test_protected_prose_byte_exact(self):
        text = read(SKILLS / "flow-next-plan-review/SKILL.md")
        self.assertIn(FOREGROUND_RULE_BULLET, text,
                      "plan-review Foreground rule bullet drifted (must stay byte-exact)")
        self.assertIn(CAP_SENTENCE, text,
                      "fn-90 deterministic-cap sentence drifted (must stay byte-exact)")

    def test_subprocess_fences_redeclare_spec_id(self):
        for backend in ("codex", "copilot", "cursor"):
            path = SKILLS / "flow-next-plan-review" / f"workflow-{backend}.md"
            text = read(path)
            self.assertIn('SPEC_ID="${1:-}"', text)
            self.assertIn(f"$FLOWCTL {backend} plan-review", text)

    def test_no_agent_side_iteration_counting(self):
        for path in (SKILLS / "flow-next-plan-review").glob("*.md"):
            self.assertNotIn("iteration counter in agent context", read(path),
                             f"{path}: agent-side review counting reintroduced (fn-90)")


if __name__ == "__main__":
    unittest.main()
