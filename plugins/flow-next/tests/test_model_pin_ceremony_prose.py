"""fn-115.2 — setup model-pin refresh ceremony prose contracts.

The ceremony is pure agent prose in the setup skill (flowctl only stores).
These pins lock the load-bearing contracts so a future edit cannot drop:

  * ceremony present in setup workflow (canonical + Codex mirror)
  * autonomous skip stated (same three markers fn-113 uses)
  * probe commands named (cursor-agent --list-models, copilot -p "/model",
    codex accept-probe)
  * models.verifiedAt stamp step present
  * models.roles write keys named
  * failure-feedback receipt scan mentioned
  * CLAUDE.md / routing-table offer present (not forced)

Run:
    python3 -m unittest plugins.flow-next.tests.test_model_pin_ceremony_prose -q
"""

from __future__ import annotations

import pathlib
import re
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN = REPO_ROOT / "plugins" / "flow-next"

CANONICAL_WORKFLOW = PLUGIN / "skills" / "flow-next-setup" / "workflow.md"
MIRROR_WORKFLOW = PLUGIN / "codex" / "skills" / "flow-next-setup" / "workflow.md"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


class ModelPinCeremonyProseContract(unittest.TestCase):
    """Ceremony prose pins on canonical setup workflow AND the Codex mirror."""

    def _assert_contract(self, path: pathlib.Path) -> None:
        self.assertTrue(path.is_file(), f"missing: {path}")
        text = _read(path)

        # Ceremony present (section header + fn tag).
        self.assertIn("Model-pin refresh ceremony", text, path)
        self.assertIn("fn-115.2", text, path)
        self.assertIn("6e:", text, path)

        # Fresh AND re-runs.
        self.assertRegex(
            text,
            re.compile(r"fresh setup\s+AND\s+re-runs", re.IGNORECASE),
            path,
        )

        # Autonomous skip stated SILENTLY; same three markers fn-113 uses.
        self.assertIn("skipped SILENTLY", text, path)
        self.assertIn("MODELS_ASK", text, path)
        self.assertIn("FLOW_RALPH", text, path)
        self.assertIn("REVIEW_RECEIPT_PATH", text, path)
        self.assertIn("FLOW_AUTONOMOUS", text, path)
        # The three-marker gate must actually short-circuit the ceremony.
        self.assertRegex(
            text,
            re.compile(
                r'FLOW_RALPH:-.*"1".*REVIEW_RECEIPT_PATH.*'
                r'FLOW_AUTONOMOUS:-.*"1"',
                re.DOTALL,
            ),
            path,
        )
        self.assertIn('MODELS_CEREMONY="skipped (autonomous)"', text, path)

        # Probe commands named (exact task/spec strings).
        self.assertIn("cursor-agent --list-models", text, path)
        self.assertIn('copilot -p "/model"', text, path)
        self.assertIn("codex accept-probe", text, path)

        # Skip a probe when its CLI is absent.
        self.assertRegex(
            text,
            re.compile(r"skip.*probe.*absent|absent.*skip.*probe", re.IGNORECASE),
            path,
        )

        # Roles + backends exact keys task .1 validates.
        for role in (
            "fastJudge",
            "review",
            "delegate",
            "scoutFast",
            "scoutIntelligent",
        ):
            self.assertIn(role, text, f"{path}: missing role {role}")
        self.assertIn("models.roles", text, path)
        self.assertIn("models.roles.<role>.<backend>", text, path)

        # verifiedAt stamp step present (config set + ISO date).
        self.assertIn("models.verifiedAt", text, path)
        self.assertRegex(
            text,
            re.compile(
                r'config set models\.verifiedAt',
            ),
            path,
        )
        self.assertIn("%Y-%m-%d", text, path)

        # Write path uses flowctl config set for role pins.
        self.assertRegex(
            text,
            re.compile(r"config set models\.roles\."),
            path,
        )

        # Failure-feedback: scan receipts for ladder activations.
        self.assertIn("review-receipts", text, path)
        self.assertRegex(
            text,
            re.compile(r"fallback-ladder|ladder activation", re.IGNORECASE),
            path,
        )
        # Receipt model field (actual run) vs pin.
        self.assertRegex(
            text,
            re.compile(r"\bmodel\b.*pin|pin.*\bmodel\b", re.IGNORECASE),
            path,
        )

        # Propose via blocking ask (canonical: AskUserQuestion; Codex mirror:
        # sync-codex rewrites to a plain-text numbered prompt).
        self.assertTrue(
            "AskUserQuestion" in text or "plain-text numbered prompt" in text,
            f"{path}: missing blocking ask primitive",
        )
        self.assertIn("Accept proposed map (Recommended)", text, path)
        self.assertIn("Stamp verifiedAt only", text, path)
        self.assertIn("current -> proposed", text, path)

        # Routing-table offer (not force).
        self.assertRegex(
            text,
            re.compile(r"Offer \(not force\)|offer.*routing table", re.IGNORECASE),
            path,
        )
        self.assertIn("model-routing", text, path)

        # Doctrine: agent probes/judges; flowctl only stores.
        self.assertRegex(
            text,
            re.compile(
                r"agent probes.*judges|probes, judges|probe.*judge.*propose",
                re.IGNORECASE,
            ),
            path,
        )
        self.assertRegex(
            text,
            re.compile(r"flowctl only stores", re.IGNORECASE),
            path,
        )

    def test_canonical_workflow(self) -> None:
        self._assert_contract(CANONICAL_WORKFLOW)

    def test_mirror_workflow(self) -> None:
        self._assert_contract(MIRROR_WORKFLOW)


if __name__ == "__main__":
    unittest.main()
