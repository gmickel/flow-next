#!/usr/bin/env python3
"""Regenerate fn-159's frozen review-prompt fixtures and token evidence.

Run from the repository root after intentional prompt edits:

    uv run --with tiktoken==0.13.0 \
      optimization/reached-path/generate_review_prompt_parity_evidence.py \
      --baseline <pre-edit-commit> --write

The script independently renders the immutable baseline source and the current
source with the exact parity-suite inputs. ``--write`` is deliberately required
before it mutates tracked fixtures or evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType

import tiktoken


ROOT = Path(__file__).resolve().parents[2]
FLOWCTL_PATH = ROOT / "plugins/flow-next/scripts/flowctl.py"
FIXTURES = ROOT / "plugins/flow-next/tests/fixtures/review_prompts"
EVIDENCE = ROOT / "optimization/reached-path/evidence/fn136/review-output-format-token-delta.json"

SPEC = "SPEC_BODY_LINE1\nSPEC_BODY_LINE2"
HINTS = "hint-a\nhint-b"
DSUM = " 3 files changed, 10 insertions(+), 2 deletions(-)"
DDIFF = "diff --git a/x.py b/x.py\n+print(1)\n"
TASKS = "TASK1\nTASK2"
BASE = "main"
FOCUS = "auth and sessions"
# Measured fn-159 calibration deltas. This exact ceiling makes any subsequent
# prompt growth a conscious rebaseline, not a quietly widening allowance.
MAX_TOKEN_DELTA = {"cl100k_base": 310, "o200k_base": 308}


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_baseline(commit: str) -> ModuleType:
    source = subprocess.run(
        ["git", "show", f"{commit}:plugins/flow-next/scripts/flowctl.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "flowctl.py"
        path.write_text(source, encoding="utf-8")
        module = _load_module(path, "flowctl_prompt_baseline")
    for loader, fallback_name in {
        "load_impl_review_template": "IMPL_REVIEW_PROMPT_FALLBACK",
        "load_plan_review_template": "PLAN_REVIEW_PROMPT_FALLBACK",
        "load_standalone_review_template": "STANDALONE_REVIEW_PROMPT_FALLBACK",
        "load_completion_review_template": "COMPLETION_REVIEW_PROMPT_FALLBACK",
    }.items():
        fallback = getattr(module, fallback_name)
        setattr(module, loader, lambda fallback=fallback: fallback)
    return module


def _without_output_format(text: str) -> str:
    start = text.index("## Output Format\n")
    offset = start + len("## Output Format\n")
    in_fence = False
    for line in text[offset:].splitlines(keepends=True):
        if line.startswith("```"):
            in_fence = not in_fence
        elif not in_fence and line.startswith("## "):
            return text[:start] + "## Output Format\n<FORMAT>\n" + text[offset:]
        offset += len(line)
    raise ValueError("Output Format has no following section boundary")


def _rendered_prompts(module: ModuleType) -> dict[str, str]:
    prompts = {
        "impl": module.build_review_prompt(
            "impl", SPEC, HINTS, diff_summary=DSUM, diff_content=DDIFF
        ),
        "impl_empty_optional": module.build_review_prompt(
            "impl", SPEC, "", diff_summary="", diff_content=""
        ),
        "plan": module.build_review_prompt("plan", SPEC, HINTS, task_specs=TASKS),
        "plan_no_tasks": module.build_review_prompt("plan", SPEC, HINTS),
        "standalone": module.build_standalone_review_prompt(BASE, FOCUS, DSUM),
        "standalone_no_focus": module.build_standalone_review_prompt(BASE, None, DSUM),
        "completion": module.build_completion_review_prompt(SPEC, TASKS, DSUM, DDIFF),
        "completion_no_tasks": module.build_completion_review_prompt(SPEC, "", DSUM, DDIFF),
    }
    corpus_root = ROOT / "optimization/review-prompt"
    for name, spec in {
        "plan_corpus_risky": (corpus_root / "spec_corpus.md").read_text(encoding="utf-8"),
        "plan_corpus_clean": (corpus_root / "spec_clean.md").read_text(encoding="utf-8"),
        "plan_corpus_user_edited": (
            "# User-edited plan\n\n## Acceptance\n"
            "- Preserve operator-authored batch size 37; do not restore generated 50.\n"
            "## Test strategy\n- Verify batches of exactly 37 and malformed-row rollback.\n"
        ),
    }.items():
        prompts[name] = module.build_review_prompt(
            "plan",
            spec,
            "Production Plan Review context hints.",
            task_specs="Current task specs are supplied from persisted .flow/task files.",
        )
    return prompts


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True, help="immutable pre-edit commit")
    parser.add_argument("--write", action="store_true", help="write fixtures and evidence")
    args = parser.parse_args()

    baseline = _rendered_prompts(_load_baseline(args.baseline))
    candidate = _rendered_prompts(_load_module(FLOWCTL_PATH, "flowctl_prompt_candidate"))
    if baseline.keys() != candidate.keys():
        raise ValueError("baseline and candidate prompt sets differ")
    encodings = {name: tiktoken.get_encoding(name) for name in MAX_TOKEN_DELTA}
    prompts = {}
    for name in sorted(candidate):
        token_counts = {
            encoding: {
                "baseline": len(codec.encode(baseline[name])),
                "candidate": len(codec.encode(candidate[name])),
            }
            for encoding, codec in encodings.items()
        }
        for counts in token_counts.values():
            counts["delta"] = counts["candidate"] - counts["baseline"]
        prompts[name] = {
            "baseline_sha256": _sha(baseline[name]),
            "baseline_masked_sha256": _sha(_without_output_format(baseline[name])),
            "candidate_sha256": _sha(candidate[name]),
            "candidate_masked_sha256": _sha(_without_output_format(candidate[name])),
            "tokens": token_counts,
        }
    within_budget = all(
        counts["delta"] <= MAX_TOKEN_DELTA[encoding]
        for row in prompts.values()
        for encoding, counts in row["tokens"].items()
    )
    evidence = {
        "schema_version": 2,
        "baseline": {"commit": args.baseline, "kind": "immutable_git_commit"},
        "measurement": {
            "tool": "tiktoken",
            "version": tiktoken.__version__,
            "encodings": list(MAX_TOKEN_DELTA),
        },
        "rebaseline": {
            "rationale": (
                "fn-159 intentionally changes review instructions outside Output Format: "
                "surface severity, confidence, terminal grammar, and settled-plan calibration."
            ),
            "max_token_delta": MAX_TOKEN_DELTA,
        },
        "prompts": prompts,
        "acceptance": {"all_deltas_within_rebaseline_budget": within_budget},
    }
    payload = json.dumps(evidence, indent=2, sort_keys=True) + "\n"
    if args.write:
        for name, prompt in candidate.items():
            if name in {
                "impl", "impl_empty_optional", "plan", "plan_no_tasks",
                "standalone", "standalone_no_focus", "completion", "completion_no_tasks",
            }:
                (FIXTURES / f"{name}.txt").write_text(prompt, encoding="utf-8")
        EVIDENCE.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
