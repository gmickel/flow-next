"""Execute the unattended scope, review and RP receipt fences (fn-255)."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SKILLS = ROOT / "skills"


def fence(relative, marker):
    text = (SKILLS / relative).read_text(encoding="utf-8")
    return next(block for block in re.findall(r"```bash\n(.*?)```", text, re.S) if marker in block)


@unittest.skipIf(os.name == "nt" or not shutil.which("bash") or not shutil.which("jq"),
                 "skill fences require POSIX bash and jq")
class UnattendedSkillFences(unittest.TestCase):
    def shell(self, code, **env):
        return subprocess.run(["bash", "-c", code], env={**os.environ, **env},
                              capture_output=True, text=True)

    def test_scope_resolution_and_unresolved_stop(self):
        code = fence("flow-next-flow/auto.md", 'if SCOPE_JSON=')
        for output, rc, expected in (
            ({"id": "wor-17-x", "tasks": []}, 0, "scope=wor-17-x"),
            ({"error": "Spec missing does not exist"}, 2, "PILOT_VERDICT=NEEDS_HUMAN"),
            ({"id": "wor-17-x.1", "status": "todo"}, 0, "PILOT_VERDICT=NEEDS_HUMAN"),
        ):
            with self.subTest(output=output):
                stub = 'flowctl() { printf "config warning\\n" >&2; printf "%s" "$OUTPUT"; return "$RC"; }\n'
                result = self.shell(stub + code + '\nprintf "scope=%s" "$PILOT_SPEC"',
                                    FLOWCTL="flowctl", PILOT_SPEC="wor-17-x", OUTPUT=json.dumps(output), RC=str(rc))
                self.assertIn(expected, result.stdout)
                if rc or "tasks" not in output:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn("scope=", result.stdout)
                else:
                    self.assertEqual(result.returncode, 0, result.stderr)

    def test_review_resolution_uses_spec_without_forwarding_default(self):
        code = fence("flow-next-flow/auto.md", 'REVIEW_ARG=""')
        stub = 'flowctl() { [ "$1" = review-backend ] && [ "$2" = wor-17-x ] || return 2; printf "%s" "$BACKEND"; }\n'
        for explicit, backend, expected in (("", "ASK", "0|"), ("", "codex", "1|"),
                                             ("rp", "ASK", "1|--review=rp")):
            with self.subTest(explicit=explicit, backend=backend):
                result = self.shell(stub + code + '\nprintf "%s|%s" "$REVIEW_CONFIGURED" "$REVIEW_ARG"',
                                    FLOWCTL="flowctl", SELECTED_SPEC="wor-17-x", PILOT_REVIEW=explicit, BACKEND=backend)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, expected)
                self.assertNotIn("--review=ASK", result.stdout)

    def test_triage_only_runs_on_successful_fanout_route(self):
        code = fence("flow-next-impl-review/SKILL.md", 'if [[ -z "${TRIAGE_DISABLED:-}"')
        with tempfile.TemporaryDirectory() as tmp:
            receipt = Path(tmp) / "receipt.json"
            before = '{"verdict":"NEEDS_WORK"}'
            stub = '''flowctl() {
  if [ "$1" = review-route ]; then
    printf '{"action":"%s","task_id":"fn-1.1","receipt_path":"%s"}' "$ACTION" "$RECEIPT"
    return "$PROBE_RC"
  fi
  if [ "$1" = triage-skip ]; then
    printf '{"verdict":"SHIP"}' > "$RECEIPT"
    printf '{"reason":"docs only"}'
  fi
}
'''
            for action, rc, skipped in (("fanout", "0", True), ("resume", "0", False),
                                         ("fanout", "2", False), ("", "0", False)):
                with self.subTest(action=action, rc=rc):
                    receipt.write_text(before, encoding="utf-8")
                    result = self.shell(stub + code + '\nprintf FULL_REVIEW', FLOWCTL="flowctl",
                                        TASK_ID="fn-1.1", BASE_COMMIT="", ACTION=action, PROBE_RC=rc,
                                        RECEIPT=str(receipt), TRIAGE_DISABLED="", FLOW_RALPH_NO_TRIAGE="")
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual("VERDICT=SHIP" in result.stdout, skipped)
                    self.assertEqual("FULL_REVIEW" in result.stdout, not skipped)
                    if not skipped:
                        self.assertEqual(receipt.read_text(encoding="utf-8"), before)

    def test_each_dispatch_fence_has_independent_allowlist(self):
        text = (SKILLS / "flow-next-flow/auto.md").read_text(encoding="utf-8")
        blocks = [block for block in re.findall(r"```bash\n(.*?)```", text, re.S)
                  if "DISPATCH_TARGET=" in block]
        self.assertGreaterEqual(len(blocks), 6)
        for block in blocks:
            with self.subTest(target=block.split("DISPATCH_TARGET=", 1)[1].splitlines()[0]):
                start = block.index('case "$DISPATCH_TARGET" in')
                guard = block[start:block.index("esac", start) + len("esac")]
                # Each check executes in a new shell with no previous definitions.
                for target, allowed in (("/flow-next:work", True), ("/flow-next:release", False)):
                    result = self.shell(guard, DISPATCH_TARGET=target)
                    self.assertEqual(result.returncode == 0, allowed, result.stderr)

    def test_standalone_rp_tally_runs_with_posix_awk_and_suffix_ids(self):
        text = (SKILLS / "flow-next-impl-review/workflow-rp.md").read_text(encoding="utf-8")
        start = text.index('  EXTRA_FIELDS=""', text.index("## Phase 4:"))
        code = text[start:text.index('  RECEIPT_INPUT=', start)]
        awk = shutil.which("mawk") or shutil.which("original-awk") or shutil.which("awk")
        if not awk:
            self.skipTest("portable awk unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            # Route every awk in the real fence through the selected implementation.
            (directory / "awk").symlink_to(awk)
            response = directory / "response.md"
            response.write_text("Suppressed findings: 3 at anchor 50, 7 at anchor 25.\n"
                                "Classification counts: 2 introduced, 4 pre_existing.\n"
                                "Unaddressed R-IDs: [R4a, R9, R4a]\n", encoding="utf-8")
            for task in ("", "fn-1.1"):
                with self.subTest(task=task):
                    result = self.shell(code + '\nprintf \'{"mode":"rp"%s}\' "$EXTRA_FIELDS"',
                                        RESPONSE_FILE=str(response), TASK_ID=task, VERDICT="NEEDS_WORK",
                                        PATH=str(directory) + os.pathsep + os.environ["PATH"])
                    self.assertEqual(result.returncode, 0, result.stderr)
                    data = json.loads(result.stdout)
                    if task:
                        self.assertEqual(data, {"mode": "rp"})
                    else:
                        self.assertEqual(data["suppressed_count"], {"50": 3, "25": 7})
                        self.assertEqual(data["unaddressed"], ["R4a", "R9"])
                        self.assertEqual(data["introduced_count"], 2)
                        self.assertEqual(data["pre_existing_count"], 4)


if __name__ == "__main__":
    unittest.main()
