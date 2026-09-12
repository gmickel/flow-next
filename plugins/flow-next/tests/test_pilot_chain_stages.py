"""Static contract pins for in-tick stage chaining (`pipeline.chainStages`)
under the unattended driver (`flow --auto --tick`, formerly the pilot tick).

Honest harness limitation: the chain lives in host-agent prose and bash inside
`skills/flow-next-flow/auto.md`, not flowctl Python - there is no executable
harness for a hop (no `gh`, no host agent in CI). So the load-bearing
invariants are pinned as the smallest distinctive tokens (G2 - never a
sentence, never a size baseline), plus executable runs of the two bash fences
that can run standalone:

* the gate derives from the root config snapshot (`.value.pipeline.chainStages`)
  and adds no `config get` (the single-call contract: the ONE call lives in
  auto.md's autonomy block, and the chain fence is jq-only);
* the gate is honoured only under `--tick` (`AUTO_TICK=1`); in long-horizon
  mode `on` leaves `CHAIN_ENABLED=0` and prints one stderr notice;
* the verdict grammar admits the `qa+make-pr` stage token;
* the chain block names `make-pr` as its only target, requires `QA_ADVANCED`,
  and never names `plan-review` or `work` as a target;
* explain reports `chain=` plus a precondition-checked `would-chain=`;
* every authoritative single-stage surface carries the gated clause, pinned by
  the key name `chainStages`.

`auto.md` is the single always-loaded-under---auto file; where the pilot
tests distinguished SKILL.md from workflow.md, both now resolve to auto.md.
Pinned on the canonical file AND its codex-mirror copy (the `both_copies`
pattern from test_skill_prose_diet.py). Surfaces with no mirror copy (the
conduct checklist, the sync script) stay canonical-only.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# The executable fence tests run the driver's bash through a POSIX bash with
# jq on PATH; the Windows CI job has neither the coreutils the fences assume
# nor a UTF-8 subprocess encoding for the prose comments, so they skip there
# (the token pins still run everywhere).
_POSIX_BASH = unittest.skipIf(
    sys.platform == "win32" or shutil.which("bash") is None or shutil.which("jq") is None,
    "executable fence tests need a POSIX bash + jq",
)

PLUGIN_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = PLUGIN_DIR.parent.parent

FLOW_SKILL = PLUGIN_DIR / "skills" / "flow-next-flow"
MIRROR_FLOW_SKILL = PLUGIN_DIR / "codex" / "skills" / "flow-next-flow"
PILOT_STUB = PLUGIN_DIR / "skills" / "flow-next-pilot" / "SKILL.md"
CONDUCT_MD = REPO_ROOT / "agent_docs" / "conduct" / "pilot.md"
SYNC_SCRIPT = REPO_ROOT / "scripts" / "sync-codex.sh"

CONFIG_GET = re.compile(r'\$FLOWCTL"?\s+config get')
CHAIN_KEY_READ = ".value.pipeline.chainStages"
CHAIN_STAGE_TOKEN = "qa+make-pr"
CHAIN_HEADING = "### Chained stage (`pipeline.chainStages`, `--tick` only)"
SNAPSHOT_LINE = (
    'PILOT_CFG_SNAPSHOT="${TMPDIR:-/tmp}/flow-pilot-config-'
    "$(git rev-parse --show-toplevel 2>/dev/null | cksum | cut -d' ' -f1).json\""
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def both_copies(rel: str) -> list[Path]:
    """Canonical flow-skill file + its codex-mirror copy (mirror must exist)."""
    canonical = FLOW_SKILL / rel
    mirrored = MIRROR_FLOW_SKILL / rel
    assert canonical.exists(), f"missing canonical file: {rel}"
    assert mirrored.exists(), f"missing codex mirror copy: {rel}"
    return [canonical, mirrored]


AUTO_MDS = both_copies("auto.md")
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


def chain_gate_fence(text: str) -> str:
    start = text.find("CHAIN_ENABLED=0\n")
    assert start != -1, "chain gate fence not found"
    end = text.find("```", start)
    return text[start:end]


class ChainGateReadTestCase(unittest.TestCase):
    def test_gate_derives_from_root_snapshot_with_no_new_config_get(self):
        for path in AUTO_MDS:
            text = read(path)
            self.assertIn(CHAIN_KEY_READ, text, path)
            # auto.md owns the ONE config call (the root snapshot); the chain
            # gate fence itself is jq-only.
            self.assertEqual(len(CONFIG_GET.findall(text)), 1,
                             f"{path}: auto.md owns exactly ONE config call")
            self.assertEqual(len(CONFIG_GET.findall(chain_gate_fence(text))), 0,
                             f"{path}: must derive the chain gate via jq, never config get")

    def test_only_literal_on_under_tick_enables_and_error_is_off(self):
        for path in AUTO_MDS:
            fence = chain_gate_fence(read(path))
            self.assertIn('if [ "${CHAIN_STAGES:-}" = "on" ]; then', fence, path)
            self.assertIn('if [ "${AUTO_TICK:-0}" = "1" ]; then', fence, path)
            self.assertIn("CHAIN_ENABLED=1", fence, path)
            # Fail-closed: the jq read's error branch resolves to an empty (off)
            # value, never to an ACTIVE-style fail-open flag.
            self.assertIn('2>/dev/null)" || CHAIN_STAGES=""', fence, path)


class ChainTableTestCase(unittest.TestCase):
    def blocks(self):
        return [(path, h2_section(read(path), CHAIN_HEADING)) for path in AUTO_MDS]

    def test_block_requires_fresh_qa_advance(self):
        for path, block in self.blocks():
            self.assertIn("QA_ADVANCED=true", block, path)
            self.assertIn("CHAIN_ENABLED=1", block, path)
            self.assertIn("AUTO_TICK=1", block, path)

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
    def test_stage_token_admitted_on_the_authoritative_surface(self):
        for path in AUTO_MDS:
            self.assertIn(CHAIN_STAGE_TOKEN, read(path), f"{path}: stage token missing")

    def test_chained_verdict_lines_use_the_joined_stage_token(self):
        for path in AUTO_MDS:
            text = read(path)
            self.assertIn(f"PILOT_VERDICT=ADVANCED spec=<id> stage={CHAIN_STAGE_TOKEN}", text, path)
            self.assertIn(f"PILOT_VERDICT=BLOCKED spec=<id> stage={CHAIN_STAGE_TOKEN}", text, path)

    def test_backlog_decision_log_is_per_dispatched_stage(self):
        for path in AUTO_MDS:
            text = read(path)
            # The chained tick has a concrete two-append template: the qa row is
            # always `advanced` with no cost; the make-pr row carries the terminal
            # action and the whole-tick cost once.
            self.assertIn('--action advanced --stage qa', text, path)
            self.assertIn('--action "$ACTION" --stage make-pr ${COST_TOKENS:+--cost-tokens "$COST_TOKENS"}', text, path)

    @_POSIX_BASH
    def test_make_pr_verify_probe_parse_failure_is_flagged(self):
        # Executable: run the verify parse fence against valid, empty, and
        # malformed probe output. A malformed body must set PR_VERIFY_FAILED=1
        # (jq is the status-bearing command — no trailing `head` masks it);
        # a valid body yields the first OPEN url; no OPEN row yields "" with
        # the flag still 0 (the healthy-no-advance path).
        cases = {
            '[{"state":"CLOSED","url":"c"},{"state":"OPEN","url":"https://x/1"}]': ("https://x/1", "0"),
            '[{"state":"CLOSED","url":"c"}]': ("", "0"),
            '{not json': ("", "1"),
        }
        for path in AUTO_MDS:
            line = next(l for l in read(path).splitlines() if l.startswith("OPEN_PR_URL=$(printf"))
            for body, (url, failed) in cases.items():
                script = f"PR_VERIFY_FAILED=0\nPR_VERIFY_JSON={body!r}\n{line}\nprintf '%s|%s' \"$OPEN_PR_URL\" \"$PR_VERIFY_FAILED\""
                out = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
                self.assertEqual(out, f"{url}|{failed}", f"{path}: {body}")

    @_POSIX_BASH
    def test_chain_gate_fence_exits_zero_and_chains_only_under_tick(self):
        # Executable: the gate fence must resolve off/on AND exit 0 either way
        # (a trailing `[ ... ] && X=1` returns 1 on the default-off path).
        # `on` chains only under --tick (AUTO_TICK=1); in long-horizon mode it
        # stays off and prints one stderr notice naming the key.
        for path in AUTO_MDS:
            with self.subTest(copy=path):
                self._check_chain_gate_fence(read(path))

    def _run_fence(self, fence: str, snapshot: str, auto_tick: str) -> subprocess.CompletedProcess:
        script = fence.replace(SNAPSHOT_LINE, f'PILOT_CFG_SNAPSHOT="{snapshot}"')
        self.assertIn(snapshot, script, "snapshot path substitution failed")
        script += '\nprintf "%s" "$CHAIN_ENABLED"'
        env = {**os.environ, "AUTO_TICK": auto_tick}
        return subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=env)

    def _check_chain_gate_fence(self, text: str):
        fence = chain_gate_fence(text)
        self.assertIn("if [", fence)
        # (config value, AUTO_TICK) -> (CHAIN_ENABLED, stderr notice expected)
        cases = (
            ("off", "1", "0", False),
            ("on", "1", "1", False),
            ("on", "0", "0", True),
            (True, "1", "0", False),
            ("maybe", "1", "0", False),
        )
        for value, tick, want, notice in cases:
            with self.subTest(value=value, auto_tick=tick), tempfile.TemporaryDirectory() as td:
                snap = Path(td) / "snap.json"
                snap.write_text(json.dumps({"key": None, "value": {"pipeline": {"chainStages": value}}}))
                res = self._run_fence(fence, str(snap), tick)
                self.assertEqual(res.returncode, 0, f"{value}/{tick}: fence exited {res.returncode}")
                self.assertEqual(res.stdout, want, f"{value}/{tick}: CHAIN_ENABLED")
                self.assertEqual("chainStages" in res.stderr, notice, f"{value}/{tick}: stderr {res.stderr!r}")
        # missing snapshot ⇒ off, still exit 0
        res = self._run_fence(fence, "/nonexistent/snap.json", "1")
        self.assertEqual((res.returncode, res.stdout), (0, "0"))

    def test_make_pr_verify_probe_captures_gh_status(self):
        # A bare `gh | jq | head` pipeline swallows a gh failure into an empty
        # URL (a false strike). The probe must capture gh's status separately
        # and route failure to crash-class NEEDS_HUMAN.
        for path in AUTO_MDS:
            text = read(path)
            start = text.find("For `make-pr`, advancement means")
            end = text.find("Echo the URL when present", start)
            self.assertTrue(start != -1 and end != -1, f"{path}: make-pr verify block not found")
            block = text[start:end]
            self.assertIn("PR_VERIFY_FAILED=0", block, path)
            self.assertIn(") || PR_VERIFY_FAILED=1", block, path)
            self.assertIn('stage=make-pr reason="gh probe failed at make-pr verify"', block, path)
            self.assertNotIn("OPEN_PR_URL=$(gh pr list", block, path)


class ExplainReportTestCase(unittest.TestCase):
    def test_explain_paragraph_reports_chain_and_would_chain(self):
        for path in AUTO_MDS:
            text = read(path)
            self.assertIn("chain=<off|on>", text, path)
            self.assertIn("would-chain=make-pr", text, path)
            self.assertIn("would-chain=none", text, path)


class SingleStageSurfacesTestCase(unittest.TestCase):
    def test_every_single_stage_surface_carries_the_gated_clause(self):
        for path in (*AUTO_MDS, PILOT_STUB, CONDUCT_MD):
            self.assertIn("chainStages", read(path), f"{path}: gated clause missing")

    def test_conduct_checklist_names_the_closed_table(self):
        conduct = read(CONDUCT_MD)
        self.assertIn("pipeline.chainStages", conduct)
        self.assertIn(CHAIN_STAGE_TOKEN, conduct)

    def test_sync_script_pilot_descriptions_are_the_deprecated_alias_shape(self):
        # The two hardcoded pilot descriptions are now alias descriptions
        # pointing at `flow --auto --tick`; the openai.yaml row carries the
        # catalog flag `false` so the alias leaves the published tier. The
        # catalog length cap is enforced by the sync script's own hard-fail
        # guard at regen time - not re-pinned here (G2: no size baselines).
        lines = [
            ln for ln in read(SYNC_SCRIPT).splitlines()
            if ln.startswith('generate_openai_yaml "flow-next-pilot"')
            or ln.lstrip().startswith('"flow-next-pilot":')
        ]
        self.assertEqual(len(lines), 2, "expected the two hardcoded pilot descriptions")
        for ln in lines:
            targets = [s for s in re.findall(r'"([^"]*)"', ln) if "--auto --tick" in s]
            self.assertEqual(len(targets), 1, f"alias description must name the flow --auto --tick target: {ln}")
            # The mirror writes these as UNQUOTED YAML scalars: a `: ` inside
            # the value is a mapping separator and breaks frontmatter parsing.
            self.assertNotIn(": ", targets[0], ln)
        yaml_line = next(ln for ln in lines if ln.startswith("generate_openai_yaml"))
        self.assertTrue(yaml_line.rstrip().endswith(" false"),
                        f"pilot alias must be out of the catalog: {yaml_line}")


if __name__ == "__main__":
    unittest.main()
