#!/usr/bin/env python3
"""Measure omission-only sparse inputs, proving identity with flowctl expansion."""

import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "plugins/flow-next/scripts"))
SPEC = importlib.util.spec_from_file_location(
    "flowctl", ROOT / "plugins/flow-next/scripts/flowctl.py"
)
flowctl = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = flowctl
SPEC.loader.exec_module(flowctl)
FIELDS = (
    "changeType", "additions", "deletions", "diffUrl",
    "sourceRefs", "rIds", "taskIds", "attentionClass",
)


def encoded(value):
    return flowctl._pr_aid_serialized_text(value).encode("utf-8")


def historical_diff(artifact):
    """Keep flowctl's diff flags/parser, substituting the recorded head for HEAD."""
    base, head = artifact["baseSha"], artifact["headSha"]
    run_git = flowctl._export_run_git

    def at_head(args, **kwargs):
        args = [head if arg == "HEAD" else
                f"{base}..{head}" if arg == f"{base}..HEAD" else arg
                for arg in args]
        return run_git(args, **kwargs)

    try:
        with patch.object(flowctl, "_export_run_git", side_effect=at_head):
            return flowctl._pr_aid_live_diff_files(ROOT, base, head), None
    except flowctl.PrCognitiveAidValidationError as error:
        return None, str(error)


def measure(path, diff_cache):
    raw = (ROOT / path).read_text(encoding="utf-8")
    complete = json.loads(raw)
    target = encoded(complete)
    sparse = copy.deepcopy(complete)
    key = (complete["baseSha"], complete["headSha"])
    if key not in diff_cache:
        diff_cache[key] = historical_diff(complete)
    metadata, unavailable = diff_cache[key]
    saved = dict.fromkeys((*FIELDS, "wholeRows"), 0)
    counts = dict.fromkeys(saved, 0)

    def identical(candidate):
        errors = []
        expanded = flowctl._expand_pr_cognitive_aid_input(
            candidate, metadata, _errors=errors
        )
        return not errors and encoded(expanded) == target

    result = {
        "path": path, "diskBytes": len(raw.encode("utf-8")),
        "completeBytes": len(target), "diffUnavailable": unavailable,
    }
    if not identical(sparse):
        # Never manufacture metadata or rewrite old artifacts to make them fit.
        result["limit"] = "complete input itself does not expand identically"
        errors = []
        expanded = flowctl._expand_pr_cognitive_aid_input(
            complete, metadata, _errors=errors
        )
        result["expansionErrors"] = errors
        result["addedFields"] = {}
        for before_group, after_group in zip(
            complete["changeWalkthrough"]["groups"],
            expanded["changeWalkthrough"]["groups"], strict=True,
        ):
            for before_row, after_row in zip(before_group["files"], after_group["files"], strict=False):
                for field in sorted(after_row.keys() - before_row.keys()):
                    result["addedFields"][field] = result["addedFields"].get(field, 0) + 1
        result["addedRows"] = sum(
            len(group["files"]) for group in expanded["changeWalkthrough"]["groups"]
        ) - sum(len(group["files"]) for group in complete["changeWalkthrough"]["groups"])
    else:
        groups = sparse["changeWalkthrough"]["groups"]
        # Generated rows append to the final available step. Reverse traversal
        # removes suffix rows first so ordered reconstruction remains possible.
        # Repeat because freeing a slot can enable a previously rejected omission.
        changed = True
        while changed:
            changed = False
            for group in reversed(groups):
                for index in range(len(group["files"]) - 1, -1, -1):
                    row = group["files"][index]
                    if row.get("summary") != "" or metadata is None:
                        continue
                    before = len(encoded(sparse))
                    del group["files"][index]
                    if identical(sparse):
                        saved["wholeRows"] += before - len(encoded(sparse))
                        counts["wholeRows"] += 1
                        changed = True
                    else:
                        group["files"].insert(index, row)
        for group in groups:
            for row in group["files"]:
                for field in FIELDS:
                    if field not in row:
                        continue
                    before = len(encoded(sparse))
                    value = row.pop(field)
                    if identical(sparse):
                        saved[field] += before - len(encoded(sparse))
                        counts[field] += 1
                    else:
                        row[field] = value
        if not identical(sparse):
            raise RuntimeError(f"identity proof failed: {path}")
    result.update(sparseBytes=len(encoded(sparse)), savedBytes=saved, omitted=counts)
    assert sum(saved.values()) == len(target) - result["sparseBytes"]
    return result


def main():
    # Historical objects must already be local, even in a partial clone.
    os.environ["GIT_NO_LAZY_FETCH"] = "1"
    paths = subprocess.run(
        ["git", "ls-files", "-z", ".flow/artifacts"], cwd=ROOT,
        check=True, capture_output=True, encoding="utf-8",
    ).stdout.split("\0")
    paths = sorted(path for path in paths
                   if "/pr-cognitive-aid/" in path and path.endswith(".json"))
    cache = {}
    rows = [measure(path, cache) for path in paths]
    complete = sum(row["completeBytes"] for row in rows)
    sparse = sum(row["sparseBytes"] for row in rows)
    report = {
        "artifacts": len(rows), "diskBytes": sum(row["diskBytes"] for row in rows),
        "completeBytes": complete, "sparseBytes": sparse,
        "savedBytes": complete - sparse,
        "reductionPercent": round(100 * (complete - sparse) / complete, 4) if complete else 0,
        "diffUnavailable": sum(row["diffUnavailable"] is not None for row in rows),
        "identityUnavailable": sum("limit" in row for row in rows),
        "unchangedArtifacts": sum(row["completeBytes"] == row["sparseBytes"] for row in rows),
        "fields": {field: {
            "omitted": sum(row["omitted"][field] for row in rows),
            "savedBytes": sum(row["savedBytes"][field] for row in rows),
        } for field in (*FIELDS, "wholeRows")},
        "records": rows,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
