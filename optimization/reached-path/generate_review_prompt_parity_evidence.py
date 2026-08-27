#!/usr/bin/env python3
"""Regenerate the frozen review-prompt fixtures and token evidence (fn-159, recalibrated fn-206).

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

HINTS = "hint-a\nhint-b"
DSUM = " 3 files changed, 10 insertions(+), 2 deletions(-)"
BASE = "main"
FOCUS = "auth and sessions"
# Token deltas are point-in-time MEASUREMENTS recorded in the evidence JSON and
# judged via .flow/criteria.md G1 — never a stored ceiling. Prompt-size ratchets
# were deliberately removed (2026-08-07); this script measures, it does not gate.
ENCODINGS = ("cl100k_base", "o200k_base")


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


SPEC_PATH = ".flow/specs/fn-parity.md"
TASK_PATHS = (".flow/tasks/fn-parity.1.md", ".flow/tasks/fn-parity.2.md")
RANGE = "aaaaaaa..bbbbbbb"

_CORPUS_NAMES = ("plan_corpus_risky", "plan_corpus_clean", "plan_corpus_user_edited")


def _rendered_prompts(module: ModuleType) -> dict[str, str]:
    """Render the current builders (identities)."""
    prompts = {
        "impl": module.build_review_prompt(
            "impl", context_hints=HINTS, review_scope=DSUM,
            diff_range=RANGE, spec_path=SPEC_PATH,
        ),
        "impl_empty_optional": module.build_review_prompt(
            "impl", spec_path=SPEC_PATH
        ),
        "plan": module.build_review_prompt(
            "plan", context_hints=HINTS, spec_path=SPEC_PATH,
            task_spec_paths=TASK_PATHS,
        ),
        "plan_no_tasks": module.build_review_prompt(
            "plan", context_hints=HINTS, spec_path=SPEC_PATH
        ),
        "standalone": module.build_standalone_review_prompt(BASE, FOCUS, DSUM, RANGE),
        "standalone_no_focus": module.build_standalone_review_prompt(
            BASE, None, DSUM, RANGE
        ),
        "completion": module.build_completion_review_prompt(
            SPEC_PATH, TASK_PATHS, DSUM, RANGE
        ),
        "completion_no_tasks": module.build_completion_review_prompt(
            SPEC_PATH, (), DSUM, RANGE
        ),
    }
    for name in _CORPUS_NAMES:
        # The corpus bodies now differ ON DISK; the prompt names which one.
        prompts[name] = module.build_review_prompt(
            "plan",
            context_hints="Production Plan Review context hints.",
            spec_path=f".flow/specs/fn-corpus-{name}.md",
            task_spec_paths=(".flow/tasks/fn-corpus.1.md",),
        )
    return prompts


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True, help="immutable pre-edit commit")
    parser.add_argument("--write", action="store_true", help="write fixtures and evidence")
    args = parser.parse_args()

    # Post-fn-169 baseline: identical builder signatures, so render both sides
    # with the same inputs and measure only the fn-206 prompt-text delta.
    baseline = _rendered_prompts(_load_baseline(args.baseline))
    candidate = _rendered_prompts(_load_module(FLOWCTL_PATH, "flowctl_prompt_candidate"))
    if baseline.keys() != candidate.keys():
        raise ValueError("baseline and candidate prompt sets differ")
    encodings = {name: tiktoken.get_encoding(name) for name in ENCODINGS}
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
    measured_max_delta = {
        encoding: max(row["tokens"][encoding]["delta"] for row in prompts.values())
        for encoding in ENCODINGS
    }
    evidence = {
        "schema_version": 2,
        "baseline": {"commit": args.baseline, "kind": "immutable_git_commit"},
        "measurement": {
            "tool": "tiktoken",
            "version": tiktoken.__version__,
            "encodings": list(ENCODINGS),
        },
        "rebaseline": {
            "rationale": (
                "fn-206 intentionally adds the reviewer verification-budget rail to the impl "
                "and completion review prompts: focused suites plus finding-targeted commands; "
                "the full suite belongs to the run's final gate, never a review round."
            ),
            "measured_max_token_delta": measured_max_delta,
        },
        "prompts": prompts,
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
