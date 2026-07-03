"""CI gate: `flowctl plan-sync-probe` vs the FROZEN gate-corpus answer key.

fn-83.2 (R2/R3/R4). The corpus lives in `optimization/plan-sync-gate/`
(scenarios.json + builders.py + answer-key.json — APPEND-ONLY, see its
README). The answer key was generated ONCE from the REAL production
`agents/plan-sync.md` (N=3 runs per scenario, majority vote, ANY flip ⇒
drift-positive, model id recorded) and is FROZEN — this check runs the
deterministic probe only; the LLM is NEVER re-run in CI.

Assertions:
  - HARD zero-false-skip merge gate: every key-DRIFT scenario probed with
    its TRUTHFUL deviation flag must `spawn`.
  - Adversarial arm: every drift-positive re-probed with deviation forced
    `no` must still `spawn` wherever the drift is path/token-visible; the
    two flag-dependent residual classes (`visibility: flag-only`,
    annotated `residual`) are asserted as the DOCUMENTED expected miss
    (`skip`) — never green-washed into a pass of the lattice.
  - Frozen behavior lock: each arm's decision must equal the recorded
    `probe_expected` — probe changes require a conscious re-baseline of
    scenarios.json + results.tsv, never a silent drift.
  - Metrics honesty: the skip-rate and rule-of-three rows committed in
    results.tsv must match what the probe actually does today.

Replay scenarios pin full 40-char SHAs from this repository's history;
`builders.ensure_commit_available` fetches them (origin, then the canonical
repo URL) when a shallow CI clone lacks them. A missing commit FAILS the
check — a silently shrunk corpus would weaken the gate.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[3]
HARNESS_DIR = REPO_ROOT / "optimization" / "plan-sync-gate"
RESULTS_TSV = HARNESS_DIR / "results.tsv"


def _load_builders():
    spec = importlib.util.spec_from_file_location(
        "plan_sync_gate_builders", HARNESS_DIR / "builders.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


builders = _load_builders()


class AnswerKeySchemaTest(unittest.TestCase):
    """The frozen key must stay complete and internally consistent."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.scenarios = builders.load_scenarios()
        cls.key = builders.load_answer_key()

    def test_key_is_frozen_with_model_recorded(self) -> None:
        self.assertTrue(self.key["frozen"])
        self.assertEqual(self.key["n_runs"], 3)
        self.assertTrue(self.key["model_id"].startswith("claude-"))
        self.assertIn("wobble", self.key["vote_rule"].lower())

    def test_every_scenario_has_a_key_entry(self) -> None:
        key_ids = set(self.key["scenarios"].keys())
        scenario_ids = {s["id"] for s in self.scenarios}
        self.assertEqual(scenario_ids, key_ids)

    def test_votes_wellformed_and_label_rule_applied(self) -> None:
        # ANY yes vote ⇒ drift (a flip across runs = wobble = ambiguity =
        # drift; unanimous yes is drift a fortiori).
        for sc_id, entry in self.key["scenarios"].items():
            with self.subTest(scenario=sc_id):
                votes = entry["votes"]
                self.assertEqual(len(votes), 3)
                self.assertTrue(all(v in ("yes", "no") for v in votes))
                expected_label = "drift" if "yes" in votes else "no_drift"
                self.assertEqual(entry["label"], expected_label)
                self.assertEqual(entry["wobble"], len(set(votes)) > 1)

    def test_corpus_minimums(self) -> None:
        # ≥10 constructed positives + ≥10 history replays (append-only floor).
        fixtures = [s for s in self.scenarios if s["kind"] == "fixture"]
        replays = [s for s in self.scenarios if s["kind"] == "replay"]
        self.assertGreaterEqual(len(fixtures), 10)
        self.assertGreaterEqual(len(replays), 10)

    def test_residual_annotations_present(self) -> None:
        # The two flag-dependent classes must stay annotated, never hidden.
        residual_ids = {s["id"] for s in self.scenarios if s.get("residual")}
        self.assertIn("pos-rename-plainword", residual_ids)
        self.assertIn("pos-deviation-only", residual_ids)
        for s in self.scenarios:
            if s.get("residual"):
                self.assertEqual(s["visibility"], "flag-only", s["id"])
                self.assertEqual(
                    s["probe_expected"].get("adversarial"), "skip", s["id"]
                )


