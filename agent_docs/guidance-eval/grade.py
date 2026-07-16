#!/usr/bin/env python3
"""Deterministic grader for one guidance-eval scratch repo.

Reads the scratch repo's flow state + the flowctl logging shim log and emits ONE
JSON object (one line) with the scored dimensions. No network, no model, no
judgement - every field is a mechanical read of committed state, so the same repo
grades identically forever.

Usage:  grade.py <scratch_dir>

Scored dimensions (common):
  spec_created      a spec exists
  n_tasks           tasks under the first spec
  any_task_done     at least one task reached status=done
  all_tasks_done    every task reached status=done
  evidence_ok       EVERY done task carries valid evidence (see evidence_valid())
  md_todos          forbidden TODO/TASKS/PLAN*.md files at repo root (want empty)
  tests_green       `python3 -m unittest discover -s tests` exits 0
  committed         commits beyond the scaffold commit
  flowctl_calls     agent flowctl invocations (from the shim log)
  flowctl_errors    non-zero-rc agent flowctl invocations

Scenario-specific:
  slugify:   src_present (src/slugify.py)
  multitask: src_present (src/envconf.py); has_dependency (some task depends on
             another in the same spec); lifecycle_event (shim log shows a
             `task reset` or `block`); lifecycle_kind
"""
import json
import pathlib
import subprocess
import sys


def evidence_valid(ev):
    """Valid iff a dict with keys commits/tests/prs, each a list of strings, and
    at least one commit recorded. This is the sole correctness-critical contract
    the eval measures (the historical failure was `done` with no/empty evidence)."""
    if not isinstance(ev, dict):
        return False
    for key in ("commits", "tests", "prs"):
        val = ev.get(key)
        if not isinstance(val, list):
            return False
        if any(not isinstance(x, str) for x in val):
            return False
    return len(ev.get("commits", [])) > 0


def main():
    d = pathlib.Path(sys.argv[1]).resolve()
    meta_path = d / ".eval-meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    scenario = meta.get("scenario", "slugify")

    flowctl_py = str(d / ".flow/bin/flowctl.py")

    def fc(*args):
        """Call the REAL flowctl (not the shim) so grading does not pollute the log."""
        return subprocess.run(
            ["python3", flowctl_py, *args], cwd=d, capture_output=True, text=True
        )

    def as_list(raw, key):
        try:
            obj = json.loads(raw or "[]")
        except json.JSONDecodeError:
            return []
        if isinstance(obj, dict):
            return obj.get(key, [])
        return obj if isinstance(obj, list) else []

    r = dict(meta)
    r["run"] = d.name

    # 1. spec + task lifecycle state
    specs = as_list(fc("specs", "--json").stdout, "specs")
    r["spec_created"] = len(specs) > 0
    n_tasks = 0
    done_tasks = []
    all_task_ids = []
    deps_by_task = {}
    evidence_all_ok = None  # None -> no done tasks to judge
    if specs:
        sid = specs[0]["id"]
        tasks = as_list(fc("tasks", "--spec", sid, "--json").stdout, "tasks")
        n_tasks = len(tasks)
        ev_flags = []
        for t in tasks:
            show = fc("show", t["id"], "--json").stdout
            try:
                info = json.loads(show or "{}")
            except json.JSONDecodeError:
                info = {}
            all_task_ids.append(t["id"])
            deps_by_task[t["id"]] = list(info.get("depends_on") or [])
            if info.get("status") == "done":
                done_tasks.append(t["id"])
                ev_flags.append(evidence_valid(info.get("evidence")))
        if ev_flags:
            evidence_all_ok = all(ev_flags)
    # A real in-spec dependency: some task depends on ANOTHER task in this spec
    # (a dangling/out-of-spec dep does not count).
    task_id_set = set(all_task_ids)
    in_spec_dependency = any(
        dep in task_id_set
        for tid, deps in deps_by_task.items()
        for dep in deps
        if dep != tid
    )
    r["n_tasks"] = n_tasks
    r["any_task_done"] = len(done_tasks) > 0
    r["all_tasks_done"] = n_tasks > 0 and len(done_tasks) == n_tasks
    r["done_tasks"] = done_tasks
    r["evidence_ok"] = bool(evidence_all_ok)

    # 2. forbidden markdown TODO artifacts at repo root
    bad = [
        p.name
        for p in d.glob("*.md")
        if p.name.upper().startswith(("TODO", "TASKS", "PLAN"))
    ]
    r["md_todos"] = bad

    # 3. tests
    tp = subprocess.run(
        ["python3", "-m", "unittest", "discover", "-s", "tests"],
        cwd=d,
        capture_output=True,
        text=True,
    )
    r["tests_green"] = tp.returncode == 0

    # 4. shim log: agent flowctl invocations + failures
    log = d / ".flow/invocations.log"
    inv = log.read_text().splitlines() if log.exists() else []
    r["flowctl_calls"] = len(inv)
    r["flowctl_errors"] = sum(1 for line in inv if not line.startswith("0|"))
    r["error_cmds"] = [
        line.split("|", 1)[1][:70] for line in inv if not line.startswith("0|")
    ][:4]

    # 5. commits beyond the scaffold commit
    lg = subprocess.run(
        ["git", "log", "--oneline"], cwd=d, capture_output=True, text=True
    )
    r["committed"] = max(0, len(lg.stdout.splitlines()) - 1)

    # 6. scenario-specific dimensions
    if scenario == "multitask":
        r["src_present"] = (d / "src/envconf.py").exists()
        r["has_dependency"] = in_spec_dependency
        # lifecycle event = a SUCCESSFUL (rc==0) `task reset <id>` or `block <id>`
        # whose target is an in-spec task. A failed command, or one aimed at a
        # task outside this spec, does NOT count. The shim logs "rc|argv...".
        reset_seen = False
        block_seen = False
        for line in inv:
            rc_str, _, rest = line.partition("|")
            if rc_str != "0":
                continue  # only successful invocations count
            args = rest.split()
            if args[:2] == ["task", "reset"] and len(args) >= 3 and args[2] in task_id_set:
                reset_seen = True
            if args[:1] == ["block"] and len(args) >= 2 and args[1] in task_id_set:
                block_seen = True
        r["lifecycle_event"] = reset_seen or block_seen
        r["lifecycle_kind"] = (
            "reset" if reset_seen else ("block" if block_seen else "none")
        )
        dims = [
            r["spec_created"],
            n_tasks >= 2,
            r["has_dependency"],
            r["lifecycle_event"],
            r["all_tasks_done"],
            r["evidence_ok"],
            r["tests_green"],
            not bad,
            r["committed"] > 0,
            r["src_present"],
        ]
    else:  # slugify (single-task)
        r["src_present"] = (d / "src/slugify.py").exists()
        dims = [
            r["spec_created"],
            r["any_task_done"],
            r["evidence_ok"],
            r["tests_green"],
            not bad,
            r["committed"] > 0,
            r["src_present"],
        ]

    score_num = sum(bool(x) for x in dims)
    score_max = len(dims)
    r["score"] = f"{score_num}/{score_max}"
    r["passed"] = score_num == score_max  # every scored dimension satisfied
    print(json.dumps(r))


if __name__ == "__main__":
    main()
