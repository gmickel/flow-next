"""Structured host-trace/eval harness for prompt-first chart skill (fn-135.4 / R47).

Loads fixtures under fixtures/chart_prompt_scenarios/*.json. Each fixture is a
host-trace scenario: user prompt, expected inferred operation(s), read-back
points, guarded flowctl chart mutations, and the exact terminal CHART_VERDICT
line where applicable.

The harness does not run an LLM. It validates fixture schema and cross-checks
expectations against the skill prose contracts (same technique as
test_prime_eval.py: expectations are data; the oracle asserts contracts, never
live judgment). Static prose tests in test_chart_skill_contract.py remain useful
but are not evidence for prompt interpretation coverage.

Run:
    cd plugins/flow-next/tests && python3 -m unittest test_chart_prompt_scenarios -q
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parent
REPO_ROOT = PLUGIN.parent.parent
FIXTURES_DIR = HERE / "fixtures" / "chart_prompt_scenarios"
SKILL_DIR = PLUGIN / "skills" / "flow-next-chart"
GUIDE_SKILL_MD = PLUGIN / "skills" / "flow-next-guide" / "SKILL.md"

SKILL_MD = SKILL_DIR / "SKILL.md"
WORKFLOW_MD = SKILL_DIR / "workflow.md"
EXAMPLES_MD = SKILL_DIR / "references" / "examples.md"

# Required top-level keys on every scenario fixture.
REQUIRED_TOP = (
    "id",
    "family",
    "description",
    "user_prompt",
    "context",
    "expected",
    "skill_contract_tokens",
)

REQUIRED_CONTEXT = ("mode_hint", "driver", "chart_id", "decision_pin")

REQUIRED_EXPECTED = (
    "mode",
    "inferred_operations",
    "read_backs",
    "guarded_mutations",
    "notes",
)

REQUIRED_MUTATIONS = ("allowed", "forbidden")

# Exact grammar from SKILL.md (R15). Placeholders <id>/<D> allowed.
VERDICT_RE = re.compile(
    r"^CHART_VERDICT=(RESOLVED|BLOCKED|NEEDS_HUMAN|COMPLETE|NO_WORK) "
    r"chart=(?P<chart>\S+) "
    r"decision=(?P<decision>\S+) "
    r'reason="[^"]+"$'
)

# Families the task/spec require (R47 + task.4 acceptance). One or more
# fixtures may cover a family.
REQUIRED_FAMILIES = frozenset(
    {
        "bounded_grounding",
        "skip_chart",
        "conflicting_stale_evidence",
        "known_background_fact",
        "ambiguous_steering",
        "prototype_lifecycle",
        "reversal_supersession",
        "attended_gating",
        "adaptive_frontier_growth",
        "tracker_parent_url",
        "tracker_decision_url",
        "tracker_unknown_url",
        "stale_claim_recovery",
        "over_ceiling",
        "unattended_fanout",
    }
)

# flowctl chart surface tokens that may appear in guarded mutation lists.
# Non-flowctl conceptual forbids (e.g. batch_claim) are allowed as free strings.
KNOWN_FLOWCTL_CHART_OPS = frozenset(
    {
        "chart create",
        "chart create --initial-map-file",
        "chart create --initial-map-file --force-size --reason",
        "chart claim",
        "chart release-claim",
        "chart release-claim --break-stale --reason",
        "chart resolve",
        "chart resolve --answer-file",
        "chart resolve --supersedes",
        "chart resolve --answer-file --sharpen-file",
        "chart resolve --sharpen-file",
        "chart attach-asset",
        "chart attach-asset --asset-file",
        "chart frontier",
        "chart show",
        "chart locate",
        "chart briefing",
        "chart briefing --proposal-file",
        "chart out-of-scope",
        "chart park-question",
        "chart wire-decision",
        "chart abandon",
        "chart reopen",
    }
)

EM_OR_EN_DASH = re.compile("[\u2012\u2013\u2014\u2015]")

VALID_DRIVERS = frozenset({"attended", "unattended"})
VALID_MODES = frozenset(
    {
        "chart",
        "work",
        "status",
        "re-enter",
        "status_or_work_disambiguate",
        "ambiguous",
        "guide",
    }
)


def _load_fixtures() -> list[tuple[Path, dict[str, Any]]]:
    if not FIXTURES_DIR.is_dir():
        return []
    out: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(FIXTURES_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        out.append((path, data))
    return out


def _skill_prose() -> str:
    return "\n".join(
        (
            SKILL_MD.read_text(encoding="utf-8"),
            WORKFLOW_MD.read_text(encoding="utf-8"),
            EXAMPLES_MD.read_text(encoding="utf-8"),
        )
    )


def _guide_prose() -> str:
    if not GUIDE_SKILL_MD.is_file():
        return ""
    return GUIDE_SKILL_MD.read_text(encoding="utf-8")


def _is_flowctl_like(token: str) -> bool:
    t = token.strip().lower()
    return t.startswith(("chart ", "flowctl chart"))


class ChartPromptFixturesExist(unittest.TestCase):
    def test_fixtures_dir_and_skill_files(self) -> None:
        self.assertTrue(FIXTURES_DIR.is_dir(), f"missing {FIXTURES_DIR}")
        for path in (SKILL_MD, WORKFLOW_MD, EXAMPLES_MD):
            self.assertTrue(path.is_file(), f"missing {path}")
        fixtures = list(FIXTURES_DIR.glob("*.json"))
        self.assertGreaterEqual(
            len(fixtures),
            len(REQUIRED_FAMILIES),
            "expected at least one fixture per required family",
        )


class ChartPromptFixtureSchema(unittest.TestCase):
    """Every fixture matches the pinned host-trace schema."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.fixtures = _load_fixtures()
        cls.assertTrue(cls.fixtures, "no chart_prompt_scenarios fixtures loaded")

    def test_required_top_level_keys_and_types(self) -> None:
        for path, data in self.fixtures:
            with self.subTest(fixture=path.name):
                self.assertIsInstance(data, dict)
                for key in REQUIRED_TOP:
                    self.assertIn(key, data, f"{path.name}: missing {key}")
                self.assertIsInstance(data["id"], str)
                self.assertTrue(data["id"].strip())
                self.assertIsInstance(data["family"], str)
                self.assertIsInstance(data["description"], str)
                self.assertIsInstance(data["user_prompt"], str)
                self.assertTrue(data["user_prompt"].strip())
                self.assertIsInstance(data["context"], dict)
                self.assertIsInstance(data["expected"], dict)
                self.assertIsInstance(data["skill_contract_tokens"], list)
                self.assertTrue(
                    data["skill_contract_tokens"],
                    f"{path.name}: skill_contract_tokens must be non-empty",
                )
                for tok in data["skill_contract_tokens"]:
                    self.assertIsInstance(tok, str)
                    self.assertTrue(tok.strip(), f"{path.name}: empty token")

    def test_context_shape(self) -> None:
        for path, data in self.fixtures:
            ctx = data["context"]
            with self.subTest(fixture=path.name):
                for key in REQUIRED_CONTEXT:
                    self.assertIn(key, ctx, f"{path.name}: context missing {key}")
                self.assertIn(ctx["driver"], VALID_DRIVERS, path.name)
                # mode_hint is free-form routing signal; non-empty string
                self.assertIsInstance(ctx["mode_hint"], str)
                self.assertTrue(ctx["mode_hint"].strip())
                # chart_id / decision_pin may be null
                if ctx["chart_id"] is not None:
                    self.assertIsInstance(ctx["chart_id"], str)
                if ctx["decision_pin"] is not None:
                    self.assertIsInstance(ctx["decision_pin"], str)
                self.assertIn("repo_evidence", ctx)
                self.assertIsInstance(ctx["repo_evidence"], list)
                self.assertIn("prior_state", ctx)
                self.assertIsInstance(ctx["prior_state"], dict)

    def test_expected_shape(self) -> None:
        for path, data in self.fixtures:
            exp = data["expected"]
            with self.subTest(fixture=path.name):
                for key in REQUIRED_EXPECTED:
                    self.assertIn(key, exp, f"{path.name}: expected missing {key}")
                self.assertIn(exp["mode"], VALID_MODES, path.name)
                self.assertIsInstance(exp["inferred_operations"], list)
                self.assertTrue(
                    exp["inferred_operations"],
                    f"{path.name}: inferred_operations empty",
                )
                for op in exp["inferred_operations"]:
                    self.assertIsInstance(op, str)
                    self.assertTrue(op.strip())
                self.assertIsInstance(exp["read_backs"], list)
                self.assertTrue(exp["read_backs"], f"{path.name}: read_backs empty")
                mut = exp["guarded_mutations"]
                self.assertIsInstance(mut, dict)
                for key in REQUIRED_MUTATIONS:
                    self.assertIn(key, mut, f"{path.name}: mutations missing {key}")
                    self.assertIsInstance(mut[key], list)
                # allowed/forbidden are lists of strings
                for side in ("allowed", "forbidden"):
                    for item in mut[side]:
                        self.assertIsInstance(item, str, f"{path.name} {side}")
                        self.assertTrue(item.strip())
                self.assertIsInstance(exp["notes"], list)
                # verdict may be null when the scenario stops at a blocking ask
                if "verdict" in exp and exp["verdict"] is not None:
                    self.assertIsInstance(exp["verdict"], str)

    def test_unique_ids(self) -> None:
        ids = [data["id"] for _, data in self.fixtures]
        self.assertEqual(len(ids), len(set(ids)), f"duplicate fixture ids: {ids}")

    def test_no_em_dashes_in_fixtures(self) -> None:
        for path, data in self.fixtures:
            blob = json.dumps(data, ensure_ascii=False)
            with self.subTest(fixture=path.name):
                m = EM_OR_EN_DASH.search(blob)
                if m is not None:
                    self.fail(
                        f"{path.name}: em/en dash U+{ord(m.group(0)):04X}; "
                        "use plain hyphens only"
                    )


