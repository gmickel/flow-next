#!/usr/bin/env python3
"""Real Claude plugin invocation smoke for the fn-130 optimized skill fleet."""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_fleet_oracles import case_checks, flowctl, parse_stream, run, scrub, sha_text

REPO = Path(__file__).resolve().parents[2]
B1 = "8ed71a73ccc593a8a018dcdb805a86f396dcf76f"
EVIDENCE = Path(__file__).resolve().parent / "evidence" / "fn130"
OUT = EVIDENCE / "claude-plugin-fleet-smoke.json"
CASES = (
    "setup",
    "tracker-sync",
    "prime",
    "plan",
    "plan-review",
    "work",
    "strategy",
    "make-pr",
    "pilot",
)
VARIANTS = ("b1", "candidate")


def init_git(repo: Path) -> None:
    run(["git", "init", "-q", "-b", "main"], cwd=repo)
    run(["git", "config", "user.name", "Flow Next Smoke"], cwd=repo)
    run(["git", "config", "user.email", "smoke@example.invalid"], cwd=repo)


def commit_all(repo: Path, message: str, *, allow_empty: bool = False) -> None:
    run(["git", "add", "."], cwd=repo)
    cmd = ["git", "commit", "-qm", message]
    if allow_empty:
        cmd.insert(2, "--allow-empty")
    run(cmd, cwd=repo)


def init_flow(plugin: Path, repo: Path) -> None:
    flowctl(plugin, repo, "init")


def create_spec(plugin: Path, repo: Path, title: str) -> str:
    payload = json.loads(
        flowctl(plugin, repo, "spec", "create", "--title", title, "--json")
    )
    return str(payload["id"])


def write_plan(plugin: Path, repo: Path, spec_id: str, *, detailed: bool = True) -> None:
    body = f"""# Fleet smoke plan

## Goal
Create a deterministic marker file in this disposable repository.

## Approach
{"Write `result.txt` containing exactly `FLEET_SMOKE_OK` and verify it." if detailed else "Implementation details intentionally pending."}

## Acceptance Criteria
- **R1:** `result.txt` exists and contains exactly `FLEET_SMOKE_OK`.

## Requirement coverage
| Req | Description | Task(s) | Gap justification |
|---|---|---|---|
| R1 | Deterministic marker | {spec_id}.1 | — |
"""
    path = repo / "plan.md"
    path.write_text(body)
    flowctl(plugin, repo, "spec", "set-plan", spec_id, "--file", str(path), "--json")
    path.unlink()


def create_task(plugin: Path, repo: Path, spec_id: str) -> str:
    payload = json.loads(
        flowctl(
            plugin,
            repo,
            "task",
            "create",
            "--spec",
            spec_id,
            "--title",
            "Write deterministic marker",
            "--satisfies",
            "R1",
            "--json",
        )
    )
    task_id = str(payload["id"])
    task_body = f"""---
satisfies: [R1]
---
# {task_id} Write deterministic marker

## Description
Create `result.txt` containing exactly `FLEET_SMOKE_OK`.

## Acceptance
- [ ] `result.txt` exists
- [ ] Its complete contents are `FLEET_SMOKE_OK`

## Quick commands
```bash
test "$(cat result.txt)" = FLEET_SMOKE_OK
```
"""
    task_path = repo / "task.md"
    task_path.write_text(task_body)
    flowctl(plugin, repo, "task", "set-spec", task_id, "--file", str(task_path))
    task_path.unlink()
    return task_id


def fixture_setup(plugin: Path, repo: Path) -> dict[str, Any]:
    return {
        "command": "/flow-next:setup mode:autonomous",
        "env": {"FLOW_AUTONOMOUS": "1"},
    }


def fixture_tracker(plugin: Path, repo: Path) -> dict[str, Any]:
    init_flow(plugin, repo)
    return {
        "command": "/flow-next:tracker-sync reconcile mode:autonomous",
        "env": {"FLOW_AUTONOMOUS": "1"},
    }


