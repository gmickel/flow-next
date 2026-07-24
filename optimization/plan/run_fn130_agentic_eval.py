#!/usr/bin/env python3
"""Paired B1/candidate Plan-emission eval for fn-130.7 completion evidence."""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
B1 = "8ed71a73ccc593a8a018dcdb805a86f396dcf76f"
PLAN_FILES = (
    "plugins/flow-next/skills/flow-next-plan/SKILL.md",
    "plugins/flow-next/skills/flow-next-plan/steps.md",
    "plugins/flow-next/skills/flow-next-plan/examples.md",
)
EVIDENCE = HERE / "evidence" / "fn130"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def git_text(ref: str, path: str) -> str:
    run = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    return run.stdout


def instructions(variant: str) -> tuple[str, dict[str, str]]:
    texts: list[str] = []
    hashes: dict[str, str] = {}
    for path in PLAN_FILES:
        body = git_text(B1, path) if variant == "b1" else (REPO / path).read_text()
        texts.append(f"\n\n===== {path} =====\n\n{body}")
        hashes[path] = sha(body)
    return "".join(texts), hashes


def fixtures() -> dict[str, str]:
    source = (HERE / "test-inputs.md").read_text()
    found: dict[str, str] = {}
    for index in range(1, 5):
        match = re.search(
            rf"^## P{index}\b.*?(?=^## P{index + 1}\b|\Z)",
            source,
            flags=re.MULTILINE | re.DOTALL,
        )
        if not match:
            raise RuntimeError(f"missing P{index} fixture")
        found[f"P{index}"] = match.group(0).strip()
    found["P5"] = (HERE / "holdout" / "input.md").read_text().strip()
    return found


def emission_prompt(rules: str, fixture_id: str, fixture: str) -> str:
    return f"""You are evaluating Plan's authoring judgment. Treat the PLAN INSTRUCTIONS
below as your complete operating instructions. The research bundle is already frozen:
do not browse, call tools, ask questions, or modify files.

Produce exactly the spec and task specifications those instructions would create for
fixture {fixture_id}. Output markdown only. Include the full spec, task frontmatter,
acceptance criteria, dependency/wave information, and requirement-coverage table.

<plan_instructions>
{rules}
</plan_instructions>

<fixture>
{fixture}
</fixture>

<eval_override>
This is an output-only evaluation. Any Plan instruction to call Write, Edit,
flowctl, Task, AskUserQuestion, or another tool means: render the artifact that
would result inline in your response instead. Do not stop at a proposed tool
call or narrate what you would write. Your response itself must contain the full
spec and task markdown.
</eval_override>
"""


def run_emission(
    variant: str,
    run_number: int,
    fixture_id: str,
    fixture: str,
    rules: str,
    model: str,
) -> dict[str, Any]:
    prompt = emission_prompt(rules, fixture_id, fixture)
    cmd = [
        "claude",
        "-p",
        "--safe-mode",
        "--disable-slash-commands",
        "--append-system-prompt",
        (
            "Output-only evaluation: never call or propose a tool. Render every "
            "would-be spec/task write fully inline in the final response."
        ),
        "--tools",
        "",
        "--permission-mode",
        "plan",
        "--model",
        model,
        "--output-format",
        "json",
        "--no-session-persistence",
    ]
    proc = subprocess.run(
        cmd,
        input=prompt,
        text=True,
        capture_output=True,
        cwd=tempfile.gettempdir(),
        timeout=360,
    )
    try:
        envelope = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"{variant}/run{run_number}/{fixture_id}: invalid Claude JSON: "
            f"{proc.stderr[-500:]}"
        ) from exc
    usage = envelope.get("usage") or {}
    result = envelope.get("result")
    if (
        proc.returncode != 0
        or envelope.get("is_error")
        or not isinstance(result, str)
        or not result.strip()
        or usage.get("input_tokens", 0) <= 0
        or usage.get("output_tokens", 0) <= 0
    ):
        raise RuntimeError(
            f"{variant}/run{run_number}/{fixture_id}: invalid authenticated run "
            f"rc={proc.returncode} error={envelope.get('is_error')} usage={usage} "
            f"result={str(result)[:200]}"
        )
    return {
        "id": f"{variant}-r{run_number}-{fixture_id}",
        "variant": variant,
        "run": run_number,
        "fixture": fixture_id,
        "fixture_sha256": sha(fixture),
        "subject_prompt_sha256": sha(prompt),
        "oracle_in_subject_prompt": False,
        "model": model,
        "usage": usage,
        "result_sha256": sha(result),
        "result": result,
    }


