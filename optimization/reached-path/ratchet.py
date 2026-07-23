"""Zero-loss ratchet + subjective/borderline run-count policy (fn-130 R2).

Keep only when every accuracy/coverage/negative-control cell meets or exceeds
baseline AND at least one predeclared efficiency or quality measure improves.
A flat or noisy result is discard — never keep.
"""

from __future__ import annotations

from typing import Any, Optional

BORDERLINE_MIN_N = 2
SUBJECTIVE_MAJORITY_N = (3, 5)  # inclusive range; default mid = 3


def subjective_policy() -> dict[str, Any]:
    return {
        "borderline_paired_n_min": BORDERLINE_MIN_N,
        "subjective_majority_n": list(SUBJECTIVE_MAJORITY_N),
        "subjective_majority_default": 3,
        "flat_or_noisy": "discard",
        "sealed_holdout": "required_when_judgment_or_examples_can_overfit",
        "lineage": "B0 -> V1/B1 -> candidate (immutable; fail closed on hash mismatch)",
    }


def decide_ratchet(
    *,
    baseline_accuracy: dict[str, bool],
    candidate_accuracy: dict[str, bool],
    baseline_metrics: dict[str, float],
    candidate_metrics: dict[str, float],
    improved_keys: Optional[list[str]] = None,
    borderline: bool = False,
    subjective: bool = False,
    paired_runs: int = 1,
    majority_votes: Optional[list[bool]] = None,
    noisy: bool = False,
) -> dict[str, Any]:
    """Return a ratchet verdict record.

    ``improved_keys`` names metric fields that are allowed to count as the
    required efficiency/quality improvement (e.g. ``reached_path_chars`` lower
    is better; ``detection_rate`` higher is better). When omitted, any numeric
    metric that moves in a predeclared direction listed under
    ``baseline_metrics['__lower_better__']`` / ``__higher_better__`` counts.
    """
    if noisy:
        return _discard("noisy_result")

    # Accuracy: every shared cell must meet or exceed baseline (True >= True).
    for cell, base_ok in baseline_accuracy.items():
        cand = candidate_accuracy.get(cell)
        if cand is None:
            return _discard(f"missing_accuracy_cell:{cell}")
        if base_ok and not cand:
            return _discard(f"accuracy_regression:{cell}")

    lower_better = set(baseline_metrics.get("__lower_better__", []) or [])
    higher_better = set(baseline_metrics.get("__higher_better__", []) or [])
    if improved_keys is None:
        improved_keys = sorted(lower_better | higher_better)

    improved = False
    for key in improved_keys:
        if key.startswith("__"):
            continue
        if key not in baseline_metrics or key not in candidate_metrics:
            continue
        b = float(baseline_metrics[key])
        c = float(candidate_metrics[key])
        if key in lower_better and c < b:
            improved = True
        if key in higher_better and c > b:
            improved = True

    if not improved:
        return _discard("flat_no_predeclared_improvement")

    if borderline and paired_runs < BORDERLINE_MIN_N:
        return _discard(f"borderline_needs_paired_n>={BORDERLINE_MIN_N}")

    if subjective:
        votes = list(majority_votes or [])
        n = len(votes)
        lo, hi = SUBJECTIVE_MAJORITY_N
        if n < lo or n > hi:
            return _discard(f"subjective_needs_majority_n_in_{lo}-{hi}")
        yes = sum(1 for v in votes if v)
        if yes * 2 <= n:
            return _discard("subjective_majority_not_met")

    return {
        "verdict": "keep",
        "reason": "zero_loss_and_predeclared_improvement",
        "policy": subjective_policy(),
    }


def _discard(reason: str) -> dict[str, Any]:
    return {
        "verdict": "discard",
        "reason": reason,
        "policy": subjective_policy(),
    }


def validate_lineage(
    *,
    stage: str,
    expected_input_hashes: dict[str, str],
    observed_input_hashes: dict[str, str],
) -> dict[str, Any]:
    """Fail closed when prompt hashes do not match the declared lineage stage.

    Stages:
      B0 — original-main freeze (task 130.1)
      B1 — post fleet-version structural baseline (task 130.2); later tasks
           MUST compare candidates to B1, never directly to B0
      candidate — a mutation under test against B1
    """
    mismatches = {
        k: {"expected": expected_input_hashes[k], "observed": observed_input_hashes.get(k)}
        for k in expected_input_hashes
        if observed_input_hashes.get(k) != expected_input_hashes[k]
    }
    ok = not mismatches
    return {
        "stage": stage,
        "ok": ok,
        "mismatches": mismatches,
        "rule": "fail_closed_on_hash_mismatch; structural_candidates_compare_to_B1_never_B0",
    }