def fixture_prime(plugin: Path, repo: Path) -> dict[str, Any]:
    init_flow(plugin, repo)
    (repo / "README.md").write_text("# Fleet Smoke\n")
    return {"command": "/flow-next:prime --classify-only", "env": {}}


def fixture_plan(plugin: Path, repo: Path) -> dict[str, Any]:
    init_flow(plugin, repo)
    spec_id = create_spec(plugin, repo, "Plan plugin smoke")
    write_plan(plugin, repo, spec_id, detailed=False)
    meta = json.loads((repo / ".flow" / "meta.json").read_text())
    meta["setup_mode"] = "copy"
    meta["setup_version"] = "0.0.1"
    (repo / ".flow" / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    return {
        "command": f"/flow-next:plan {spec_id} mode:autonomous --review=none",
        "env": {"FLOW_AUTONOMOUS": "1"},
        "spec_id": spec_id,
    }


def fixture_plan_review(plugin: Path, repo: Path) -> dict[str, Any]:
    init_flow(plugin, repo)
    spec_id = create_spec(plugin, repo, "Plan review plugin smoke")
    write_plan(plugin, repo, spec_id)
    create_task(plugin, repo, spec_id)
    return {
        "command": f"/flow-next:plan-review {spec_id} --review=export",
        "env": {},
        "spec_id": spec_id,
    }


def fixture_work(plugin: Path, repo: Path) -> dict[str, Any]:
    init_flow(plugin, repo)
    spec_id = create_spec(plugin, repo, "Work plugin smoke")
    write_plan(plugin, repo, spec_id)
    task_id = create_task(plugin, repo, spec_id)
    return {
        "command": f"/flow-next:work {task_id} mode:autonomous",
        "env": {"FLOW_AUTONOMOUS": "1"},
        "spec_id": spec_id,
        "task_id": task_id,
    }


def fixture_strategy(plugin: Path, repo: Path) -> dict[str, Any]:
    init_flow(plugin, repo)
    foreign = """# Existing strategy

This file belongs to another strategy system. Keep it unchanged.
"""
    (repo / "STRATEGY.md").write_text(foreign)
    return {
        "command": "/flow-next:strategy",
        "env": {},
        "strategy_before": sha_text(foreign),
    }


def fixture_make_pr(plugin: Path, repo: Path) -> dict[str, Any]:
    init_flow(plugin, repo)
    spec_id = create_spec(plugin, repo, "Make PR plugin smoke")
    write_plan(plugin, repo, spec_id)
    task_id = create_task(plugin, repo, spec_id)
    commit_all(repo, "test: base fixture")
    run(["git", "switch", "-qc", spec_id], cwd=repo)
    (repo / "result.txt").write_text("FLEET_SMOKE_OK\n")
    run(["git", "add", "result.txt"], cwd=repo)
    run(["git", "commit", "-qm", "feat: add marker"], cwd=repo)
    flowctl(plugin, repo, "start", task_id, "--json")
    flowctl(
        plugin,
        repo,
        "done",
        task_id,
        "--summary",
        "Marker implemented.",
        "--evidence",
        '{"commits":["HEAD"],"tests":["test marker"],"prs":[]}',
        "--json",
    )
    commit_all(repo, "chore: complete task")
    return {
        "command": f"/flow-next:make-pr {spec_id} --dry-run --base main --no-mermaid",
        "env": {"FLOW_AUTONOMOUS": "1"},
        "spec_id": spec_id,
    }


def fixture_pilot(plugin: Path, repo: Path) -> dict[str, Any]:
    init_flow(plugin, repo)
    spec_id = create_spec(plugin, repo, "Pilot plugin smoke")
    write_plan(plugin, repo, spec_id)
    create_task(plugin, repo, spec_id)
    flowctl(plugin, repo, "spec", "ready", spec_id, "--json")
    return {
        "command": f"/flow-next:pilot --spec {spec_id} --dry-run",
        "env": {"FLOW_AUTONOMOUS": "1"},
        "spec_id": spec_id,
    }


BUILDERS: dict[str, Callable[[Path, Path], dict[str, Any]]] = {
    "setup": fixture_setup,
    "tracker-sync": fixture_tracker,
    "prime": fixture_prime,
    "plan": fixture_plan,
    "plan-review": fixture_plan_review,
    "work": fixture_work,
    "strategy": fixture_strategy,
    "make-pr": fixture_make_pr,
    "pilot": fixture_pilot,
}


def run_case(
    case: str,
    variant: str,
    plugin: Path,
    work_root: Path,
    model: str,
) -> dict[str, Any]:
    repo = work_root / f"{variant}-{case}"
    repo.mkdir()
    init_git(repo)
    context = BUILDERS[case](plugin, repo)
    if not (repo / ".git" / "HEAD").is_file():
        raise RuntimeError(f"{variant}/{case}: fixture git init failed")
    if run(["git", "rev-parse", "--verify", "HEAD"], cwd=repo, check=False).returncode:
        commit_all(repo, "test: fixture", allow_empty=True)
    else:
        status = run(["git", "status", "--porcelain"], cwd=repo).stdout
        if status:
            commit_all(repo, "test: fixture state")
    before_status = run(["git", "status", "--short"], cwd=repo).stdout
    stream_path = work_root / f"{variant}-{case}.jsonl"
    debug_path = work_root / f"{variant}-{case}.debug.log"
    isolation = (
        f"The only Flow-Next plugin allowed for this evaluation is {plugin}. "
        "Invoke the requested Skill tool normally. If the skill launcher requires "
        "you to read its markdown, use only that exact plugin root. Never search "
        "for or read any installed/cached Flow-Next copy. Execute the skill rather "
        "than merely describing it. This is a disposable repository."
    )
    if case == "plan-review":
        isolation += (
            f" For the export destination only, write beneath {repo}/.harness-output "
            "instead of ~/Desktop, and do not open a GUI application."
        )
    env = os.environ.copy()
    env.update(context.get("env", {}))
    env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"
    cmd = [
        "claude",
        "-p",
        "--setting-sources",
        "",
        "--strict-mcp-config",
        "--mcp-config",
        '{"mcpServers":{}}',
        "--plugin-dir",
        str(plugin),
        "--append-system-prompt",
        isolation,
        "--permission-mode",
        "bypassPermissions",
        "--model",
        model,
        "--output-format",
        "stream-json",
        "--verbose",
        "--debug-file",
        str(debug_path),
        "--no-session-persistence",
        context["command"],
    ]
    started = dt.datetime.now(dt.timezone.utc)
    proc = run(cmd, cwd=repo, env=env, check=False, timeout=900)
    stream_path.write_text(proc.stdout)
    parsed = parse_stream(stream_path, expected_plugin=plugin, repo=repo, case=case)
    checks = dict(parsed.pop("checks"))
    checks["claude_exit_zero"] = proc.returncode == 0
    checks.update(
        case_checks(
            case,
            parsed,
            repo=repo,
            plugin=plugin,
            context=context,
            before_status=before_status,
        )
    )
    duration = (dt.datetime.now(dt.timezone.utc) - started).total_seconds()
    row = {
        "id": f"{variant}-{case}",
        "variant": variant,
        "case": case,
        "command": context["command"],
        "plugin_root_sha256": sha_text(
            "\n".join(
                f"{path.relative_to(plugin)}:{hashlib.sha256(path.read_bytes()).hexdigest()}"
                for path in sorted(plugin.rglob("*"))
                if path.is_file()
            )
        ),
        "checks": checks,
        "pass": all(checks.values()),
        "duration_seconds": round(duration, 3),
        "stderr": scrub(proc.stderr[-2000:], repo=repo, plugin=plugin),
        "repo_status_before": before_status,
        "repo_status_after": run(["git", "status", "--short"], cwd=repo).stdout,
        "head": run(["git", "log", "-5", "--pretty=%h %s"], cwd=repo).stdout,
        **parsed,
    }
    print(
        f"{row['id']}: {'PASS' if row['pass'] else 'FAIL'} ({duration:.1f}s)",
        flush=True,
    )
    return row


def materialize_b1(root: Path) -> Path:
    archive = root / "b1.tar"
    with archive.open("wb") as handle:
        proc = subprocess.run(
            ["git", "archive", "--format=tar", B1, "plugins/flow-next"],
            cwd=REPO,
            stdout=handle,
        )
    if proc.returncode != 0:
        raise RuntimeError("could not materialize B1 plugin")
    run(["tar", "-xf", str(archive)], cwd=root)
    return root / "plugins" / "flow-next"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--case", choices=CASES, action="append")
    parser.add_argument("--variant", choices=VARIANTS, action="append")
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--keep-workdir", action="store_true")
    parser.add_argument(
        "--merge-existing",
        action="store_true",
        help="replace selected rows in the existing full evidence artifact",
    )
    args = parser.parse_args()
    cases = tuple(args.case or CASES)
    variants = tuple(args.variant or VARIANTS)

    work_root = Path(tempfile.mkdtemp(prefix="fn130-claude-fleet-"))
    try:
        plugins = {
            "b1": materialize_b1(work_root),
            "candidate": REPO / "plugins" / "flow-next",
        }
        jobs = [
            (case, variant, plugins[variant])
            for variant in variants
            for case in cases
        ]
        rows: list[dict[str, Any]] = []
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=max(1, args.workers)
        ) as pool:
            futures = {
                pool.submit(
                    run_case, case, variant, plugin, work_root, args.model
                ): (case, variant)
                for case, variant, plugin in jobs
            }
            for future in concurrent.futures.as_completed(futures):
                case, variant = futures[future]
                try:
                    rows.append(future.result())
                except Exception as exc:
                    print(f"{variant}-{case}: ERROR {exc}", flush=True)
                    rows.append(
                        {
                            "id": f"{variant}-{case}",
                            "variant": variant,
                            "case": case,
                            "checks": {"harness_completed": False},
                            "pass": False,
                            "error": str(exc),
                        }
                    )
        if args.merge_existing:
            if not OUT.is_file():
                raise RuntimeError("--merge-existing requires an existing evidence artifact")
            existing = json.loads(OUT.read_text()).get("rows", [])
            replaced_ids = {row["id"] for row in rows}
            rows.extend(row for row in existing if row["id"] not in replaced_ids)
        rows.sort(key=lambda row: row["id"])
        parity_cases = tuple(sorted({row["case"] for row in rows}))
        parity = {
            case: {
                "b1_pass": next(
                    row["pass"]
                    for row in rows
                    if row["case"] == case and row["variant"] == "b1"
                )
                if "b1" in variants
                else None,
                "candidate_pass": next(
                    row["pass"]
                    for row in rows
                    if row["case"] == case and row["variant"] == "candidate"
                )
                if "candidate" in variants
                else None,
            }
            for case in parity_cases
        }
        candidate_rows = [row for row in rows if row["variant"] == "candidate"]
        promotion_pass = bool(candidate_rows) and all(row["pass"] for row in candidate_rows)
        artifact = {
            "schema_version": 1,
            "date_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "lineage": f"{B1} -> {run(['git', 'rev-parse', 'HEAD'], cwd=REPO).stdout.strip()}",
            "claude_version": run(["claude", "--version"], cwd=REPO).stdout.strip(),
            "model": args.model,
            "invocation": "real /flow-next:* Skill via claude --plugin-dir",
            "isolation": {
                "setting_sources": [],
                "strict_empty_mcp": True,
                "inline_plugin_must_override_installed": True,
                "flow_skill_reads_limited_to_expected_root": True,
                "safe_mode_rejected": "safe mode disables plugin skills",
            },
            "promotion_criterion": "all candidate workflows pass; B1 misses remain visible",
            "promotion_pass": promotion_pass,
            "parity": parity,
            "rows": rows,
        }
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(artifact, indent=2) + "\n")
        passed = promotion_pass if candidate_rows else all(row["pass"] for row in rows)
        print(f"evidence -> {OUT.relative_to(REPO)}")
        print(f"rows={len(rows)} pass={sum(row['pass'] for row in rows)}")
        return 0 if passed else 1
    finally:
        if args.keep_workdir:
            print(f"workdir retained: {work_root}")
        else:
            shutil.rmtree(work_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