class ChartPromptVerdictGrammar(unittest.TestCase):
    """Exact terminal CHART_VERDICT lines match the skill grammar when set."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.fixtures = _load_fixtures()

    def _check_verdict(self, label: str, verdict: str) -> None:
        self.assertTrue(
            VERDICT_RE.match(verdict),
            f"{label}: verdict does not match grammar: {verdict!r}",
        )
        self.assertTrue(
            verdict.startswith("CHART_VERDICT="),
            f"{label}: must start with CHART_VERDICT=",
        )

    def test_primary_verdicts(self) -> None:
        for path, data in self.fixtures:
            exp = data["expected"]
            if exp.get("verdict") is None:
                continue
            with self.subTest(fixture=path.name):
                self._check_verdict(path.name, exp["verdict"])

    def test_optional_alt_verdicts(self) -> None:
        for path, data in self.fixtures:
            exp = data["expected"]
            with self.subTest(fixture=path.name):
                if "verdict_without_consent" in exp:
                    self._check_verdict(
                        f"{path.name}/without_consent",
                        exp["verdict_without_consent"],
                    )
                if isinstance(exp.get("verdict_after_disambiguation"), dict):
                    status = exp["verdict_after_disambiguation"].get("status")
                    if status:
                        self._check_verdict(f"{path.name}/status", status)


class ChartPromptGuardedMutations(unittest.TestCase):
    """Guarded mutation lists are consistent and reference known chart ops."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.fixtures = _load_fixtures()
        cls.prose = _skill_prose()

    def test_allowed_not_in_forbidden(self) -> None:
        for path, data in self.fixtures:
            mut = data["expected"]["guarded_mutations"]
            allowed = set(mut["allowed"])
            forbidden = set(mut["forbidden"])
            with self.subTest(fixture=path.name):
                overlap = allowed & forbidden
                self.assertFalse(
                    overlap,
                    f"{path.name}: allowed∩forbidden={sorted(overlap)}",
                )

    def test_flowctl_like_allowed_ops_are_known_or_documented(self) -> None:
        prose_lower = self.prose.lower()
        for path, data in self.fixtures:
            mut = data["expected"]["guarded_mutations"]
            with self.subTest(fixture=path.name):
                for op in mut["allowed"]:
                    if not _is_flowctl_like(op):
                        continue
                    # Normalize "flowctl chart X" -> "chart X"
                    norm = re.sub(r"^flowctl\s+", "", op.strip(), flags=re.I)
                    if norm in KNOWN_FLOWCTL_CHART_OPS:
                        continue
                    # Prefix match against known ops (e.g. flags subset)
                    if any(
                        norm == k or norm.startswith(k + " ") or k.startswith(norm)
                        for k in KNOWN_FLOWCTL_CHART_OPS
                    ):
                        continue
                    # Still require the base subcommand to appear in skill prose
                    base = " ".join(norm.split()[:2])  # "chart create"
                    self.assertIn(
                        base,
                        prose_lower,
                        f"{path.name}: allowed op {op!r} not in skill prose "
                        f"or known surface",
                    )

    def test_no_mutation_scenarios_have_empty_allowed_or_read_only(self) -> None:
        """Skip-chart and unknown-URL: create/resolve must be forbidden."""
        hard_no_create = {
            "skip-chart-no-consequential-unknowns",
            "tracker-unknown-url-no-mutation",
        }
        for path, data in self.fixtures:
            if data["id"] not in hard_no_create:
                continue
            mut = data["expected"]["guarded_mutations"]
            with self.subTest(fixture=path.name):
                joined_forbidden = " ".join(mut["forbidden"]).lower()
                self.assertTrue(
                    "create" in joined_forbidden or not mut["allowed"],
                    f"{data['id']}: must forbid create or allow nothing",
                )
                for op in mut["allowed"]:
                    self.assertNotRegex(
                        op.lower(),
                        r"create|resolve|claim",
                        f"{data['id']}: unexpected mutating allowed op {op!r}",
                    )


