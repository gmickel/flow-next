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

Pinned on the canonical skill files AND their codex-mirror copies (the
`both_copies` pattern from test_skill_prose_diet.py): fn-219.4 regenerated the
mirror once, after every canonical prose task landed. Surfaces with no mirror
copy (`commands/pilot.md`, the conduct checklist, the sync script) stay
canonical-only.
"""

from __future__ import annotations

import re
import shutil
import sys
import unittest
from pathlib import Path

# The executable fence tests run the workflow's bash through a POSIX bash with
# jq on PATH; the Windows CI job has neither the coreutils the fences assume
# nor a UTF-8 subprocess encoding for the prose comments, so they skip there
# (the token pins still run everywhere).
_POSIX_BASH = unittest.skipIf(
    sys.platform == "win32" or shutil.which("bash") is None or shutil.which("jq") is None,
    "executable fence tests need a POSIX bash + jq",
)

PLUGIN_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = PLUGIN_DIR.parent.parent

PILOT_SKILL = PLUGIN_DIR / "skills" / "flow-next-pilot"
MIRROR_PILOT_SKILL = PLUGIN_DIR / "codex" / "skills" / "flow-next-pilot"
COMMAND_MD = PLUGIN_DIR / "commands" / "pilot.md"
CONDUCT_MD = REPO_ROOT / "agent_docs" / "conduct" / "pilot.md"
SYNC_SCRIPT = REPO_ROOT / "scripts" / "sync-codex.sh"

CONFIG_GET = re.compile(r'\$FLOWCTL"?\s+config get')
CHAIN_KEY_READ = ".value.pipeline.chainStages"
CHAIN_STAGE_TOKEN = "qa+make-pr"
CHAIN_HEADING = "### Chained stage (`pipeline.chainStages`)"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def both_copies(rel: str) -> list[Path]:
    """Canonical pilot file + its codex-mirror copy (mirror must exist)."""
    canonical = PILOT_SKILL / rel
    mirrored = MIRROR_PILOT_SKILL / rel
    assert canonical.exists(), f"missing canonical file: {rel}"
    assert mirrored.exists(), f"missing codex mirror copy: {rel}"
    return [canonical, mirrored]


SKILL_MDS = both_copies("SKILL.md")
WORKFLOWS = both_copies("workflow.md")
BACKLOG_MODES = both_copies("references/backlog-mode.md")


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
        for path in WORKFLOWS:
            wf = read(path)
            self.assertIn(CHAIN_KEY_READ, wf, path)
            self.assertEqual(len(CONFIG_GET.findall(wf)), 0,
                             f"{path}: must derive the chain gate via jq, never config get")
        for path in SKILL_MDS:
            self.assertEqual(len(CONFIG_GET.findall(read(path))), 1,
                             f"{path}: SKILL.md still owns the ONE config call")

    def test_only_literal_on_enables_and_error_is_off(self):
        for path in WORKFLOWS:
            wf = read(path)
            self.assertIn('if [ "${CHAIN_STAGES:-}" = "on" ]; then CHAIN_ENABLED=1; fi', wf, path)
            # Fail-closed: the jq read's error branch resolves to an empty (off)
            # value, never to an ACTIVE-style fail-open flag.
            self.assertIn('2>/dev/null)" || CHAIN_STAGES=""', wf, path)


class ChainTableTestCase(unittest.TestCase):
    def blocks(self):
        return [(path, h2_section(read(path), CHAIN_HEADING)) for path in WORKFLOWS]

    def test_block_requires_fresh_qa_advance(self):
        for path, block in self.blocks():
            self.assertIn("QA_ADVANCED=true", block, path)
            self.assertIn("CHAIN_ENABLED=1", block, path)

    def test_block_targets_make_pr_only(self):
        for path, block in self.blocks():
            self.assertIn("/flow-next:make-pr <spec-id> mode:autonomous", block, path)
            self.assertNotIn("plan-review", block,
                             f"{path}: plan-review is never a chain target (dissolved: plan embeds its review)")
            self.assertNotRegex(block, r"(→|->)\s*`?work`?",
                                f"{path}: work is never chained into")

    def test_backlog_dispatch_is_guarded_before_the_chained_make_pr(self):
        for path, block in self.blocks():
            self.assertIn('assert_allowed_dispatch "$DISPATCH_TARGET"', block, path)
            self.assertIn('DISPATCH_TARGET="/flow-next:make-pr"', block, path)


class VerdictGrammarTestCase(unittest.TestCase):
    def test_stage_token_admitted_on_both_authoritative_surfaces(self):
        for path in (*SKILL_MDS, *WORKFLOWS):
            self.assertIn(CHAIN_STAGE_TOKEN, read(path), f"{path}: stage token missing")

    def test_chained_verdict_lines_use_the_joined_stage_token(self):
        for path in WORKFLOWS:
            wf = read(path)
            self.assertIn(f"PILOT_VERDICT=ADVANCED spec=<id> stage={CHAIN_STAGE_TOKEN}", wf, path)
            self.assertIn(f"PILOT_VERDICT=BLOCKED spec=<id> stage={CHAIN_STAGE_TOKEN}", wf, path)

    def test_backlog_decision_log_is_per_dispatched_stage(self):
        for path in WORKFLOWS:
            wf = read(path)
            # The chained tick has a concrete two-append template: the qa row is
            # always `advanced` with no cost; the make-pr row carries the terminal
            # action and the whole-tick cost once.
            self.assertIn('--action advanced --stage qa', wf, path)
            self.assertIn('--action "$ACTION" --stage make-pr ${COST_TOKENS:+--cost-tokens "$COST_TOKENS"}', wf, path)

    @_POSIX_BASH
    def test_make_pr_verify_probe_parse_failure_is_flagged(self):
        # Executable: run the verify parse fence against valid, empty, and
        # malformed probe output. A malformed body must set PR_VERIFY_FAILED=1
        # (jq is the status-bearing command — no trailing `head` masks it);
        # a valid body yields the first OPEN url; no OPEN row yields "" with
        # the flag still 0 (the healthy-no-advance path).
        import subprocess
        cases = {
            '[{"state":"CLOSED","url":"c"},{"state":"OPEN","url":"https://x/1"}]': ("https://x/1", "0"),
            '[{"state":"CLOSED","url":"c"}]': ("", "0"),
            '{not json': ("", "1"),
        }
        for path in WORKFLOWS:
            line = next(l for l in read(path).splitlines() if l.startswith("OPEN_PR_URL=$(printf"))
            for body, (url, failed) in cases.items():
                script = f"PR_VERIFY_FAILED=0\nPR_VERIFY_JSON={body!r}\n{line}\nprintf '%s|%s' \"$OPEN_PR_URL\" \"$PR_VERIFY_FAILED\""
                out = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
                self.assertEqual(out, f"{url}|{failed}", f"{path}: {body}")

    @_POSIX_BASH
    def test_chain_gate_fence_exits_zero_for_off_and_on(self):
        # Executable: the gate fence must resolve off/on AND exit 0 either way
        # (a trailing `[ ... ] && X=1` returns 1 on the default-off path).
        for path in WORKFLOWS:
            with self.subTest(copy=path):
                self._check_chain_gate_fence(read(path))

    def _check_chain_gate_fence(self, wf: str):
        import json
        import subprocess
        import tempfile
        start = wf.find("CHAIN_ENABLED=0\n")
        end = wf.find("```", start)
        fence = wf[start:end]
        self.assertIn("if [", fence)
        for value, want in (("off", "0"), ("on", "1"), (True, "0"), ("maybe", "0")):
            with tempfile.TemporaryDirectory() as td:
                snap = Path(td) / "snap.json"
                snap.write_text(json.dumps({"key": None, "value": {"pipeline": {"chainStages": value}}}))
                script = fence.replace(
                    'PILOT_CFG_SNAPSHOT="${TMPDIR:-/tmp}/flow-pilot-config-$(git rev-parse --show-toplevel 2>/dev/null | cksum | cut -d\' \' -f1).json"',
                    f'PILOT_CFG_SNAPSHOT="{snap}"',
                ) + '\nprintf "%s" "$CHAIN_ENABLED"'
                self.assertIn(str(snap), script, "snapshot path substitution failed")
                res = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
                self.assertEqual(res.returncode, 0, f"{value}: fence exited {res.returncode}")
                self.assertEqual(res.stdout, want, f"{value}: CHAIN_ENABLED")
        # missing snapshot ⇒ off, still exit 0
        script = fence.replace(
            'PILOT_CFG_SNAPSHOT="${TMPDIR:-/tmp}/flow-pilot-config-$(git rev-parse --show-toplevel 2>/dev/null | cksum | cut -d\' \' -f1).json"',
            'PILOT_CFG_SNAPSHOT="/nonexistent/snap.json"',
        ) + '\nprintf "%s" "$CHAIN_ENABLED"'
        res = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
        self.assertEqual((res.returncode, res.stdout), (0, "0"))

    def test_make_pr_verify_probe_captures_gh_status(self):
        # A bare `gh | jq | head` pipeline swallows a gh failure into an empty
        # URL (a false strike). The probe must capture gh's status separately
        # and route failure to crash-class NEEDS_HUMAN.
        for path in WORKFLOWS:
            wf = read(path)
            start = wf.find("For `make-pr`, advancement means")
            end = wf.find("Echo the URL when present", start)
            self.assertTrue(start != -1 and end != -1, f"{path}: make-pr verify block not found")
            block = wf[start:end]
            self.assertIn("PR_VERIFY_FAILED=0", block, path)
            self.assertIn(") || PR_VERIFY_FAILED=1", block, path)
            self.assertIn('stage=make-pr reason="gh probe failed at make-pr verify"', block, path)
            self.assertNotIn("OPEN_PR_URL=$(gh pr list", block, path)


class DryRunReportTestCase(unittest.TestCase):
    def test_dry_run_paragraph_reports_chain_and_would_chain(self):
        for path in WORKFLOWS:
            para = paragraph_starting(read(path), "Dry-run stops after classification.")
            self.assertIn("chain=<off|on>", para, path)
            self.assertIn("would-chain=make-pr", para, path)
            self.assertIn("would-chain=none (stage <x> heads no pair)", para, path)


class SingleStageSurfacesTestCase(unittest.TestCase):
    def test_every_single_stage_surface_carries_the_gated_clause(self):
        for path in (*SKILL_MDS, *WORKFLOWS, *BACKLOG_MODES, COMMAND_MD, CONDUCT_MD):
            self.assertIn("chainStages", read(path), f"{path}: gated clause missing")

    def test_conduct_checklist_names_the_closed_table(self):
        conduct = read(CONDUCT_MD)
        self.assertIn("pipeline.chainStages", conduct)
        self.assertIn(CHAIN_STAGE_TOKEN, conduct)

    def test_sync_script_pilot_descriptions_carry_the_clause_as_valid_yaml(self):
        # The catalog length cap is enforced by the sync script's own hard-fail
        # guard at regen time — not re-pinned here (G2: no size baselines).
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
            # The mirror writes these as UNQUOTED YAML scalars: a `: ` inside
            # the value is a mapping separator and breaks frontmatter parsing.
            self.assertNotIn(": ", desc[0], ln)


if __name__ == "__main__":
    unittest.main()
