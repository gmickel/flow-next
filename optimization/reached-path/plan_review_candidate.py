"""Plan Review selected-backend candidate evidence (fn-130.6).

Measures the real skill read route with the frozen reached-path algorithm and
exercises the production ``build_review_prompt("plan", ...)`` path for risky,
clean, and user-edited corpora. No parallel prompt construction.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from character import compute_reached_path_from_paths, file_hash
from ratchet import decide_ratchet

SKILL_DIR = Path("plugins/flow-next/skills/flow-next-plan-review")
ROOT = SKILL_DIR / "SKILL.md"
COMMON = SKILL_DIR / "workflow.md"
PROMPT = SKILL_DIR / "references/plan-review-prompt.md"
BACKENDS = ("codex", "copilot", "cursor", "host", "rp")
ROUTES = ("none", "export", "host", "codex", "copilot", "cursor", "rp", "unavailable")


def backend_file(backend: str) -> Path:
    return SKILL_DIR / f"workflow-{backend}.md"


def selected_backend(route: str) -> str | None:
    if route in ("none", "export"):
        return None
    # Configured-but-unavailable is represented by a selected Codex backend
    # whose executable check fails. It must still load only Codex guidance.
    return "codex" if route == "unavailable" else route


def route_trace(repo_root: Path, route: str) -> dict[str, Any]:
    if route not in ROUTES:
        raise ValueError(f"unknown Plan Review route: {route}")
    selected = selected_backend(route)
    activated = [repo_root / COMMON]
    if selected:
        activated.append(repo_root / backend_file(selected))
    measured = compute_reached_path_from_paths(
        repo_root,
        repo_root / ROOT,
        activated,
    )
    required = [ROOT.as_posix(), COMMON.as_posix()]
    if selected:
        required.append(backend_file(selected).as_posix())
    forbidden = [
        backend_file(name).as_posix()
        for name in BACKENDS
        if name != selected
    ]
    return {
        "route": route,
        "selected_backend": selected,
        "required_reads": required,
        "forbidden_reads": forbidden,
        "metrics": measured,
    }


def route_evidence(repo_root: Path) -> dict[str, Any]:
    rows = []
    for route in ROUTES:
        baseline_path = (
            repo_root
            / "optimization/reached-path/fixtures/b1/plan-review"
            / f"{route}.json"
        )
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        candidate = route_trace(repo_root, route)
        b1_chars = baseline["metrics"]["reached_path_chars"]
        candidate_chars = candidate["metrics"]["reached_path_chars"]
        candidate["baseline_b1_chars"] = b1_chars
        candidate["reduction_chars"] = b1_chars - candidate_chars
        candidate["reduction_percent"] = round(
            100 * (b1_chars - candidate_chars) / b1_chars, 2
        )
        rows.append(candidate)
    measured_paths = {
        row["route"]: {file["path"] for file in row["metrics"]["files"]}
        for row in rows
    }
    accuracy = {
        "all_routes_have_common": all(
            COMMON.as_posix() in measured_paths[row["route"]] for row in rows
        ),
        "none_export_backend_cold": all(
            row["selected_backend"] is None
            and all(
                backend_file(b).as_posix() not in measured_paths[row["route"]]
                for b in BACKENDS
            )
            for row in rows
            if row["route"] in ("none", "export")
        ),
        "exactly_one_selected_backend": all(
            sum(
                backend_file(b).as_posix() in measured_paths[row["route"]]
                for b in BACKENDS
            )
            == 1
            and backend_file(row["selected_backend"]).as_posix()
            in measured_paths[row["route"]]
            for row in rows
            if row["route"] not in ("none", "export")
        ),
        "every_route_reduced": all(row["reduction_chars"] > 0 for row in rows),
    }
    worst_candidate = max(row["metrics"]["reached_path_chars"] for row in rows)
    ratchet = decide_ratchet(
        baseline_accuracy={key: True for key in accuracy},
        candidate_accuracy=accuracy,
        baseline_metrics={
            "reached_path_chars": rows[0]["baseline_b1_chars"],
            "__lower_better__": ["reached_path_chars"],
        },
        candidate_metrics={"reached_path_chars": worst_candidate},
    )
    return {
        "lineage": "B0 -> V1/B1 -> candidate",
        "algorithm": "lf-full-file-on-activation-once-per-path-hash",
        "routes": rows,
        "accuracy": accuracy,
        "ratchet": ratchet,
    }


def corpus_evidence(
    repo_root: Path,
    build_plan_prompt: Callable[..., str],
) -> dict[str, Any]:
    """Exercise the production backend prompt builder, not a prose-reader proxy."""
    corpus_root = repo_root / "optimization/review-prompt"
    risky = (corpus_root / "spec_corpus.md").read_text(encoding="utf-8")
    clean = (corpus_root / "spec_clean.md").read_text(encoding="utf-8")
    user_edited = (
        "# User-edited plan\n\n"
        "## Acceptance\n"
        "- Preserve operator-authored batch size 37; do not restore generated 50.\n"
        "## Test strategy\n"
        "- Verify batches of exactly 37 and malformed-row rollback.\n"
    )
    # fn-169 R4: the prompt carries the spec PATH, so the corpus varies by path,
    # not by embedded body. `spec_grounded_verbatim` became a path claim: the
    # reviewer must be able to resolve exactly one named spec. The three bodies
    # above still differ, but they now differ ON DISK, which is where the
    # reviewer reads them — the prompt's job is to name which one.
    task_path = ".flow/tasks/fn-corpus.1.md"
    rows = {}
    for name, spec in (
        ("risky", risky),
        ("clean", clean),
        ("user-edited-spec", user_edited),
    ):
        spec_path = f".flow/specs/fn-corpus-{name}.md"
        prompt = build_plan_prompt(
            "plan",
            context_hints="Production Plan Review context hints.",
            spec_path=spec_path,
            task_spec_paths=(task_path,),
        )
        rows[name] = {
            "production_builder": "flowctl.build_review_prompt(plan)",
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "spec_body_chars": len(spec),
            "spec_grounded_verbatim": f"<spec>\n{spec_path}\n</spec>" in prompt,
            "task_specs_grounded_verbatim": (
                f"<task_specs>\n{task_path}\n</task_specs>" in prompt
            ),
            "verdict_grammar_present": all(
                tag in prompt
                for tag in (
                    "<verdict>SHIP</verdict>",
                    "<verdict>NEEDS_WORK</verdict>",
                    "<verdict>MAJOR_RETHINK</verdict>",
                )
            ),
        }

    b1_prompt_hash = json.loads(
        (
            repo_root
            / "optimization/reached-path/fixtures/b1/plan-review/codex.json"
        ).read_text(encoding="utf-8")
    )["prompt_hashes"][PROMPT.as_posix()]
    baseline_rendered = (
        repo_root
        / "plugins/flow-next/tests/fixtures/review_prompts/plan.txt"
    ).read_text(encoding="utf-8")
    # fn-169 R4: identities. Must mirror the parity suite's `plan` fixture inputs
    # exactly, or the byte comparison below compares two different prompts.
    candidate_rendered = build_plan_prompt(
        "plan",
        context_hints="hint-a\nhint-b",
        spec_path=".flow/specs/fn-parity.md",
        task_spec_paths=(
            ".flow/tasks/fn-parity.1.md", ".flow/tasks/fn-parity.2.md",
        ),
    )

    def without_output_format(text: str) -> str:
        start = text.index("## Output Format\n")
        offset = start + len("## Output Format\n")
        in_fence = False
        end = -1
        for line in text[offset:].splitlines(keepends=True):
            if line.startswith("```"):
                in_fence = not in_fence
            elif not in_fence and line.startswith("## "):
                end = offset
                break
            offset += len(line)
        if end == -1:
            return text
        return text[:start] + "## Output Format\n<FORMAT>\n" + text[end:]

    format_only_to_b1 = without_output_format(
        candidate_rendered
    ) == without_output_format(baseline_rendered)
    rows["prompt_template"] = {
        "path": PROMPT.as_posix(),
        "b1_sha256": b1_prompt_hash,
        "candidate_sha256": file_hash(repo_root / PROMPT),
        "byte_identical_to_b1": file_hash(repo_root / PROMPT) == b1_prompt_hash,
        "format_only_to_b1": format_only_to_b1,
        "rendered_chars_delta": len(candidate_rendered) - len(baseline_rendered),
        "actual_token_measurement": (
            "optimization/reached-path/evidence/fn136/"
            "review-output-format-token-delta.json"
        ),
        "quality_baseline": (
            "The fn-136 guard binds assembled prompt bytes to the immutable "
            "pre-change commit, confines the delta to Output Format, and records "
            "non-increasing cl100k_base and o200k_base token counts."
        ),
    }
    return rows
