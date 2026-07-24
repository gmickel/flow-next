#!/usr/bin/env python3
"""Real-backend B1/candidate Plan Review corpus evidence for fn-130.6."""

from __future__ import annotations

import concurrent.futures
import datetime as dt
import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
B1 = "8ed71a73ccc593a8a018dcdb805a86f396dcf76f"
OUT = HERE / "evidence" / "fn130" / "plan-review-real-backend.json"
FLOWCTL_PATH = REPO / "plugins/flow-next/scripts/flowctl.py"
PROMPT_PATH = (
    "plugins/flow-next/skills/flow-next-plan-review/references/plan-review-prompt.md"
)


def load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location("fn130_plan_review_flowctl", FLOWCTL_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load flowctl")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FLOWCTL = load_flowctl()

PLANTED = {
    "P1": ["untestable", "not measurable", "vague", "r2"],
    "P2": ["malformed", "invalid row", "validation", "error handling"],
    "P3": ["interface", "contract", "return type", "underspecified"],
    "P4": ["empty file", "duplicate", "oversized", "encoding", "edge case"],
    "P5": ["too large", "split", "decompose", "one iteration"],
    "P6": ["ordering", "dependency", "task 3 before", "sequencing"],
    "P7": ["test strategy", "missing test", "test coverage"],
    "P8": ["idempoten", "rollback", "partial failure", "atomic"],
    "P9": ["observability", "logging", "metrics", "progress"],
    "P10": ["contradic", "synchronous", "background", "inconsistent"],
}


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def corpus() -> dict[str, str]:
    root = REPO / "optimization/review-prompt"
    return {
        "risky": (root / "spec_corpus.md").read_text(),
        "clean": (root / "spec_clean.md").read_text(),
        "user-edited": (
            "# User-edited plan\n\n"
            "## Acceptance\n"
            "- Preserve operator-authored batch size 37; do not restore generated 50.\n"
            "## Test strategy\n"
            "- Verify batches of exactly 37 and malformed-row rollback.\n"
        ),
    }


def build_prompt(spec: str) -> str:
    return FLOWCTL.build_review_prompt(
        "plan",
        spec,
        "Production Plan Review context hints.",
        task_specs="Current persisted task specs; respect operator-authored values.",
    )


def run_review(
    variant: str,
    name: str,
    prompt: str,
    model: str,
    effort: str,
) -> dict[str, Any]:
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
        "--json",
        "-",
    ]
    proc = subprocess.run(
        cmd,
        input=prompt,
        text=True,
        capture_output=True,
        cwd=REPO,
        timeout=600,
    )
    messages: list[str] = []
    usage: dict[str, Any] = {}
    for line in proc.stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "turn.completed":
            usage = event.get("usage") or {}
        item = event.get("item") or {}
        if item.get("type") == "agent_message" and item.get("text"):
            messages.append(item["text"])
    review = "\n".join(messages)
    if proc.returncode != 0 or not review or usage.get("input_tokens", 0) <= 0:
        raise RuntimeError(
            f"{variant}/{name} backend failure rc={proc.returncode}: {proc.stderr[-500:]}"
        )
    verdicts = re.findall(r"<verdict>(\w+)</verdict>", review)
    lower = review.lower()
    evidence: dict[str, Any] = {}
    if name == "risky":
        evidence["detections"] = {
            key: any(word in lower for word in words) for key, words in PLANTED.items()
        }
        evidence["caught"] = sum(evidence["detections"].values())
    elif name == "clean":
        evidence["clean_ship"] = verdicts[-1] == "SHIP" if verdicts else False
    else:
        evidence["preserves_37"] = "37" in review
        evidence["does_not_restore_50"] = not re.search(
            r"(restore|use|change to|batch size)\D{0,20}50", lower
        )
    return {
        "id": f"{variant}-{name}",
        "variant": variant,
        "corpus": name,
        "prompt_sha256": sha(prompt),
        "usage": usage,
        "verdict": verdicts[-1] if verdicts else "UNKNOWN",
        "evidence": evidence,
        "review_sha256": sha(review),
        "review": review,
    }


def main() -> int:
    model = "gpt-5.6-sol"
    effort = "high"
    rows: list[dict[str, Any]] = []
    specs = corpus()
    prompts = {name: build_prompt(spec) for name, spec in specs.items()}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = [
            pool.submit(run_review, variant, name, prompts[name], model, effort)
            for variant in ("b1", "candidate")
            for name in specs
        ]
        for future in concurrent.futures.as_completed(futures):
            row = future.result()
            rows.append(row)
            print(f"reviewed {row['id']} -> {row['verdict']}")
    rows.sort(key=lambda row: row["id"])

    by_id = {row["id"]: row for row in rows}
    risky_floor = min(
        by_id[f"{variant}-risky"]["evidence"]["caught"]
        for variant in ("b1", "candidate")
    )
    checks = {
        "prompt_template_byte_identical_to_b1": sha(
            (REPO / PROMPT_PATH).read_text()
        )
        == sha(
            subprocess.run(
                ["git", "show", f"{B1}:{PROMPT_PATH}"],
                cwd=REPO,
                capture_output=True,
                text=True,
                check=True,
            ).stdout
        ),
        "baseline_candidate_prompts_identical": all(
            by_id[f"b1-{name}"]["prompt_sha256"]
            == by_id[f"candidate-{name}"]["prompt_sha256"]
            for name in specs
        ),
        "risky_detection_floor": risky_floor >= 7,
        "clean_ships": all(
            by_id[f"{variant}-clean"]["evidence"]["clean_ship"]
            for variant in ("b1", "candidate")
        ),
        "user_edit_grounded": all(
            by_id[f"{variant}-user-edited"]["evidence"]["preserves_37"]
            and by_id[f"{variant}-user-edited"]["evidence"]["does_not_restore_50"]
            for variant in ("b1", "candidate")
        ),
        "nonzero_usage": all(row["usage"].get("input_tokens", 0) > 0 for row in rows),
    }
    artifact = {
        "schema_version": 1,
        "date_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "lineage": f"{B1} -> candidate",
        "backend": "codex",
        "model": model,
        "effort": effort,
        "backend_version": subprocess.run(
            ["codex", "--version"], capture_output=True, text=True, check=True
        ).stdout.strip(),
        "production_builder": "flowctl.build_review_prompt(plan)",
        "corpus_hashes": {name: sha(spec) for name, spec in specs.items()},
        "checks": checks,
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(artifact, indent=2) + "\n")
    print(json.dumps(checks, indent=2))
    print(f"evidence -> {OUT.relative_to(REPO)}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
