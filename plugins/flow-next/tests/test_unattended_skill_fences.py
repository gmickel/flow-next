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
        code = fence("flow-next-flow/auto.md", 'SNAPSHOT_ARGS=()')
        for output, rc, expected in (
            ({"selected": {"id": "wor-17-x"}}, 0, "scope=wor-17-x"),
            ({"error": "Spec missing does not exist"}, 2, "PILOT_VERDICT=NEEDS_HUMAN"),
            ({"error": "Expected spec id"}, 2, "PILOT_VERDICT=NEEDS_HUMAN"),
        ):
            with self.subTest(output=output):
                stub = 'flowctl() { printf "config warning\\n" >&2; printf "%s" "$OUTPUT"; return "$RC"; }\n'
                result = self.shell(stub + code + '\nprintf "scope=%s" "$PILOT_SPEC"',
                                    FLOWCTL="flowctl", PILOT_SPEC="wor-17-x", OUTPUT=json.dumps(output), RC=str(rc))
                self.assertIn(expected, result.stdout)
                if rc:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn("scope=", result.stdout)
                else:
                    self.assertEqual(result.returncode, 0, result.stderr)

    def test_review_resolution_uses_spec_without_forwarding_default(self):
        code = fence("flow-next-flow/auto.md", 'REVIEW_ARG=""')
        stub = 'flowctl() { [ "$1" = review-backend ] && [ "$2" = wor-17-x ] || return 2; printf "%s" "$BACKEND"; }\n'
        for explicit, backend, expected in (("", "ASK", "0|"), ("", "codex", "1|"),
                                             ("copilot", "ASK", "1|--review=copilot")):
            with self.subTest(explicit=explicit, backend=backend):
                result = self.shell(stub + code + '\nprintf "%s|%s" "$REVIEW_CONFIGURED" "$REVIEW_ARG"',
                                    FLOWCTL="flowctl", SELECTED_SPEC="wor-17-x", PILOT_REVIEW=explicit, BACKEND=backend,
                                    PILOT_SNAPSHOT=json.dumps({"review_backend": {"spec": "none"},
                                        "candidates": [{"id": "wor-17-x", "review_backend": {"spec": backend}}]}))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, expected)
                self.assertNotIn("--review=ASK", result.stdout)

    def test_cli_step_triages_only_a_fanout_route(self):
        """impl-review SKILL.md step 2: route first, triage only on fanout."""
        code = fence("flow-next-impl-review/SKILL.md", "triage-skip")
        code = code.replace('REVIEW_ID="<literal or empty>"', 'REVIEW_ID="fn-1.1"')
        code = code.replace('DIFF_BASE="<literal>"', 'DIFF_BASE="abc123"')
        code = code.replace('BACKEND="<literal>"', 'BACKEND="codex"')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            stub = root / "scripts" / "flowctl"
            stub.write_text(
                "#!/usr/bin/env bash\n"
                'case "$1" in\n'
                "  review-route)\n"
                "    printf '{\"action\":\"%s\",\"task_id\":\"fn-1.1\",\"receipt_path\":\"%s\",\"message\":\"stopped\"}' \"$ACTION\" \"$RECEIPT\"\n"
                '    exit "$PROBE_RC" ;;\n'
                "  triage-skip)\n"
                '    [ "$TRIAGE_RC" = 0 ] || exit 1\n'
                "    printf '{\"verdict\":\"SHIP\"}' > \"$RECEIPT\"\n"
                "    printf '{\"reason\":\"docs only\"}' ;;\n"
                "  codex) echo FULL_REVIEW ;;\n"
                "esac\n",
                encoding="utf-8",
            )
            stub.chmod(0o755)
            receipt = root / "receipt.json"
            before = '{"verdict":"NEEDS_WORK"}'
            # (action, route rc, triage rc) -> (exit ok, skipped, full review)
            for action, route_rc, triage_rc, ok, skipped, full in (
                ("fanout", "0", "0", True, True, False),
                ("fanout", "0", "1", True, False, True),
                ("fix-then-rereview", "0", "0", True, False, False),
                ("stop", "0", "0", False, False, False),
                ("fanout", "2", "0", False, False, False),
            ):
                with self.subTest(action=action, route_rc=route_rc, triage_rc=triage_rc):
                    receipt.write_text(before, encoding="utf-8")
                    result = self.shell(code, DROID_PLUGIN_ROOT=str(root), ACTION=action,
                                        PROBE_RC=route_rc, TRIAGE_RC=triage_rc, RECEIPT=str(receipt))
                    self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
                    self.assertEqual("VERDICT=SHIP" in result.stdout, skipped)
                    self.assertEqual("FULL_REVIEW" in result.stdout, full)
                    if not skipped:
                        self.assertEqual(receipt.read_text(encoding="utf-8"), before)

    def test_other_paths_triage_only_runs_on_successful_fanout_route(self):
        code = fence("flow-next-impl-review/other-paths.md", 'if [[ -z "${TRIAGE_DISABLED:-}"')
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
                                        RECEIPT=str(receipt), TRIAGE_DISABLED="")
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual("VERDICT=SHIP" in result.stdout, skipped)
                    self.assertEqual("FULL_REVIEW" in result.stdout, not skipped)
                    if not skipped:
                        self.assertEqual(receipt.read_text(encoding="utf-8"), before)

    def test_stage_dispatch_fence_refuses_unlisted_stages_on_its_own(self):
        code = fence("flow-next-flow/auto.md", 'DISPATCH_TARGET="/flow-next:$STAGE"')
        # The fence runs in a fresh shell with no earlier definitions, as a tool call does.
        for stage, land, allowed in (("work", "0", True), ("make-pr", "0", True),
                                     ("release", "0", False), ("land", "0", False),
                                     ("land", "1", True)):
            with self.subTest(stage=stage, land=land):
                result = self.shell(code, PILOT_AUTONOMY="backlog", STAGE=stage,
                                    LAND_AUTHORIZED=land, LAND_SCOPE_SPEC="fn-1",
                                    LAND_SCOPE_PR="7")
                self.assertEqual(result.returncode == 0, allowed, result.stdout + result.stderr)
                if not allowed:
                    self.assertIn("PILOT_VERDICT=NEEDS_HUMAN", result.stdout)


if __name__ == "__main__":
    unittest.main()
