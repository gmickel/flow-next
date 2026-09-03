"""fn-219.2 - static contract pins for pilot in-tick stage chaining
(`pipeline.chainStages`, R2-R5, R11).

Honest harness limitation: the chain lives in host-agent prose and bash inside
the pilot skill workflow, not flowctl Python - there is no executable harness
for a tick (no `gh`, no host agent in CI). So the load-bearing invariants are
pinned as the smallest distinctive tokens (G2 - never a sentence, never a
size baseline):

* the gate derives from the root config snapshot (`.value.pipeline.chainStages`)
  and adds no `config get` (the fn-110 single-call contract);
* the verdict grammar admits the `qa+make-pr` stage token;
* the chain block names `make-pr` as its only target, requires `QA_ADVANCED`,
  and never names `plan-review` or `work` as a target;
* dry-run reports `chain=` plus a precondition-checked `would-chain=`;
* every authoritative single-stage surface carries the gated clause, pinned by
  the key name `chainStages`.

Canonical files only: task fn-219.4 regenerates the codex mirror once and
extends these pins to the mirror copies via the `both_copies` pattern.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = PLUGIN_DIR.parent.parent

PILOT_SKILL = PLUGIN_DIR / "skills" / "flow-next-pilot"
SKILL_MD = PILOT_SKILL / "SKILL.md"
WORKFLOW = PILOT_SKILL / "workflow.md"
BACKLOG_MODE = PILOT_SKILL / "references" / "backlog-mode.md"
COMMAND_MD = PLUGIN_DIR / "commands" / "pilot.md"
CONDUCT_MD = REPO_ROOT / "agent_docs" / "conduct" / "pilot.md"
SYNC_SCRIPT = REPO_ROOT / "scripts" / "sync-codex.sh"

CONFIG_GET = re.compile(r'\$FLOWCTL"?\s+config get')
CHAIN_KEY_READ = ".value.pipeline.chainStages"
CHAIN_STAGE_TOKEN = "qa+make-pr"
CHAIN_HEADING = "### Chained stage (`pipeline.chainStages`)"
# The two hardcoded pilot description strings the sync script emits into the
# Codex catalog (each capped by the shared skills budget).
CATALOG_DESCRIPTION_CAP = 200


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def h2_section(text: str, heading: str) -> str:
    """Slice from `heading` (any level) up to the next H2 (`## `) line."""
    start = text.index(heading)
    m = re.search(r"^## ", text[start + len(heading):], flags=re.M)
    end = start + len(heading) + m.start() if m else len(text)
    return text[start:end]


def paragraph_starting(text: str, prefix: str) -> str:
    start = text.index(prefix)
    end = text.find("\n\n", start)
    return text[start:end if end != -1 else len(text)]


class ChainGateReadTestCase(unittest.TestCase):
    def test_gate_derives_from_root_snapshot_with_no_new_config_get(self):
        wf = read(WORKFLOW)
        self.assertIn(CHAIN_KEY_READ, wf)
        self.assertEqual(len(CONFIG_GET.findall(wf)), 0,
                         "workflow.md must derive the chain gate via jq, never config get")
        self.assertEqual(len(CONFIG_GET.findall(read(SKILL_MD))), 1,
                         "SKILL.md still owns the ONE config call")

    def test_only_literal_on_enables_and_error_is_off(self):
        wf = read(WORKFLOW)
        self.assertIn('[ "${CHAIN_STAGES:-}" = "on" ] && CHAIN_ENABLED=1', wf)
        # Fail-closed: the jq read's error branch resolves to an empty (off)
        # value, never to an ACTIVE-style fail-open flag.
        self.assertIn('2>/dev/null)" || CHAIN_STAGES=""', wf)


class ChainTableTestCase(unittest.TestCase):
    def setUp(self):
        self.block = h2_section(read(WORKFLOW), CHAIN_HEADING)

    def test_block_requires_fresh_qa_advance(self):
        self.assertIn("QA_ADVANCED=true", self.block)
        self.assertIn("CHAIN_ENABLED=1", self.block)

    def test_block_targets_make_pr_only(self):
        self.assertIn("/flow-next:make-pr <spec-id> mode:autonomous", self.block)
        self.assertNotIn("plan-review", self.block,
                         "plan-review is never a chain target (dissolved: plan embeds its review)")
        self.assertNotRegex(self.block, r"(→|->)\s*`?work`?",
                            "work is never chained into")

    def test_backlog_dispatch_is_guarded_before_the_chained_make_pr(self):
        self.assertIn('assert_allowed_dispatch "$DISPATCH_TARGET"', self.block)
        self.assertIn('DISPATCH_TARGET="/flow-next:make-pr"', self.block)


class VerdictGrammarTestCase(unittest.TestCase):
    def test_stage_token_admitted_on_both_authoritative_surfaces(self):
        for path in (SKILL_MD, WORKFLOW):
            self.assertIn(CHAIN_STAGE_TOKEN, read(path), f"{path}: stage token missing")

    def test_chained_verdict_lines_use_the_joined_stage_token(self):
        wf = read(WORKFLOW)
        self.assertIn(f"PILOT_VERDICT=ADVANCED spec=<id> stage={CHAIN_STAGE_TOKEN}", wf)
        self.assertIn(f"PILOT_VERDICT=BLOCKED spec=<id> stage={CHAIN_STAGE_TOKEN}", wf)

    def test_backlog_decision_log_is_per_dispatched_stage(self):
        wf = read(WORKFLOW)
        self.assertIn("one row per dispatched stage", wf)
        self.assertNotIn("exactly one row per acting backlog tick", wf)
        # The chained tick has a concrete two-append template: the qa row is
        # always `advanced` with no cost; the make-pr row carries the terminal
        # action and the whole-tick cost once.
        self.assertIn('--action advanced --stage qa', wf)
        self.assertIn('--action "$ACTION" --stage make-pr ${COST_TOKENS:+--cost-tokens "$COST_TOKENS"}', wf)

    def test_make_pr_verify_probe_captures_gh_status(self):
        # A bare `gh | jq | head` pipeline swallows a gh failure into an empty
        # URL (a false strike). The probe must capture gh's status separately
        # and route failure to crash-class NEEDS_HUMAN.
        wf = read(WORKFLOW)
        start = wf.find("For `make-pr`, advancement means")
        end = wf.find("Echo the URL when present", start)
        self.assertTrue(start != -1 and end != -1, "make-pr verify block not found")
        block = wf[start:end]
        self.assertIn("PR_VERIFY_FAILED=0", block)
        self.assertIn(") || PR_VERIFY_FAILED=1", block)
        self.assertIn('stage=make-pr reason="gh probe failed at make-pr verify"', block)
        self.assertNotIn("OPEN_PR_URL=$(gh pr list", block)


class DryRunReportTestCase(unittest.TestCase):
    def test_dry_run_paragraph_reports_chain_and_would_chain(self):
        para = paragraph_starting(read(WORKFLOW), "Dry-run stops after classification.")
        self.assertIn("chain=<off|on>", para)
        self.assertIn("would-chain=make-pr", para)
        self.assertIn("would-chain=none (stage <x> heads no pair)", para)


class SingleStageSurfacesTestCase(unittest.TestCase):
    def test_every_single_stage_surface_carries_the_gated_clause(self):
        for path in (SKILL_MD, WORKFLOW, BACKLOG_MODE, COMMAND_MD, CONDUCT_MD):
            self.assertIn("chainStages", read(path), f"{path}: gated clause missing")

    def test_conduct_checklist_names_the_closed_table(self):
        conduct = read(CONDUCT_MD)
        self.assertIn("pipeline.chainStages", conduct)
        self.assertIn("never names `plan-review` as a target", conduct)
        self.assertIn(CHAIN_STAGE_TOKEN, conduct)

    def test_sync_script_pilot_descriptions_carry_the_clause_under_the_cap(self):
        lines = [
            ln for ln in read(SYNC_SCRIPT).splitlines()
            if ln.startswith('generate_openai_yaml "flow-next-pilot"')
            or ln.lstrip().startswith('"flow-next-pilot":')
        ]
        self.assertEqual(len(lines), 2, "expected the two hardcoded pilot descriptions")
        for ln in lines:
            desc = re.findall(r'"(Single-tick[^"]*)"', ln)
            self.assertEqual(len(desc), 1, ln)
            self.assertIn("chainStages", desc[0], ln)
            self.assertLessEqual(len(desc[0]), CATALOG_DESCRIPTION_CAP, ln)
            # The mirror writes these as UNQUOTED YAML scalars: a `: ` inside
            # the value is a mapping separator and breaks frontmatter parsing.
            self.assertNotIn(": ", desc[0], ln)


if __name__ == "__main__":
    unittest.main()
