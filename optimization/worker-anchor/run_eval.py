#!/usr/bin/env python3
"""Comprehension-equivalence eval runner for the worker anchor bundle (fn-83.3, R9).

Per frozen task, two subject runs against the SAME question set:
  (a) bundle arm     — the subject sees ONLY ``inputs/<task>/bundle.md``
  (b) statusquo arm  — the subject sees ONLY ``inputs/<task>/statusquo.md``

The subject is a read-only headless `claude -p` call (no tools, empty cwd)
answering the committed question set strictly from the supplied document.
Grading is DETERMINISTIC against the committed answer key
(``questions.json`` accept/reject regexes) — bundle-vs-statusquo agreement
is NOT the metric; both-wrong fails both arms.

Merge gate (see README): on EVERY question set, bundle score >= statusquo
score AND bundle score >= the key threshold (6/7).

Usage:
  python3 optimization/worker-anchor/run_eval.py            # run + grade
  python3 optimization/worker-anchor/run_eval.py --grade-only  # regrade saved runs
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
KEY = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))

MODEL_ALIAS = "sonnet"  # resolved model id is recorded from the run JSON
TIMEOUT_S = 900

PROMPT_TEMPLATE = """You are a task-implementation worker re-anchoring on flow-next task {task_id}.
The document between the <document> tags below is the ONLY material you have.
Answer strictly from it — no tools, no prior knowledge of this repository, no guesses.

Questions:
{questions}

Output EXACTLY one line per question, formatted `q1: <concise answer>` (through q{n}).
No other text, no commentary.

<document>
{document}
</document>
"""


def build_prompt(task_short: str, arm: str) -> str:
    entry = KEY["tasks"][task_short]
    doc = (HERE / "inputs" / task_short / f"{arm}.md").read_text(
        encoding="utf-8"
    )
    questions = "\n".join(
        f"{q['id']}: {q['question']}" for q in entry["questions"]
    )
    return PROMPT_TEMPLATE.format(
        task_id=entry["task_id"],
        questions=questions,
        n=len(entry["questions"]),
        document=doc,
    )


def run_subject(task_short: str, arm: str) -> dict:
    prompt = build_prompt(task_short, arm)
    with tempfile.TemporaryDirectory() as empty_cwd:
        result = subprocess.run(
            ["claude", "-p", "--model", MODEL_ALIAS, "--output-format", "json"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_S,
            cwd=empty_cwd,
        )
    if result.returncode != 0:
        raise SystemExit(
            f"subject run failed ({task_short}/{arm}): {result.stderr[:500]}"
        )
    payload = json.loads(result.stdout)
    RUNS.mkdir(exist_ok=True)
    (RUNS / f"{task_short}-{arm}.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    return payload


def resolved_model(payload: dict) -> str:
    usage = payload.get("modelUsage") or {}
    if isinstance(usage, dict) and usage:
        return ";".join(sorted(usage.keys()))
    return str(payload.get("model", "unknown"))


def grade(task_short: str, answer_text: str) -> "tuple[int, int, list]":
    entry = KEY["tasks"][task_short]
    lines = {}
    for line in answer_text.splitlines():
        m = re.match(r"^\s*(q\d+)\s*:\s*(.*)$", line, re.IGNORECASE)
        if m:
            lines[m.group(1).lower()] = m.group(2)
    score = 0
    detail = []
    for q in entry["questions"]:
        answer = lines.get(q["id"], "")
        ok = bool(answer) and all(
            re.search(pat, answer, re.IGNORECASE) for pat in q["accept"]
        )
        if ok and any(
            re.search(pat, answer, re.IGNORECASE)
            for pat in q.get("reject", [])
        ):
            ok = False
        score += int(ok)
        detail.append((q["id"], "PASS" if ok else "FAIL", answer[:100]))
    return score, len(entry["questions"]), detail


def main() -> None:
    grade_only = "--grade-only" in sys.argv
    today = date.today().isoformat()
    rows = []
    gate_ok = True
    threshold_num = 6  # key threshold: 6/7 per set (README)

    for task_short in KEY["tasks"]:
        scores = {}
        for arm in ("bundle", "statusquo"):
            run_path = RUNS / f"{task_short}-{arm}.json"
            if grade_only:
                payload = json.loads(run_path.read_text(encoding="utf-8"))
            else:
                payload = run_subject(task_short, arm)
            model = resolved_model(payload)
            score, total, detail = grade(task_short, payload.get("result", ""))
            scores[arm] = score
            rows.append((today, task_short, arm, f"{score}/{total}", model))
            print(f"{task_short} [{arm}] {score}/{total}  model={model}")
            for qid, verdict, ans in detail:
                print(f"    {qid}: {verdict}  {ans}")
        if scores["bundle"] < scores["statusquo"]:
            gate_ok = False
            print(f"  GATE FAIL: bundle < statusquo on {task_short}")
        if scores["bundle"] < threshold_num:
            gate_ok = False
            print(f"  GATE FAIL: bundle below key threshold on {task_short}")

    print()
    print("MERGE GATE:", "PASS" if gate_ok else "FAIL")
    print()
    print("results.tsv rows:")
    for r in rows:
        print("\t".join(r))


if __name__ == "__main__":
    main()
