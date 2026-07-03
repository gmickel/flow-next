#!/usr/bin/env python3
"""Cross-repo replay runner for the plan-sync gate ship-gate (fn-83.6).

Materializes pinned post-task states of EXTERNAL flow-managed repos
(DocIQ-Sphere / gno / transcribe) as detached read-only worktrees, probes
them with the CURRENT working-tree `flowctl plan-sync-probe`, and (maintainer
only) generates frozen answer keys with the REAL production plan-sync agent
per the fn-83.2 procedure (optimization/plan-sync-gate/README.md §Answer key).

READ-ONLY toward the external repos: the only writes are the detached
worktree itself (removed afterwards) and a planSync config patch INSIDE the
scratch worktree. Runtime state is reconstructed into an isolated
FLOW_STATE_DIR — the external repos' live state stores are never touched.

PRIVACY: external-repo file CONTENT never leaves the maintainer machine.
Committed artifacts are the scenario pointer table (repo path + task ids +
SHAs + derivation notes), aggregate results, and the verdict. Raw agent
outputs and key votes live in the maintainer-local KEYS_DIR.

Usage:
  python3 replay.py probe <scenarios.json> [--only <id>]      # deterministic
  python3 replay.py keygen <scenarios.json> --only <id> [--runs N]
  python3 replay.py prompt <scenarios.json> --only <id>       # print prompt
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# When run from the committed location optimization/plan-sync-gate/cross-repo/
# the flow-next repo root is three levels up; tolerate scratch use via env.
FLOW_NEXT_ROOT = Path(os.environ.get("FLOW_NEXT_ROOT",
                                     str(HERE.parents[2]))).resolve()
FLOWCTL_PY = FLOW_NEXT_ROOT / "plugins" / "flow-next" / "scripts" / "flowctl.py"
PLAN_SYNC_MD = FLOW_NEXT_ROOT / "plugins" / "flow-next" / "agents" / "plan-sync.md"
WORK_DIR = Path(os.environ.get("XREPO_WORK_DIR", "/tmp/fn83-xrepo-work"))
KEYS_DIR = Path(os.environ.get(
    "XREPO_KEYS_DIR",
    os.path.expanduser("~/work/flow-next-fn83-external")))

# Prefix-anchored per the fn-83.2 procedure; tolerates markdown emphasis
# wrappers the agent sometimes adds (`**Drift detected: yes**`).
VERDICT_RE = re.compile(r"^[*_]{0,3}Drift detected:[*_ ]*\s*(yes|no)\b",
                        re.MULTILINE | re.IGNORECASE)


def run(cmd, cwd=None, env=None, check=True, timeout=None):
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    r = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True,
                       text=True, encoding="utf-8", env=full_env,
                       timeout=timeout)
    if check and r.returncode != 0:
        raise RuntimeError("cmd failed rc=%d: %s\nstderr: %s"
                           % (r.returncode, " ".join(map(str, cmd)),
                              (r.stderr or "")[:400]))
    return r


def git(repo, *args, check=True):
    return run(["git", "-C", str(repo)] + list(args), check=check)


def load_scenarios(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))["scenarios"]


# ── Materialization ────────────────────────────────────────────────────────


def spec_members_at(repo, checkout, spec_id):
    """Task ids of `spec_id` present under .flow/tasks/ at `checkout`."""
    out = git(repo, "ls-tree", "--name-only", checkout, ".flow/tasks/").stdout
    members = set()
    for line in out.split("\n"):
        name = line.strip().rsplit("/", 1)[-1]
        if not name.endswith(".json"):
            continue
        tid = name[:-len(".json")]
        if tid.rsplit(".", 1)[0] == spec_id and "." in tid:
            members.add(tid)
    return sorted(members)


def write_state(state_dir, scenario, members):
    """Reconstruct runtime state for every spec member at the checkout.

    Contract fidelity: the probe's scanned-todo set must equal the pinned
    `downstream` list (what production would have passed as
    DOWNSTREAM_TASK_IDS). Completed task -> done + evidence (derived
    base_commit); pinned downstream -> todo; every other member -> done.
    Members outside the pinned lists are surfaced as a warning.
    """
    tasks = state_dir / "tasks"
    tasks.mkdir(parents=True, exist_ok=True)
    task_id = scenario["task"]
    downstream = set(scenario["downstream"])
    known = set(scenario.get("done_siblings", [])) | downstream | {task_id}
    unknown = [m for m in members if m not in known]

    repo = Path(scenario["repo"]).expanduser()
    listed = git(repo, "rev-list", "--reverse",
                 scenario["base_commit"] + ".." + scenario["head_commit"],
                 check=False)
    commits = [c for c in listed.stdout.split("\n") if c.strip()] \
        if listed.returncode == 0 else []
    if not commits:
        commits = [scenario["head_commit"]]

    for member in members:
        if member == task_id:
            payload = {"status": "done",
                       "evidence": {"commits": commits, "tests": [], "prs": [],
                                    "base_commit": scenario["base_commit"]},
                       "updated_at": "2026-07-03T00:00:00Z"}
        elif member in downstream:
            payload = {"status": "todo", "updated_at": "2026-07-03T00:00:00Z"}
        else:
            payload = {"status": "done", "updated_at": "2026-07-03T00:00:00Z"}
        (tasks / (member + ".state.json")).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
    return unknown


def patch_config(wt):
    """Pin planSync config inside the scratch worktree (never the live repo)."""
    cfg_path = wt / ".flow" / "config.json"
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        cfg = {}
    plan_sync = cfg.get("planSync")
    if not isinstance(plan_sync, dict):
        plan_sync = {}
        cfg["planSync"] = plan_sync
    plan_sync["enabled"] = True
    plan_sync["crossSpec"] = False   # replays pin the era contract (fn-83.2)
    plan_sync["gate"] = "on"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(cfg, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")


def materialize(scenario):
    repo = Path(scenario["repo"]).expanduser()
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    wt = WORK_DIR / (scenario["id"] + "-wt")
    if wt.exists():
        cleanup(scenario)
    git(repo, "worktree", "add", "--detach", str(wt), scenario["checkout"])
    patch_config(wt)
    members = spec_members_at(repo, scenario["checkout"], scenario["spec"])
    state_dir = WORK_DIR / (scenario["id"] + "-state")
    unknown = write_state(state_dir, scenario, members)
    return {"wt": wt, "state_dir": state_dir, "members": members,
            "unknown_members": unknown}


def cleanup(scenario):
    repo = Path(scenario["repo"]).expanduser()
    wt = WORK_DIR / (scenario["id"] + "-wt")
    git(repo, "worktree", "remove", "--force", str(wt), check=False)
    git(repo, "worktree", "prune", check=False)


# ── Probe ─────────────────────────────────────────────────────────────────


def probe(scenario, mat):
    r = run([sys.executable, str(FLOWCTL_PY), "plan-sync-probe",
             scenario["task"], "--json", "--deviation", "no"],
            cwd=mat["wt"], env={"FLOW_STATE_DIR": str(mat["state_dir"])})
    return json.loads(r.stdout)


# ── Answer-key prompt (fn-83.2 procedure, unchanged) ──────────────────────


def _flowctl_in(wt, *args, default):
    try:
        r = run([sys.executable, str(FLOWCTL_PY)] + list(args), cwd=wt,
                check=False)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    return default


def build_prompt(scenario, mat):
    wt = mat["wt"]
    glossary = _flowctl_in(wt, "glossary", "list", "--json",
                           default='{"groups":[],"file_count":0,"total_terms":0}')
    decisions = _flowctl_in(wt, "memory", "list", "--track", "knowledge",
                            "--category", "decisions", "--json",
                            default='{"entries":[],"count":0}')
    strategy = _flowctl_in(wt, "strategy", "read", "--json", default="{}")
    agent_md = PLAN_SYNC_MD.read_text(encoding="utf-8")
    return """Read the following agent definition as your COMPLETE operating instructions, then execute them against the repository at your current working directory.

