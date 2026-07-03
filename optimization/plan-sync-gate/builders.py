#!/usr/bin/env python3
"""Deterministic scenario builders for the plan-sync gate corpus (fn-83.2).

Two scenario kinds, both driven by `scenarios.json` (APPEND-ONLY — see README):

- **fixture** — constructed drift-POSITIVE repos. Built from the declarative
  `FIXTURES` table below: tiny git repo + `.flow` state + a completed task
  whose implementation drifted from its spec in a specific, documented way.
  Fully deterministic (pinned author/committer dates ⇒ identical SHAs
  everywhere).

- **replay** — drift-NEGATIVE states replayed from this repository's real
  history via `git worktree add --detach <full-SHA>` (post-task states of
  fn-74/78/81/82 runs whose production plan-sync verdicts were "no drift").
  Runtime task state (status=done + evidence) was never committed — it lives
  in git-common-dir/flow-state — so it is RECONSTRUCTED from the pinned
  base/head SHAs into an isolated FLOW_STATE_DIR (the documented orchestrator
  override). NEVER probe a replay without FLOW_STATE_DIR: the state store is
  shared across worktrees and you would read/mutate the live repo's state.

HISTORICAL (fn-83.4): the CI check (test_plan_sync_gate_corpus.py) that
imported this module was removed together with `flowctl plan-sync-probe`
when the skip-gate was proven non-viable (fn-83.6 cross-repo verdict FAIL;
see the README's ARCHIVED banner and the fn-83 decision record). This module
needs the removed probe to run — recover both via git history if ever
needed. The frozen LLM answer key (answer-key.json) remains valid archived
evidence.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

HARNESS_DIR = Path(__file__).resolve().parent
REPO_ROOT = HARNESS_DIR.parents[1]
FLOWCTL_PY = REPO_ROOT / "plugins" / "flow-next" / "scripts" / "flowctl.py"
SCENARIOS_PATH = HARNESS_DIR / "scenarios.json"
ANSWER_KEY_PATH = HARNESS_DIR / "answer-key.json"

# Canonical repo for replay-SHA fetches — fork-survivable fallback: a fork's
# `origin` does not carry the base repo's refs/pull/* history.
CANONICAL_REMOTE = "https://github.com/gmickel/flow-next.git"

# Pinned dates make constructed-fixture commit SHAs identical on every
# machine/OS — the answer key and probe results are reproducible bit-for-bit.
_FIXED_GIT_ENV = {
    "GIT_AUTHOR_NAME": "gate-corpus",
    "GIT_AUTHOR_EMAIL": "gate-corpus@flow-next.test",
    "GIT_COMMITTER_NAME": "gate-corpus",
    "GIT_COMMITTER_EMAIL": "gate-corpus@flow-next.test",
    "GIT_AUTHOR_DATE": "2026-07-03T00:00:00 +0000",
    "GIT_COMMITTER_DATE": "2026-07-03T00:00:00 +0000",
}


def _run(
    cmd: list, cwd: Path, env: Optional[dict] = None, check: bool = True
) -> subprocess.CompletedProcess:
    """rc-checked subprocess (list argv, no shell, no pipelines)."""
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    result = subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True,
        encoding="utf-8", env=full_env,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            "command failed (rc=%d): %s\nstderr: %s"
            % (result.returncode, " ".join(cmd), (result.stderr or "").strip())
        )
    return result


def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return _run(["git"] + list(args), cwd=cwd, env=_FIXED_GIT_ENV, check=check)


def load_scenarios() -> list:
    data = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
    return data["scenarios"]


def load_answer_key() -> dict:
    return json.loads(ANSWER_KEY_PATH.read_text(encoding="utf-8"))


# ── Replay materialization ────────────────────────────────────────────────


def ensure_commit_available(sha: str, pr_ref: Optional[str]) -> None:
    """Make `sha` resolvable in REPO_ROOT, fetching if necessary.

    Chain: local object → `git fetch origin <sha>` → fetch the PR head ref
    from origin → both again from the canonical repo URL (fork-survivable).
    Raises with a reproduction hint when nothing works — the CI check FAILS
    rather than skipping (a silently shrunk corpus would weaken the gate).
    """
    if _git(REPO_ROOT, "rev-parse", "--verify", "--quiet", sha + "^{commit}",
            check=False).returncode == 0:
        return
    attempts = [
        ["fetch", "--quiet", "origin", sha],
        ["fetch", "--quiet", "origin", pr_ref] if pr_ref else None,
        ["fetch", "--quiet", CANONICAL_REMOTE, sha],
        ["fetch", "--quiet", CANONICAL_REMOTE, pr_ref] if pr_ref else None,
    ]
    for attempt in attempts:
        if attempt is None:
            continue
        _git(REPO_ROOT, *attempt, check=False)
        if _git(REPO_ROOT, "rev-parse", "--verify", "--quiet",
                sha + "^{commit}", check=False).returncode == 0:
            return
    raise RuntimeError(
        "replay commit %s unavailable (tried origin + %s, ref %s); "
        "run `git fetch %s %s` manually"
        % (sha, CANONICAL_REMOTE, pr_ref, CANONICAL_REMOTE, pr_ref or sha)
    )


def _write_state(state_dir: Path, task_id: str, base: str, commits: list,
                 done_siblings: Optional[list] = None) -> None:
    """Reconstruct runtime state: completed task + already-done siblings.

    Committed task DEFINITIONS carry a stale legacy `status: todo` (real
    statuses lived in the uncommitted state store — the documented
    'uncommitted state unrecoverable' limitation), so siblings that were
    done at the replayed moment must be marked done here or the probe would
    scan MORE bodies than production did.
    """
    tasks = state_dir / "tasks"
    tasks.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "done",
        "evidence": {
            "commits": commits,
            "tests": [],
            "prs": [],
            "base_commit": base,
        },
        "updated_at": "2026-07-03T00:00:00Z",
    }
    (tasks / (task_id + ".state.json")).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    for sibling in done_siblings or []:
        (tasks / (sibling + ".state.json")).write_text(
            json.dumps({"status": "done",
                        "updated_at": "2026-07-03T00:00:00Z"},
                       indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def _patch_config(repo: Path, cross_spec: bool) -> None:
    """Pin planSync config in the materialized repo to the scenario contract."""
    cfg_path = repo / ".flow" / "config.json"
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        cfg = {}
    plan_sync = cfg.get("planSync")
    if not isinstance(plan_sync, dict):
        plan_sync = {}
        cfg["planSync"] = plan_sync
    plan_sync["enabled"] = True
    plan_sync["crossSpec"] = cross_spec
    plan_sync["gate"] = "on"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(cfg, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")


def materialize_replay(scenario: dict, workdir: Path) -> dict:
    """Detached worktree at the pinned post-task SHA + isolated state dir."""
    ensure_commit_available(scenario["checkout"], scenario.get("pr_ref"))
    ensure_commit_available(scenario["base_commit"], scenario.get("pr_ref"))
    ensure_commit_available(scenario["head_commit"], scenario.get("pr_ref"))

    wt = workdir / (scenario["id"] + "-wt")
    _git(REPO_ROOT, "worktree", "add", "--detach", str(wt), scenario["checkout"])
    _patch_config(wt, scenario["cross_spec"])

    # Full commit list when connectivity allows (full clones); the probe only
    # consumes commits[-1] as head, so [head] is an equivalent minimal form on
    # shallow CI clones (base/head are the pinned range either way).
    listed = _git(wt, "rev-list", "--reverse",
                  scenario["base_commit"] + ".." + scenario["head_commit"],
                  check=False)
    commits = [c for c in listed.stdout.split("\n") if c.strip()] \
        if listed.returncode == 0 else []
    if not commits:
        commits = [scenario["head_commit"]]

    state_dir = workdir / (scenario["id"] + "-state")
    _write_state(state_dir, scenario["task"], scenario["base_commit"], commits,
                 done_siblings=scenario.get("done_siblings"))
    return {"cwd": wt, "state_dir": state_dir, "task": scenario["task"],
            "worktree": wt}


def cleanup_replay(materialized: dict) -> None:
    _git(REPO_ROOT, "worktree", "remove", "--force",
         str(materialized["worktree"]), check=False)
    _git(REPO_ROOT, "worktree", "prune", check=False)


# ── Constructed fixtures (drift-positive) ─────────────────────────────────
#
# Declarative table. Each fixture:
#   seed:  {path: content} committed as the pre-task state
#   work:  ordered commit steps: {"msg", "write": {path: content},
#          "mv": [[old, new]], "rm": [path]}
#   flow:  spec/task/downstream markdown + optional other_specs / glossary
# The executor then writes .flow, commits a production-shaped
# "chore(flow): mark <task> done" marker, and returns probe-ready metadata.
# `{head}` in the task markdown is substituted with the real head SHA.
# The declarative FIXTURES table + markdown scaffolds live in
# corpus_fixtures.py (same directory, importlib-loaded so the harness works
# regardless of how builders.py itself was imported).


def _load_corpus_fixtures():
    spec = importlib.util.spec_from_file_location(
        "plan_sync_gate_corpus_fixtures", HARNESS_DIR / "corpus_fixtures.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


_corpus_fixtures = _load_corpus_fixtures()
FIXTURES = _corpus_fixtures.FIXTURES
_SPEC_MD_TEMPLATE = _corpus_fixtures._SPEC_MD_TEMPLATE


def build_fixture(scenario: dict, workdir: Path) -> dict:
    """Build one constructed fixture repo. Deterministic (pinned git env)."""
    fx = FIXTURES[scenario["builder"]]
    repo = workdir / scenario["id"]
    repo.mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "core.autocrlf", "false")
    _git(repo, "config", "user.email", "gate-corpus@flow-next.test")
    _git(repo, "config", "user.name", "gate-corpus")

    def _write_files(files: dict) -> None:
        for rel, content in sorted(files.items()):
            path = repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            # 3.8-safe LF pin (write_text(newline=...) is 3.10+).
            with path.open("w", encoding="utf-8", newline="\n") as fh:
                fh.write(content)

    _write_files(fx["seed"])
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "seed: pre-task state")
    base = _git(repo, "rev-parse", "HEAD").stdout.strip()

    for step in fx["work"]:
        for old, new in step.get("mv", []):
            (repo / new).parent.mkdir(parents=True, exist_ok=True)
            _git(repo, "mv", old, new)
        for rel in step.get("rm", []):
            _git(repo, "rm", "-q", rel)
        _write_files(step.get("write", {}))
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", step["msg"])
    head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    listed = _git(repo, "rev-list", "--reverse", base + ".." + head)
    commits = [c for c in listed.stdout.split("\n") if c.strip()]

    # .flow state (production-shaped: spec + tasks committed by a trailing
    # done-marker commit, so the work range never contains them).
    flow = fx["flow"]
    spec_id, task_id = scenario["spec"], scenario["task"]
    flow_files = {
        ".flow/config.json": json.dumps({
            "memory": {"enabled": False},
            "planSync": {
                "enabled": True,
                "crossSpec": scenario["cross_spec"],
                "gate": "on",
            },
        }, indent=2, sort_keys=True) + "\n",
        ".flow/specs/%s.json" % spec_id: json.dumps(
            {"id": spec_id, "title": flow["spec_title"], "status": "open"},
            indent=2) + "\n",
        ".flow/specs/%s.md" % spec_id: _SPEC_MD_TEMPLATE.format(
            title=flow["spec_title"], overview=flow["spec_overview"],
            approach=flow["spec_approach"], r1=flow["spec_r1"]),
        ".flow/tasks/%s.json" % task_id: json.dumps(
            {"id": task_id, "spec": spec_id,
             "title": flow["spec_title"] + " — impl"}, indent=2) + "\n",
        ".flow/tasks/%s.md" % task_id: flow["task_md"].replace("{head}", head),
    }
    inv_map = fx.get("downstream_inv_targets", {})
    for ds_id, ds_md in flow["downstream"].items():
        if ds_id in inv_map:
            ds_md = ds_md.replace(
                "\n## Acceptance",
                "\n## Investigation targets\n\n" + inv_map[ds_id]
                + "\n\n## Acceptance", 1)
        flow_files[".flow/tasks/%s.json" % ds_id] = json.dumps(
            {"id": ds_id, "spec": spec_id, "title": ds_id,
             "depends_on": [task_id]}, indent=2) + "\n"
        flow_files[".flow/tasks/%s.md" % ds_id] = ds_md
    for other_id, (status, body) in fx["flow"].get("other_specs", {}).items():
        flow_files[".flow/specs/%s.json" % other_id] = json.dumps(
            {"id": other_id, "title": other_id, "status": status},
            indent=2) + "\n"
        flow_files[".flow/specs/%s.md" % other_id] = body
    _write_files(flow_files)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "chore(flow): mark %s done" % task_id)

    state_dir = workdir / (scenario["id"] + "-state")
    _write_state(state_dir, task_id, base, commits)
    return {"cwd": repo, "state_dir": state_dir, "task": task_id,
            "base": base, "head": head, "commits": commits}


def materialize(scenario: dict, workdir: Path) -> dict:
    if scenario["kind"] == "replay":
        return materialize_replay(scenario, workdir)
    return build_fixture(scenario, workdir)


def cleanup(scenario: dict, materialized: dict) -> None:
    if scenario["kind"] == "replay":
        cleanup_replay(materialized)


# ── Probe runner ──────────────────────────────────────────────────────────


def run_probe(materialized: dict, deviation: str) -> dict:
    """Run the CURRENT working-tree probe against a materialized scenario.

    FLOW_STATE_DIR isolation is mandatory: the default state store lives in
    git-common-dir/flow-state, which a replay worktree SHARES with the live
    checkout.
    """
    result = _run(
        [sys.executable, str(FLOWCTL_PY), "plan-sync-probe",
         materialized["task"], "--json", "--deviation", deviation],
        cwd=materialized["cwd"],
        env={"FLOW_STATE_DIR": str(materialized["state_dir"])},
    )
    return json.loads(result.stdout)


if __name__ == "__main__":
    # Manual smoke: probe every scenario on both arms, print a table.
    import tempfile

    for scenario in load_scenarios():
        with tempfile.TemporaryDirectory() as td:
            mat = materialize(scenario, Path(td))
            try:
                arms = {"truthful": scenario["truthful_deviation"], "adversarial": "no"}
                seen = {}
                for arm, dev in arms.items():
                    if arm == "adversarial" and scenario["intent"] != "positive":
                        continue
                    seen[arm] = run_probe(mat, dev)["decision"]
                print("%-28s %s" % (scenario["id"], seen))
            finally:
                cleanup(scenario, mat)