class GateCorpusTest(unittest.TestCase):
    """Run the CURRENT probe against every scenario; compare to the key."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.scenarios = builders.load_scenarios()
        cls.key = builders.load_answer_key()["scenarios"]
        cls.decisions = {}  # (scenario_id, arm) -> decision
        cls._tmp = tempfile.TemporaryDirectory()
        workdir = Path(cls._tmp.name)
        try:
            for sc in cls.scenarios:
                mat = builders.materialize(sc, workdir / sc["id"])
                try:
                    arms = {"truthful": sc["truthful_deviation"]}
                    if sc["intent"] == "positive":
                        arms["adversarial"] = "no"
                    for arm, deviation in arms.items():
                        out = builders.run_probe(mat, deviation)
                        cls.decisions[(sc["id"], arm)] = out["decision"]
                finally:
                    builders.cleanup(sc, mat)
        except BaseException:
            cls._tmp.cleanup()
            raise

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_zero_false_skips_on_lattice_inputs(self) -> None:
        # THE hard merge gate: a key-DRIFT scenario probed with its truthful
        # deviation flag must spawn. Zero exceptions, residuals included
        # (their truthful flag is `yes`, which the lattice must honor).
        false_skips = []
        for sc in self.scenarios:
            if self.key[sc["id"]]["label"] != "drift":
                continue
            decision = self.decisions[(sc["id"], "truthful")]
            if decision != "spawn":
                false_skips.append(sc["id"])
        self.assertEqual(
            false_skips, [],
            "FALSE SKIP(S) against the frozen real-agent key — the gate is "
            "NOT shippable; do not weaken the corpus: %s" % false_skips,
        )

    def test_adversarial_flag_arm(self) -> None:
        # Deviation forced `no`: path/token-visible drift must still spawn.
        # Residual (flag-only) scenarios are asserted as the DOCUMENTED
        # expected miss — the probe skipping them is the stated residual,
        # not a pass. If a future probe closes them, this assert flips and
        # the annotation must be consciously retired.
        for sc in self.scenarios:
            if sc["intent"] != "positive":
                continue
            decision = self.decisions[(sc["id"], "adversarial")]
            with self.subTest(scenario=sc["id"], visibility=sc["visibility"]):
                if sc.get("residual"):
                    self.assertEqual(
                        decision, "skip",
                        "%s: residual class now behaves differently — "
                        "re-baseline the annotation" % sc["id"],
                    )
                else:
                    self.assertEqual(
                        decision, "spawn",
                        "%s: path/token-visible drift must survive an "
                        "untruthful PLAN_DEVIATION=no" % sc["id"],
                    )

    def test_frozen_probe_expectations(self) -> None:
        # Behavior lock: every recorded arm decision must match. A probe
        # change that alters ANY decision requires a conscious re-baseline
        # (scenarios.json + results.tsv + README), never silent drift.
        for sc in self.scenarios:
            for arm, expected in sc["probe_expected"].items():
                with self.subTest(scenario=sc["id"], arm=arm):
                    self.assertEqual(self.decisions[(sc["id"], arm)], expected)

    def test_metrics_rows_match_reality(self) -> None:
        # results.tsv honesty: the committed skip-rate / false-skip /
        # rule-of-three rows must be recomputable from today's probe.
        rows = {}
        for line in RESULTS_TSV.read_text(encoding="utf-8").splitlines():
            fields = line.split("\t")
            if len(fields) >= 3 and fields[0] == "metric":
                rows[fields[1]] = fields[2]

        drift_ids = [s["id"] for s in self.scenarios
                     if self.key[s["id"]]["label"] == "drift"]
        negative_ids = [s["id"] for s in self.scenarios
                        if self.key[s["id"]]["label"] == "no_drift"]
        false_skips = sum(
            1 for sc_id in drift_ids
            if self.decisions[(sc_id, "truthful")] != "spawn")
        skips = sum(
            1 for sc_id in negative_ids
            if self.decisions[(sc_id, "truthful")] == "skip")

        self.assertEqual(
            rows["false_skips"], "%d/%d" % (false_skips, len(drift_ids)))
        self.assertEqual(
            rows["skip_rate_on_negatives"],
            "%d/%d" % (skips, len(negative_ids)))
        # Rule of three: 0 FN in N ⇒ FN-rate ≤ 3/N at 95% confidence.
        self.assertEqual(
            rows["rule_of_three_bound"],
            "<=3/%d (~%.0f%%) @95%%" % (len(drift_ids),
                                        300.0 / len(drift_ids)))


if __name__ == "__main__":
    unittest.main()
