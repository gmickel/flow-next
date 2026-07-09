#!/usr/bin/env python3
"""reveval_parse_guard.py — OFFLINE regression guard for the fn-90 runaway class.

The backend-in-the-loop harness (`reveval.py` / `reveval_plan.py`) needs live
models. This guard does NOT — it exercises the two DETERMINISTIC failure modes
behind the Cursor review-backend loop runaway (fn-90) so the class is caught on
every gate run, no CLI, no network, no cost:

  1. **Poisoned-stream parse.** The codex/copilot verdict path used to first-match
     `<verdict>…</verdict>` over the ENTIRE stream, so a verdict literal echoed in
     tool output (`command_execution` / `aggregated_output` — e.g. a grep of
     smoke_test.sh's assertions) could beat the reviewer's real verdict. flowctl
     reported SHIP while the reviewer said NEEDS_WORK. The fix isolates the final
     agent message and takes the LAST match. This guard replays both pollution
     shapes (tool-output literal + quoted-grammar literal) and asserts the true
     verdict wins.

  2. **Convergence guard.** The runaway's second root cause was a FRESH blind
     re-review each round (churn lottery). The ratchet must inject the prior
     findings and flip the contract to shrink-only (MUST-SHIP once prior findings
     are fixed and no new ≥Major). This guard asserts the ratchet block is present
     and carries the shrink-only contract, and that it stays empty (fresh review)
     on round 1 / a legacy receipt with no prior findings.

Run: `python3 reveval_parse_guard.py`  → prints PASS/FAIL, exits non-zero on FAIL.
Also imported by the flow-next unittest suite (see
`plugins/flow-next/tests/test_reveval_parse_guard.py`) so it runs in the gate.
"""
import importlib.util
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_FLOWCTL_PATH = os.path.join(REPO, "plugins/flow-next/scripts/flowctl.py")


def _load_flowctl():
    spec = importlib.util.spec_from_file_location("flowctl_guard", _FLOWCTL_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()


# ---------------------------------------------------------------- stream helpers
def _stream(*events: dict) -> str:
    return "\n".join(json.dumps(e) for e in events) + "\n"


def _agent_message(text: str) -> dict:
    return {"type": "item.completed", "item": {"type": "agent_message", "text": text}}


def _command_execution(aggregated_output: str) -> dict:
    return {
        "type": "item.completed",
        "item": {
            "type": "command_execution",
            "status": "completed",
            "aggregated_output": aggregated_output,
        },
    }


# ---------------------------------------------------------------- fixtures
# Shape 1 + 2 combined: a tool event echoes a SHIP literal from smoke_test.sh
# assertions AND the reviewer quotes the SHIP grammar while explaining the
# contract — then emits the REAL NEEDS_WORK verdict last. The true verdict must
# win on both counts.
POISONED_STREAM = _stream(
    {"type": "thread.started", "thread_id": "t-guard"},
    {"type": "turn.started"},
    _command_execution(
        "grep smoke_test.sh -> assert '<verdict>SHIP</verdict>' in output\n"
        "grep smoke_test.sh -> assert '<verdict>NEEDS_WORK</verdict>' in output"
    ),
    _agent_message(
        "Per the contract I emit either `<verdict>SHIP</verdict>` or "
        "`<verdict>NEEDS_WORK</verdict>`.\n\n"
        "There is a Critical off-by-one in line_total, so:\n"
        "<verdict>NEEDS_WORK</verdict>"
    ),
    {"type": "turn.completed", "usage": {}},
)

PRIOR_FINDINGS = (
    "Major: build_rereview_preamble ordered a fresh review each round.\n"
    "Minor: docstring wording."
)


# ---------------------------------------------------------------- checks
def _check(name: str, cond: bool, detail: str = "") -> bool:
    status = "PASS" if cond else "FAIL"
    line = f"  [{status}] {name}"
    if detail and not cond:
        line += f" — {detail}"
    print(line)
    return cond


def run_guard() -> bool:
    """Returns True iff every guard assertion holds."""
    ok = True
    print("fn-90 poisoned-stream parse guard:")

    # 1. Poisoned stream — the reviewer's true NEEDS_WORK must win, not the
    #    SHIP literals in tool output / quoted grammar.
    verdict = flowctl.parse_codex_verdict(POISONED_STREAM)
    ok &= _check(
        "poisoned stream parses to true verdict (NEEDS_WORK)",
        verdict == "NEEDS_WORK",
        f"got {verdict!r}",
    )

    # 2. The isolated final agent message must not contain the tool-output line.
    final = flowctl.extract_codex_final_message(POISONED_STREAM)
    ok &= _check(
        "final-message isolation drops aggregated_output",
        "grep smoke_test.sh" not in final and "off-by-one in line_total" in final,
    )

    print("fn-90 convergence-ratchet guard:")

    # 3. Round 1 / legacy receipt (no prior findings) → fresh review (empty block).
    ok &= _check(
        "no prior findings → fresh review (empty ratchet block)",
        flowctl.build_convergence_ratchet_block(None) == ""
        and flowctl.build_convergence_ratchet_block("") == "",
    )

    # 4. Prior findings → shrink-only ratchet contract injected.
    block = flowctl.build_convergence_ratchet_block(PRIOR_FINDINGS)
    ok &= _check(
        "prior findings injected under <prior_findings>",
        "<prior_findings>" in block and "build_rereview_preamble" in block,
    )
    ok &= _check(
        "shrink-only contract present (MUST-SHIP + ≥Major-only-blocks)",
        "MUST be `<verdict>SHIP</verdict>`" in block
        and "≥ Major" in block
        and "convergence, not leniency" in block,
    )

    # 5. build_rereview_preamble carries the ratchet through for impl + plan.
    for review_type in ("plan", "implementation", "completion"):
        pre = flowctl.build_rereview_preamble(
            ["flowctl.py"], review_type, prior_findings=PRIOR_FINDINGS
        )
        ok &= _check(
            f"re-review preamble ({review_type}) carries the ratchet",
            "CONVERGENCE RATCHET" in pre,
        )

    return ok


def main() -> int:
    ok = run_guard()
    print()
    if ok:
        print("fn-90 parse+convergence guard: ALL PASS")
        return 0
    print("fn-90 parse+convergence guard: FAILURES ABOVE", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
