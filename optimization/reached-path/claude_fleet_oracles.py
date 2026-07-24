"""Shared process, transcript, and workflow oracles for the Claude fleet smoke."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def sha_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def run(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    check: bool = True,
    input_text: str | None = None,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        input=input_text,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"command failed ({proc.returncode}): {' '.join(args)}\n"
            f"stdout={proc.stdout[-1000:]}\nstderr={proc.stderr[-1000:]}"
        )
    return proc


def flowctl(plugin: Path, repo: Path, *args: str, check: bool = True) -> str:
    proc = run(
        ["python3", str(plugin / "scripts" / "flowctl.py"), *args],
        cwd=repo,
        check=check,
    )
    return proc.stdout


def scrub(value: str, *, repo: Path, plugin: Path) -> str:
    replacements = sorted(
        (
            (str(repo), "<fixture-repo>"),
            (str(repo.resolve()), "<fixture-repo>"),
            (str(plugin), "<plugin-root>"),
            (str(plugin.resolve()), "<plugin-root>"),
            (str(Path.home()), "<home>"),
            (tempfile.gettempdir(), "<tmp>"),
        ),
        key=lambda item: len(item[0]),
        reverse=True,
    )
    result = value
    for old, new in replacements:
        result = result.replace(old, new)
    return result


def parse_stream(
    stream_path: Path, *, expected_plugin: Path, repo: Path, case: str
) -> dict[str, Any]:
    events = [json.loads(line) for line in stream_path.read_text().splitlines() if line]
    init = next(
        event
        for event in events
        if event.get("type") == "system" and event.get("subtype") == "init"
    )
    flow_plugins = [
        plugin for plugin in init.get("plugins", []) if plugin.get("name") == "flow-next"
    ]
    tool_calls: list[dict[str, Any]] = []
    skill_names: list[str] = []
    flow_reads: list[str] = []
    assistant_text: list[str] = []
    for event in events:
        if event.get("type") != "assistant":
            continue
        for item in event.get("message", {}).get("content", []):
            if item.get("type") == "text" and item.get("text"):
                assistant_text.append(str(item["text"]))
            if item.get("type") != "tool_use":
                continue
            name = str(item.get("name"))
            input_value = item.get("input") or {}
            if name == "Skill":
                skill_names.append(str(input_value.get("skill", "")))
            path = str(input_value.get("file_path", ""))
            if name == "Read" and "flow-next" in path:
                flow_reads.append(path)
            tool_calls.append(
                {
                    "name": name,
                    "input": scrub(
                        json.dumps(input_value, sort_keys=True),
                        repo=repo,
                        plugin=expected_plugin,
                    ),
                }
            )
    result = next(event for event in reversed(events) if event.get("type") == "result")
    usage = result.get("usage") or {}
    total_usage = sum(
        int(usage.get(key, 0) or 0)
        for key in (
            "input_tokens",
            "cache_creation_input_tokens",
            "cache_read_input_tokens",
            "output_tokens",
        )
    )
    expected_skills = {
        f"flow-next:flow-next-{case}",
        f"flow-next:{case}",
    }
    checks = {
        "single_inline_flow_plugin": len(flow_plugins) == 1
        and Path(flow_plugins[0].get("path", "")).resolve() == expected_plugin.resolve()
        and flow_plugins[0].get("source") == "flow-next@inline",
        "skill_invoked": bool(expected_skills.intersection(skill_names)),
        "nonzero_usage": total_usage > 0,
        "successful_turn": result.get("subtype") == "success"
        and result.get("is_error") is not True,
        "flow_reads_from_expected_root": all(
            Path(path).resolve().is_relative_to(expected_plugin.resolve())
            for path in flow_reads
        ),
    }
    return {
        "checks": checks,
        "skill_names": skill_names,
        "flow_reads": [
            scrub(path, repo=repo, plugin=expected_plugin) for path in flow_reads
        ],
        "tool_calls": tool_calls,
        "assistant_text": scrub(
            "\n".join(assistant_text), repo=repo, plugin=expected_plugin
        ),
        "result": scrub(
            str(result.get("result", "")), repo=repo, plugin=expected_plugin
        ),
        "usage": usage,
        "session_id": result.get("session_id"),
    }


def case_checks(
    case: str,
    parsed: dict[str, Any],
    *,
    repo: Path,
    plugin: Path,
    context: dict[str, Any],
    before_status: str,
) -> dict[str, bool]:
    result = parsed["result"].lower()
    transcript = f"{parsed.get('assistant_text', '')}\n{parsed['result']}".lower()
    status = run(["git", "status", "--short"], cwd=repo).stdout
    checks: dict[str, bool] = {}
    if case == "setup":
        checks["flow_initialized"] = (repo / ".flow" / "meta.json").is_file()
        instructions_written = any(
            (repo / name).is_file() for name in ("CLAUDE.md", "AGENTS.md")
        )
        checks["configuration_reached"] = instructions_written or (
            "setup mode" in transcript and "review backend" in transcript
        )
    elif case == "tracker-sync":
        checks["inactive_noop"] = any(
            token in result for token in ("inactive", "no-op", "noop", "not configured")
        )
        checks["no_tracker_receipt_write"] = not (repo / ".flow" / "sync-runs").exists()
    elif case == "prime":
        checks["classification_emitted"] = (
            "classification" in result
            or ("assessment_scope:" in result and "lifecycle:" in result)
        )
        checks["classify_only_terminal"] = any(
            token in result
            for token in (
                "classify-only",
                "classification only",
                "classification complete",
                "exiting",
            )
        )
    elif case == "plan":
        tasks = json.loads(
            flowctl(plugin, repo, "tasks", "--spec", context["spec_id"], "--json")
        )
        task_rows = tasks.get("tasks", tasks if isinstance(tasks, list) else [])
        checks["tasks_created"] = len(task_rows) >= 1
        checks["copy_drift_surfaced"] = any(
            token in transcript
            for token in (
                "differs from plugin",
                "version drift",
                "version mismatch",
                "refresh before planning",
                "run `/flow-next:setup`",
            )
        )
    elif case == "plan-review":
        spec_id = context["spec_id"]
        spec = json.loads((repo / ".flow" / "specs" / f"{spec_id}.json").read_text())
        checks["export_terminal"] = "export" in result
        checks["review_status_unchanged"] = spec.get("plan_review_status") != "ship"
        checks["no_review_subprocess"] = not any(
            call["name"] == "Bash"
            and re.search(r"(codex|copilot|cursor).*plan-review", call["input"])
            for call in parsed["tool_calls"]
        )
    elif case == "work":
        marker = repo / "result.txt"
        checks["marker_written"] = (
            marker.is_file() and marker.read_text().strip() == "FLEET_SMOKE_OK"
        )
        task = json.loads(flowctl(plugin, repo, "show", context["task_id"], "--json"))
        checks["task_done"] = task.get("status") == "done"
    elif case == "strategy":
        strategy = repo / "STRATEGY.md"
        checks["foreign_file_unchanged"] = (
            strategy.is_file()
            and sha_text(strategy.read_text()) == context["strategy_before"]
        )
        checks["choice_surfaced"] = any(
            token in result for token in ("foreign", "keep", "unchanged", "choose")
        )
    elif case == "make-pr":
        rendered_calls = "\n".join(call["input"] for call in parsed["tool_calls"])
        checks["body_rendered"] = (
            ("BEGIN PR BODY" in rendered_calls or "# Make PR plugin smoke" in rendered_calls)
            and "## Verification" in rendered_calls
            and "## Review plan" in rendered_calls
        )
        checks["no_live_pr_create"] = not any(
            call["name"] == "Bash" and "gh pr create" in call["input"]
            for call in parsed["tool_calls"]
        )
    elif case == "pilot":
        checks["terminal_verdict"] = "pilot_verdict=" in result
        checks["dry_run_no_repo_change"] = status == before_status
    return checks
