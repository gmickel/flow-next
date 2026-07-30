"""RP workflows keep CE direct review and Classic tab review isolated."""

from __future__ import annotations

import re
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "flow-next"
WORKFLOWS = (
    "flow-next-impl-review/workflow-rp.md",
    "flow-next-plan-review/workflow-rp.md",
    "flow-next-spec-completion-review/workflow-rp.md",
)


def bash_fences(text: str) -> list[str]:
    return re.findall(r"```bash\n(.*?)```", text, flags=re.DOTALL)


class RepoPromptSetupWorkflowContractTest(unittest.TestCase):
    def test_setup_fence_is_self_contained_and_requests_ce_review(self) -> None:
        for mirror_prefix in ("skills", "codex/skills"):
            for relative in WORKFLOWS:
                path = PLUGIN_ROOT / mirror_prefix / relative
                matching = [
                    fence for fence in bash_fences(path.read_text(encoding="utf-8"))
                    if "rp setup-review" in fence and "--response-type review" in fence
                ]
                self.assertEqual(len(matching), 1, path)
                fence = matching[0]
                assignment = fence.find('REVIEW_INSTRUCTIONS_FILE="')
                use = fence.find("--summary-file \"$REVIEW_INSTRUCTIONS_FILE\"")
                self.assertGreaterEqual(assignment, 0, path)
                self.assertGreater(use, assignment, path)
                for required in ("protected", "<verdict>"):
                    self.assertIn(required, fence.lower(), path)
                self.assertIn("--response-type review", fence, path)
                self.assertIn("--response-file \"$RESPONSE_FILE\"", fence, path)
                self.assertIn("> \"$SETUP_FILE\"", fence, path)
                self.assertIn("ROUND_EXIT=$?", fence, path)
                self.assertIn("SETUP_EXIT=$?", fence, path)
                self.assertIn("review-rounds record", fence, path)
                self.assertIn('source "$SETUP_FILE"', fence, path)
                self.assertIn("<verdict>", fence, path)

    def test_selection_and_initial_chat_are_classic_only(self) -> None:
        for mirror_prefix in ("skills", "codex/skills"):
            for relative in WORKFLOWS:
                path = PLUGIN_ROOT / mirror_prefix / relative
                fences = bash_fences(path.read_text(encoding="utf-8"))
                reached = [
                    fence
                    for fence in fences
                    if "rp select-get" in fence
                    or ("rp chat-send" in fence and "--new-chat" in fence)
                ]
                self.assertGreaterEqual(len(reached), 2, path)
                for fence in reached:
                    self.assertIn('RP_MODE" == "classic', fence, path)
                    self.assertIn('source "$SETUP_FILE"', fence, path)

    def test_ce_response_is_recorded_without_an_initial_chat_dispatch(self) -> None:
        for mirror_prefix in ("skills", "codex/skills"):
            for relative in WORKFLOWS:
                path = PLUGIN_ROOT / mirror_prefix / relative
                text = path.read_text(encoding="utf-8")
                self.assertIn('if [[ "$RP_MODE" == "classic" ]]; then', text, path)
                self.assertIn("RP_EXIT=0", text, path)
                self.assertIn("--response-file \"$RESPONSE_FILE\"", text, path)

    def test_ce_continuations_use_chat_identity_without_tab_state(self) -> None:
        for mirror_prefix in ("skills", "codex/skills"):
            for relative in WORKFLOWS:
                path = PLUGIN_ROOT / mirror_prefix / relative
                text = path.read_text(encoding="utf-8")
                self.assertIn('--chat-id "$CHAT_ID"', text, path)
                self.assertIn("--mode review", text, path)
                self.assertIn('RP_MODE" == "ce', text, path)

    def test_plan_setup_fence_stops_at_cap_and_finalizes_setup_failure(self) -> None:
        path = (
            PLUGIN_ROOT
            / "skills/flow-next-plan-review/workflow-rp.md"
        )
        fence = next(
            block for block in bash_fences(path.read_text(encoding="utf-8"))
            if "rp setup-review" in block and "--response-type review" in block
        ).replace("<spec-id>", "fn-1-demo").replace("<suffix>", "test")
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            log = temp / "calls.log"
            stub = temp / "flowctl"
            stub.write_text(
                "#!/usr/bin/env bash\n"
                "printf '%s\\n' \"$*\" >> \"$CALL_LOG\"\n"
                "if [[ \"$1 $2\" == \"review-rounds increment\" ]]; then\n"
                "  printf '%s\\n' '{\"round\":1,\"cap\":4}'\n"
                "  [[ \"${FAIL_CAP:-0}\" == 1 ]] && exit 4\n"
                "  exit 0\n"
                "elif [[ \"$1 $2\" == \"rp setup-review\" ]]; then\n"
                "  [[ \"${FAIL_SETUP:-0}\" == 1 ]] && exit 2\n"
                "  printf '%s\\n' 'RP_MODE=ce W=2 T=ctx CHAT_ID=chat'\n"
                "elif [[ \"$1 $2\" == \"review-rounds record\" ]]; then\n"
                "  printf '%s\\n' '{\"recorded\":true}'\n"
                "elif [[ \"$1\" == \"cat\" ]]; then\n"
                "  printf '%s\\n' '# Demo spec'\n"
                "fi\n",
                encoding="utf-8",
            )
            stub.chmod(0o755)
            prefix = (
                f"FLOWCTL={stub!s}\n"
                f"REPO_ROOT={temp!s}\n"
                "SPEC_ID=fn-1-demo\n"
                f"CALL_LOG={log!s}\n"
                "export CALL_LOG FAIL_CAP FAIL_SETUP\n"
            )
            capped = subprocess.run(
                ["bash", "-c", prefix + fence],
                env={"PATH": "/usr/bin:/bin", "FAIL_CAP": "1"},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(capped.returncode, 4, capped.stderr)
            self.assertNotIn("rp setup-review", log.read_text(encoding="utf-8"))

            log.write_text("", encoding="utf-8")
            failed = subprocess.run(
                ["bash", "-c", prefix + fence],
                env={"PATH": "/usr/bin:/bin", "FAIL_SETUP": "1"},
                text=True,
                capture_output=True,
                check=False,
            )
            calls = log.read_text(encoding="utf-8")
            self.assertEqual(
                failed.returncode,
                2,
                f"stdout={failed.stdout!r} stderr={failed.stderr!r} calls={calls!r}",
            )
            self.assertIn("rp setup-review", calls)
            self.assertIn("review-rounds record", calls)


if __name__ == "__main__":
    unittest.main()