def score_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["rows"],
        "properties": {
            "rows": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["id", "cells"],
                    "properties": {
                        "id": {"type": "string"},
                        "cells": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["id", "pass", "reason"],
                                "properties": {
                                    "id": {"type": "string"},
                                    "pass": {"type": "boolean"},
                                    "reason": {"type": "string"},
                                },
                            },
                        },
                    },
                },
            }
        },
    }


def score_prompt(rows: list[dict[str, Any]]) -> str:
    evals = (HERE / "evals.md").read_text()
    oracle = (HERE / "holdout" / "oracle.md").read_text()
    rendered = "\n\n".join(
        f"<emission id=\"{row['id']}\">\n{row['result']}\n</emission>" for row in rows
    )
    return f"""Score the supplied Plan emissions only. Do not call tools or inspect the
repository. Apply E1-E5 to P1-P4 and H1-H7 to P5. Emit one row for every input
emission, with exactly those cell IDs and concise evidence-based reasons. Do not
compare variants; score each independently.

<p1_p4_rubric>
{evals}
</p1_p4_rubric>

<p5_oracle>
{oracle}
</p5_oracle>

{rendered}
"""


def run_scorer(
    rows: list[dict[str, Any]], model: str, effort: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    with tempfile.TemporaryDirectory(prefix="fn130-plan-score-") as td:
        root = Path(td)
        schema_path = root / "schema.json"
        output_path = root / "score.json"
        schema_path.write_text(json.dumps(score_schema()))
        cmd = [
            "codex",
            "exec",
            "--model",
            model,
            "-c",
            f'model_reasoning_effort="{effort}"',
            "--sandbox",
            "read-only",
            "--skip-git-repo-check",
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(output_path),
            "--json",
            "-",
        ]
        proc = subprocess.run(
            cmd,
            input=score_prompt(rows),
            text=True,
            capture_output=True,
            cwd=root,
            timeout=600,
        )
        if proc.returncode != 0 or not output_path.is_file():
            raise RuntimeError(f"scorer failed rc={proc.returncode}: {proc.stderr[-1000:]}")
        score = json.loads(output_path.read_text())
        usage: dict[str, Any] = {}
        for line in proc.stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "turn.completed":
                usage = event.get("usage") or {}
        return score, usage


def validate_score(
    emissions: list[dict[str, Any]], score: dict[str, Any]
) -> dict[str, Any]:
    expected_rows = {row["id"]: row for row in emissions}
    actual_rows = {row["id"]: row for row in score.get("rows", [])}
    if set(actual_rows) != set(expected_rows):
        raise RuntimeError("scorer row IDs do not match emission IDs")
    cell_maps: dict[str, dict[str, bool]] = {}
    for row_id, emission in expected_rows.items():
        required = {f"E{i}" for i in range(1, 6)}
        if emission["fixture"] == "P5":
            required = {f"H{i}" for i in range(1, 8)}
        cells = {cell["id"]: bool(cell["pass"]) for cell in actual_rows[row_id]["cells"]}
        if set(cells) != required:
            raise RuntimeError(f"{row_id}: cells {sorted(cells)} != {sorted(required)}")
        cell_maps[row_id] = cells

    regressions: list[str] = []
    for run_number in (1, 2):
        for fixture_id in ("P1", "P2", "P3", "P4"):
            baseline = cell_maps[f"b1-r{run_number}-{fixture_id}"]
            candidate = cell_maps[f"candidate-r{run_number}-{fixture_id}"]
            for cell_id, passed in baseline.items():
                if passed and not candidate[cell_id]:
                    regressions.append(f"run{run_number}/{fixture_id}/{cell_id}")

    p5_runs = sorted(
        row["run"] for row in emissions
        if row["variant"] == "b1" and row["fixture"] == "P5"
    )
    if len(p5_runs) < 3:
        raise RuntimeError("P5 subjective cells require majority N>=3")
    for cell_id in (f"H{i}" for i in range(1, 8)):
        baseline_passes = sum(
            cell_maps[f"b1-r{run_number}-P5"][cell_id] for run_number in p5_runs
        )
        candidate_passes = sum(
            cell_maps[f"candidate-r{run_number}-P5"][cell_id]
            for run_number in p5_runs
        )
        majority = len(p5_runs) // 2 + 1
        if baseline_passes >= majority and candidate_passes < majority:
            regressions.append(f"majority/P5/{cell_id}")
    return {
        "baseline_passes": sum(sum(row.values()) for key, row in cell_maps.items() if key.startswith("b1-")),
        "candidate_passes": sum(sum(row.values()) for key, row in cell_maps.items() if key.startswith("candidate-")),
        "regressions": regressions,
        "zero_loss": not regressions,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=2)
    parser.add_argument("--p5-runs", type=int, default=3)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--scorer-model", default="gpt-5.6-sol")
    parser.add_argument("--scorer-effort", default="high")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="reuse existing emissions and run only missing variant/run/fixture cells",
    )
    args = parser.parse_args()
    if args.runs < 2 or args.p5_runs < 3:
        parser.error("fn-130 evidence requires paired N>=2 and P5 majority N>=3")

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    fixture_map = fixtures()
    oracle = (HERE / "holdout" / "oracle.md").read_text()
    variant_rules: dict[str, str] = {}
    source_hashes: dict[str, dict[str, str]] = {}
    for variant in ("b1", "candidate"):
        variant_rules[variant], source_hashes[variant] = instructions(variant)

    jobs = []
    for variant in ("b1", "candidate"):
        for fixture_id, fixture in fixture_map.items():
            run_count = args.p5_runs if fixture_id == "P5" else args.runs
            for run_number in range(1, run_count + 1):
                jobs.append((variant, run_number, fixture_id, fixture))

    out = EVIDENCE / "paired-emissions.json"
    emissions: list[dict[str, Any]] = []
    if args.resume and out.is_file():
        emissions = json.loads(out.read_text()).get("emissions", [])
    existing_ids = {row["id"] for row in emissions}
    jobs = [
        job for job in jobs
        if f"{job[0]}-r{job[1]}-{job[2]}" not in existing_ids
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [
            pool.submit(
                run_emission,
                variant,
                run_number,
                fixture_id,
                fixture,
                variant_rules[variant],
                args.model,
            )
            for variant, run_number, fixture_id, fixture in jobs
        ]
        for future in concurrent.futures.as_completed(futures):
            row = future.result()
            if oracle in emission_prompt(
                variant_rules[row["variant"]],
                row["fixture"],
                fixture_map[row["fixture"]],
            ):
                raise RuntimeError(f"{row['id']}: scorer oracle leaked into subject prompt")
            emissions.append(row)
            print(f"emitted {row['id']}")

    emissions.sort(key=lambda row: row["id"])
    score, scorer_usage = run_scorer(
        emissions, args.scorer_model, args.scorer_effort
    )
    ratchet = validate_score(emissions, score)
    claude_version = subprocess.run(
        ["claude", "--version"], capture_output=True, text=True, check=True
    ).stdout.strip()
    codex_version = subprocess.run(
        ["codex", "--version"], capture_output=True, text=True, check=True
    ).stdout.strip()
    artifact = {
        "schema_version": 1,
        "date_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "lineage": f"{B1} -> candidate",
        "subject_model": args.model,
        "subject_cli": claude_version,
        "scorer_model": args.scorer_model,
        "scorer_effort": args.scorer_effort,
        "scorer_cli": codex_version,
        "scorer_usage": scorer_usage,
        "source_hashes": source_hashes,
        "fixture_hashes": {key: sha(value) for key, value in fixture_map.items()},
        "oracle_sha256": sha(oracle),
        "oracle_excluded_from_subject_prompts": True,
        "emissions": emissions,
        "scores": score["rows"],
        "ratchet": ratchet,
    }
    out.write_text(json.dumps(artifact, indent=2) + "\n")
    print(json.dumps(ratchet, indent=2))
    print(f"evidence -> {out.relative_to(REPO)}")
    return 0 if ratchet["zero_loss"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