class ChartPromptSkillContractCrossCheck(unittest.TestCase):
    """Each fixture's skill_contract_tokens must appear in skill prose.

    Mirrors test_prime_eval's oracle style: fixture rows are data; the test
    asserts the contracts those rows depend on still exist in the skill.
    Guide-routing fixtures (family guide_routing) check the guide skill;
    all other families check the chart skill.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.fixtures = _load_fixtures()
        cls.prose = _skill_prose()
        cls.prose_cf = cls.prose  # case-sensitive primary
        cls.prose_lower = cls.prose.lower()
        cls.guide_prose = _guide_prose()
        cls.guide_lower = cls.guide_prose.lower()

    def test_contract_tokens_present_in_skill_prose(self) -> None:
        for path, data in self.fixtures:
            with self.subTest(fixture=path.name):
                if data.get("family") == "guide_routing":
                    prose_cf = self.guide_prose
                    prose_lower = self.guide_lower
                    label = "guide skill"
                else:
                    prose_cf = self.prose_cf
                    prose_lower = self.prose_lower
                    label = "chart skill"
                missing: list[str] = []
                for tok in data["skill_contract_tokens"]:
                    if tok in prose_cf:
                        continue
                    # Case-insensitive fallback for short prose tokens
                    if tok.lower() in prose_lower:
                        continue
                    missing.append(tok)
                self.assertEqual(
                    missing,
                    [],
                    f"{path.name}: skill_contract_tokens missing from {label}: "
                    f"{missing}",
                )

    def test_verdict_token_when_set_is_documented(self) -> None:
        """Primary verdict kind must appear in the skill verdict table."""
        for path, data in self.fixtures:
            verdict = data["expected"].get("verdict")
            if not verdict:
                continue
            m = VERDICT_RE.match(verdict)
            self.assertIsNotNone(m, path.name)
            kind = verdict.split("=", 1)[1].split()[0]
            with self.subTest(fixture=path.name, kind=kind):
                self.assertIn(kind, self.prose)

    def test_attended_gate_fixture_forbids_resolve(self) -> None:
        for path, data in self.fixtures:
            if data["family"] != "attended_gating":
                continue
            mut = data["expected"]["guarded_mutations"]
            with self.subTest(fixture=path.name):
                self.assertEqual(data["context"]["driver"], "unattended")
                forbidden_join = " ".join(mut["forbidden"]).lower()
                self.assertIn("resolve", forbidden_join)
                self.assertIn("NEEDS_HUMAN", data["expected"]["verdict"])
                self.assertIn("no answer", data["expected"]["verdict"].lower())

    def test_prototype_fixtures_require_attach_and_reaction(self) -> None:
        for path, data in self.fixtures:
            if data["family"] != "prototype_lifecycle":
                continue
            ops = " ".join(data["expected"]["inferred_operations"]).lower()
            mut_allowed = " ".join(data["expected"]["guarded_mutations"]["allowed"]).lower()
            with self.subTest(fixture=path.name):
                self.assertTrue(
                    "attach" in ops or "attach" in mut_allowed,
                    f"{path.name}: prototype must involve attach-asset",
                )
                rb = " ".join(data["expected"]["read_backs"]).lower()
                self.assertTrue(
                    "reaction" in rb or "artefact" in rb or "asset" in rb,
                    f"{path.name}: prototype read-backs must mention reaction/asset",
                )

    def test_over_ceiling_documents_refuse_and_force(self) -> None:
        for path, data in self.fixtures:
            if data["family"] != "over_ceiling":
                continue
            ops = " ".join(data["expected"]["inferred_operations"]).lower()
            with self.subTest(fixture=path.name):
                self.assertIn("refuse", ops)
                self.assertIn("force-size", ops)
                self.assertIn(
                    "verdict_without_consent",
                    data["expected"],
                    "over-ceiling must pin the refuse-without-consent verdict",
                )

    def test_fanout_forbids_batch(self) -> None:
        for path, data in self.fixtures:
            if data["family"] != "unattended_fanout":
                continue
            forbidden = " ".join(data["expected"]["guarded_mutations"]["forbidden"]).lower()
            with self.subTest(fixture=path.name):
                self.assertTrue(
                    "batch" in forbidden or "mixed" in forbidden,
                    f"{path.name}: fan-out must forbid batch/mixed results",
                )
                follow = data["expected"].get("follow_on_expectations")
                self.assertIsInstance(follow, dict)
                self.assertIn("per_invocation", follow)


class ChartPromptCoverageInventory(unittest.TestCase):
    """Required scenario families from task.4 / R47 are all present."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.fixtures = _load_fixtures()
        cls.families = {data["family"] for _, data in cls.fixtures}

    def test_all_required_families_covered(self) -> None:
        missing = sorted(REQUIRED_FAMILIES - self.families)
        extra_note = sorted(self.families - REQUIRED_FAMILIES)
        self.assertEqual(
            missing,
            [],
            f"missing required scenario families: {missing}; "
            f"present extras: {extra_note}",
        )

    def test_each_family_has_user_prompt_and_ops(self) -> None:
        by_family: dict[str, list[dict[str, Any]]] = {}
        for _, data in self.fixtures:
            by_family.setdefault(data["family"], []).append(data)
        for fam in sorted(REQUIRED_FAMILIES):
            with self.subTest(family=fam):
                rows = by_family.get(fam, [])
                self.assertTrue(rows, f"no fixtures for family {fam}")
                for row in rows:
                    self.assertTrue(row["user_prompt"].strip())
                    self.assertTrue(row["expected"]["inferred_operations"])
                    self.assertTrue(row["expected"]["read_backs"])


