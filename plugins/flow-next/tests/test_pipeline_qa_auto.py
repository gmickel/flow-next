"""`pipeline.qa` is the enum `off | on | auto`; the unattended driver reads all
three.

Contract pins only (G2): the smallest distinctive tokens plus one executable
run of the driver's QA-gate fence. The `auto` semantics themselves are
judgment in the flow skill's routing reference; nothing here asserts prose.

* the `flow --auto` QA gate (`skills/flow-next-flow/auto.md`, formerly
  pilot's) resolves two flags from the root snapshot: the literal `on` sets
  `QA_STAGE_ENABLED=1`, the literal `auto` sets `QA_STAGE_AUTO=1`, anything
  else leaves both 0 - proven by running the fence against each value;
* the setup ceremony's Live QA question names the three literal values and
  the ceremony recommends `/flow-next:features` once the stage is on or auto;
* the QA and prime skills route the `auto` rule to the flow skill's
  gate-selection reference, which exists.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent.parent
AUTO_MD = PLUGIN_DIR / "skills" / "flow-next-flow" / "auto.md"
SETUP_WORKFLOW = PLUGIN_DIR / "skills" / "flow-next-setup" / "workflow.md"
QA_SKILL = PLUGIN_DIR / "skills" / "flow-next-qa" / "SKILL.md"
PRIME_PILLARS = PLUGIN_DIR / "skills" / "flow-next-prime" / "pillars.md"
GATE_SELECTION = (
    PLUGIN_DIR / "skills" / "flow-next-flow" / "references" / "gate-selection.md"
)

QA_GATE_ON_TOKEN = '[ "${QA_GATE:-}" = "on" ] && QA_STAGE_ENABLED=1'
QA_GATE_AUTO_TOKEN = '[ "${QA_GATE:-}" = "auto" ] && QA_STAGE_AUTO=1'
SNAPSHOT_LINE = (
    'PILOT_CFG_SNAPSHOT="${TMPDIR:-/tmp}/flow-pilot-config-'
    "$(git rev-parse --show-toplevel 2>/dev/null | cksum | cut -d' ' -f1).json\""
)

_POSIX_BASH = unittest.skipIf(
    sys.platform == "win32"
    or shutil.which("bash") is None
    or shutil.which("jq") is None,
    "executable fence test needs a POSIX bash + jq",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _qa_gate_fence(workflow: str) -> str:
    start = workflow.find("QA_STAGE_ENABLED=0\n")
    assert start != -1, "flow --auto QA gate fence not found"
    end = workflow.find("```", start)
    return workflow[start:end]


class AutoQaGateReadsEveryValue(unittest.TestCase):
    def test_gate_tokens_present_and_fence_reads_auto(self) -> None:
        wf = _read(AUTO_MD)
        self.assertIn(QA_GATE_ON_TOKEN, wf)
        self.assertIn(QA_GATE_AUTO_TOKEN, wf)
        fence = _qa_gate_fence(wf)
        self.assertIn(QA_GATE_ON_TOKEN, fence)
        self.assertIn(QA_GATE_AUTO_TOKEN, fence)
        # Derived from the root snapshot, never a second config call.
        self.assertNotRegex(fence, r'\$FLOWCTL"?\s+config get')

    @_POSIX_BASH
    def test_fence_resolves_each_literal_to_its_flag(self) -> None:
        fence = _qa_gate_fence(_read(AUTO_MD))
        self.assertIn(SNAPSHOT_LINE, fence, "snapshot path line drifted")
        # value -> (QA_STAGE_ENABLED, QA_STAGE_AUTO)
        cases = (
            ("auto", "0", "1"),
            ("on", "1", "0"),
            ("off", "0", "0"),
            ("maybe", "0", "0"),
            (True, "0", "0"),
        )
        for value, enabled, auto in cases:
            with self.subTest(value=value), tempfile.TemporaryDirectory() as td:
                snap = Path(td) / "snap.json"
                snap.write_text(
                    json.dumps({"key": None, "value": {"pipeline": {"qa": value}}})
                )
                script = fence.replace(
                    SNAPSHOT_LINE, f'PILOT_CFG_SNAPSHOT="{snap}"'
                ) + '\nprintf "\\nENABLED=%s AUTO=%s" "$QA_STAGE_ENABLED" "$QA_STAGE_AUTO"'
                res = subprocess.run(
                    ["bash", "-c", script], capture_output=True, text=True
                )
                self.assertEqual(res.returncode, 0, f"{value}: {res.stderr}")
                self.assertTrue(
                    res.stdout.endswith(f"ENABLED={enabled} AUTO={auto}"),
                    f"{value}: {res.stdout!r}",
                )
                # `on` and `auto` both activate the freshness-probe sentinel;
                # every other value leaves the reference unread.
                self.assertEqual(
                    "GATE ACTIVE" in res.stdout, value in ("on", "auto"), res.stdout
                )


class SetupLiveQaQuestion(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = _read(SETUP_WORKFLOW)

    def _questions_block(self) -> str:
        start = self.text.index("### 6d: Build questions list")
        end = self.text.index("## Step 7: Process Answers")
        return self.text[start:end]

    def test_live_qa_question_names_three_literal_values(self) -> None:
        block = self._questions_block()
        self.assertIn('"header": "Live QA"', block)
        labels = re.findall(r'"label": "([^"]+)"', block)
        leading = {label.split(" ", 1)[0] for label in labels}
        self.assertTrue({"off", "on", "auto"} <= leading, labels)

    def test_answers_persist_each_literal_value(self) -> None:
        for value in ("off", "on", "auto"):
            self.assertIn(f"config set pipeline.qa {value} --json", self.text)

    def test_probe_and_features_recommendation(self) -> None:
        self.assertIn("config get pipeline.qa --raw --json", self.text)
        self.assertIn("SETUP_FIRST_RUN", self.text)
        self.assertIn("/flow-next:features", self.text)


class AutoRuleRoutesToGateSelection(unittest.TestCase):
    def test_reference_exists_and_names_the_enum(self) -> None:
        self.assertTrue(GATE_SELECTION.is_file())
        self.assertIn("`off | on | auto`", _read(GATE_SELECTION))

    def test_qa_skill_links_gate_selection_one_level_deep(self) -> None:
        self.assertIn(
            "../flow-next-flow/references/gate-selection.md", _read(QA_SKILL)
        )

    def test_prime_readiness_line_names_auto(self) -> None:
        self.assertIn("`pipeline.qa auto`", _read(PRIME_PILLARS))


if __name__ == "__main__":
    unittest.main()