<agent-definition>
%s
</agent-definition>

Input from prompt:
- COMPLETED_TASK_ID: %s
- SPEC_ID: %s
- FLOWCTL: (unavailable in this session — read the .flow/ files directly with Read/Grep/Glob; task specs are at .flow/tasks/<id>.md, task records at .flow/tasks/<id>.json, spec bodies at .flow/specs/<id>.md — or .flow/epics/<id>.md in older layouts)
- DOWNSTREAM_TASK_IDS: %s
- DRY_RUN: true
- CROSS_SPEC: false
- GLOSSARY_JSON: %s
- DECISIONS_JSON: %s
- STRATEGY_CONTENT: %s

Practical notes: you have read-only tools (Read, Grep, Glob) only — no Bash, no Write (DRY_RUN=true: report, never edit). The completed task's done summary may be absent from its markdown; in that case infer what was implemented from the repository content itself (per your Phase 1 instructions). End with the Phase 6 summary including the mandatory `Drift detected: yes|no` line.
""" % (agent_md, scenario["task"], scenario["spec"],
       ",".join(scenario["downstream"]), glossary, decisions, strategy)


def parse_verdict(text):
    matches = VERDICT_RE.findall(text or "")
    return matches[-1].lower() if matches else None


# ── Answer-key generation (fn-83.2 procedure; parallel across scenarios) ──


def spawn_vote(prompt_path, wt):
    stdin_fh = open(prompt_path, encoding="utf-8")
    proc = subprocess.Popen(
        ["claude", "-p", "--model", "opus",
         "--tools", "Read,Grep,Glob",
         "--output-format", "json"],
        stdin=stdin_fh, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, encoding="utf-8", cwd=str(wt))
    stdin_fh.close()  # child holds its own fd
    return proc


def keygen(scenarios, runs):
    """Materialize every scenario, launch all votes staggered, collect all.

    Cross-scenario parallel: total concurrent claude processes =
    len(scenarios) * runs (call this with small batches).
    """
    import time
    mats = {}
    for scenario in scenarios:
        mats[scenario["id"]] = materialize(scenario)
    try:
        jobs = []  # (scenario, run_no, proc)
        for scenario in scenarios:
            mat = mats[scenario["id"]]
            out_dir = KEYS_DIR / scenario["id"]
            out_dir.mkdir(parents=True, exist_ok=True)
            prompt = build_prompt(scenario, mat)
            prompt_path = out_dir / "prompt.md"
            prompt_path.write_text(prompt, encoding="utf-8")
            for n in range(1, runs + 1):
                jobs.append((scenario, n, spawn_vote(prompt_path, mat["wt"])))
                time.sleep(4)  # stagger launches
        votes_by_id = {}
        for scenario, n, proc in jobs:
            out_dir = KEYS_DIR / scenario["id"]
            try:
                out, err = proc.communicate(timeout=560)
            except subprocess.TimeoutExpired:
                proc.kill()
                out, err = proc.communicate()
            (out_dir / ("run-%d.json" % n)).write_text(out or "",
                                                       encoding="utf-8")
            if err and err.strip():
                (out_dir / ("run-%d.stderr.txt" % n)).write_text(
                    err, encoding="utf-8")
            verdict = None
            model_id = None
            try:
                payload = json.loads(out)
                verdict = parse_verdict(payload.get("result", ""))
                mu = payload.get("modelUsage") or {}
                model_id = next(iter(mu.keys()), None) or payload.get("model")
            except (json.JSONDecodeError, TypeError):
                pass
            votes_by_id.setdefault(scenario["id"], []).append(
                {"run": n, "verdict": verdict, "model_id": model_id,
                 "rc": proc.returncode})
            print("%s run-%d verdict=%s model=%s rc=%s"
                  % (scenario["id"], n, verdict, model_id, proc.returncode))
        for sid, votes in votes_by_id.items():
            (KEYS_DIR / sid / "votes.json").write_text(
                json.dumps(votes, indent=1) + "\n", encoding="utf-8")
    finally:
        for scenario in scenarios:
            cleanup(scenario)


# ── CLI ───────────────────────────────────────────────────────────────────


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["probe", "keygen", "prompt"])
    ap.add_argument("scenarios")
    ap.add_argument("--only")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--keep", action="store_true",
                    help="keep the worktree after the run (debugging)")
    args = ap.parse_args()

    scenarios = load_scenarios(args.scenarios)
    if args.only:
        wanted = args.only.split(",")
        scenarios = [s for s in scenarios if s["id"] in wanted]
        if not scenarios:
            sys.exit("no scenario " + args.only)

    if args.mode == "keygen":
        keygen(scenarios, args.runs)
        return

    results = []
    failures = []
    for scenario in scenarios:
        try:
            mat = materialize(scenario)
        except Exception as exc:
            failures.append({"id": scenario["id"], "error": str(exc)[:300]})
            print("FAIL %s (materialize): %s" % (scenario["id"], exc),
                  file=sys.stderr)
            cleanup(scenario)
            continue
        try:
            if mat["unknown_members"]:
                print("WARN %s: members outside pinned lists marked done: %s"
                      % (scenario["id"], ",".join(mat["unknown_members"])),
                      file=sys.stderr)
            if args.mode == "prompt":
                print(build_prompt(scenario, mat))
                continue
            if args.mode == "probe":
                p = probe(scenario, mat)
                results.append({
                    "id": scenario["id"], "task": scenario["task"],
                    "decision": p["decision"], "reason": p["reason"],
                    "n_overlaps": len(p["facts"]["overlaps"]),
                    "n_tokens": len(p["facts"]["tokens_matched"]),
                    "unparseable": p["facts"]["unparseable_downstream"],
                    "overlaps": p["facts"]["overlaps"],
                    "tokens_matched": p["facts"]["tokens_matched"],
                    "touched": p["facts"]["touched"],
                })
                print("%-14s %-7s %s" % (scenario["id"], p["decision"],
                                         p["reason"]))
                continue
        except Exception as exc:
            failures.append({"id": scenario["id"], "error": str(exc)[:300]})
            print("FAIL %s (%s): %s" % (scenario["id"], args.mode, exc),
                  file=sys.stderr)
        finally:
            if not args.keep:
                cleanup(scenario)

    if args.mode == "probe" and results:
        # Full fact dump (external touched-sets/overlaps) stays maintainer-
        # local — the committed distillation is results.tsv.
        KEYS_DIR.mkdir(parents=True, exist_ok=True)
        out = KEYS_DIR / "probe-results.json"
        out.write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
        print("wrote", out)
    if failures:
        print("FAILURES: %s" % json.dumps(failures), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