class ChartPromptExamplesAlignment(unittest.TestCase):
    """Where fixtures pin exact example verdicts, examples.md must agree."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.examples = EXAMPLES_MD.read_text(encoding="utf-8")
        cls.fixtures = {data["id"]: data for _, data in _load_fixtures()}

    def test_skip_chart_verdict_in_examples(self) -> None:
        row = self.fixtures["skip-chart-no-consequential-unknowns"]
        self.assertIn(row["expected"]["verdict"], self.examples)

    def test_needs_human_reason_documented(self) -> None:
        row = self.fixtures["attended-unattended-driver-needs-human"]
        # Grammar kind + no-answer contract appear in examples/skill
        self.assertIn("NEEDS_HUMAN", self.examples)
        self.assertIn("no answer", self.examples.lower())
        self.assertIn("NEEDS_HUMAN", row["expected"]["verdict"])

    def test_locate_failure_verdict_in_examples(self) -> None:
        row = self.fixtures["tracker-unknown-url-no-mutation"]
        self.assertIn(row["expected"]["verdict"], self.examples)

    def test_force_size_verdicts_in_examples(self) -> None:
        row = self.fixtures["over-ceiling-refuse-then-force-size"]
        self.assertIn(row["expected"]["verdict"], self.examples)
        self.assertIn(row["expected"]["verdict_without_consent"], self.examples)

    def test_chart_created_verdict_in_examples(self) -> None:
        row = self.fixtures["independent-unattended-fanout-separate-invocations"]
        self.assertIn(row["expected"]["verdict"], self.examples)


if __name__ == "__main__":
    unittest.main()
