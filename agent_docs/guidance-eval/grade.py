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
import re
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

    # 3. tests. `unittest discover` exits 0 even when it discovers ZERO tests, so
    # green-with-no-tests must not pass: require >=1 test actually RAN. (The test
    # FILE being committed + clean is enforced per scenario via committed_and_clean
    # below, so the tests that ran are the committed ones.)
    tp = subprocess.run(
        ["python3", "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=d,
        capture_output=True,
        text=True,
    )
    m = re.search(r"^Ran (\d+) test", tp.stderr, re.MULTILINE)
    ran = int(m.group(1)) if m else 0
    r["tests_ran"] = ran
    r["tests_green"] = tp.returncode == 0 and ran >= 1

    # 4. shim log: agent flowctl invocations + failures
    log = d / ".flow/invocations.log"
    inv = log.read_text().splitlines() if log.exists() else []
    r["flowctl_calls"] = len(inv)
    r["flowctl_errors"] = sum(1 for line in inv if not line.startswith("0|"))
    r["error_cmds"] = [
        line.split("|", 1)[1][:70] for line in inv if not line.startswith("0|")
    ][:4]

    # 5. committed state. The grade is only meaningful against COMMITTED work:
    # `committed>0` alone is gameable (an empty commit + uncommitted impl). So we
    # require a CLEAN worktree (worktree == HEAD) and verify the scenario's source
    # file is tracked in HEAD - only then does grading the worktree grade HEAD.
    lg = subprocess.run(
        ["git", "log", "--oneline"], cwd=d, capture_output=True, text=True
    )
    r["committed"] = max(0, len(lg.stdout.splitlines()) - 1)
    # worktree_clean is INFORMATIONAL only: the shim's invocations.log, agent.log,
    # .flow state sidecars, and __pycache__ leave the tree dirty by construction on
    # every run, so it cannot be a scored dimension. The scored committed-state
    # guard is per-source-file (src_committed + src_clean below).
    porcelain = subprocess.run(
        ["git", "status", "--porcelain"], cwd=d, capture_output=True, text=True
    )
    r["worktree_clean"] = porcelain.stdout.strip() == ""

    def in_head(relpath):
        return (
            subprocess.run(
                ["git", "cat-file", "-e", f"HEAD:{relpath}"],
                cwd=d,
                capture_output=True,
            ).returncode
            == 0
        )

    def committed_and_clean(relpath):
        """The source is tracked in HEAD AND the worktree copy matches HEAD, so the
        code the tests run against is exactly the committed code. This defeats the
        'empty commit + uncommitted implementation' gaming path without penalizing
        the harness's own always-dirty instrumentation files."""
        if not in_head(relpath):
            return False
        diff = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--", relpath], cwd=d, capture_output=True
        )
        return diff.returncode == 0  # 0 = no diff between worktree and HEAD

    # ordered successful (rc==0) lifecycle events (kind, task) from the shim log
    events = []
    for line in inv:
        rc_str, _, rest = line.partition("|")
        if rc_str != "0":
            continue
        args = rest.split()
        if args[:1] == ["done"] and len(args) >= 2:
            events.append(("done", args[1]))
        elif args[:2] == ["task", "reset"] and len(args) >= 3:
            events.append(("reset", args[2]))
        elif args[:1] == ["block"] and len(args) >= 2:
            events.append(("block", args[1]))

    # 6. scenario-specific dimensions
    if scenario == "multitask":
        src_rel = "src/envconf.py"
        r["src_present"] = (d / src_rel).exists()
        r["src_committed"] = committed_and_clean(src_rel)
        r["tests_committed"] = committed_and_clean("tests/test_envconf.py")
        r["has_dependency"] = in_spec_dependency
        # Identify the prerequisite (depended-upon) and dependent (depends_on)
        # tasks, then require the PRESCRIBED ordered workflow in the shim log:
        #   done(prereq) -> reset(prereq) -> done(prereq) -> done(dependent).
        # A subsequence match (other events may interleave) - so legitimate
        # variation is allowed, but a materially wrong execution cannot score.
        prereq = dependent = None
        for tid, deps in deps_by_task.items():
            in_spec = [dep for dep in deps if dep in task_id_set and dep != tid]
            if in_spec:
                dependent, prereq = tid, in_spec[0]
                break
        lifecycle_ordered = False
        lifecycle_kind = "none"
        if prereq and dependent:
            state = 0  # 0:await done1  1:await reset  2:await done2  3:done
            second_done_idx = None
            for i, (kind, tid) in enumerate(events):
                if tid != prereq:
                    continue
                if state == 0 and kind == "done":
                    state = 1
                elif state == 1 and kind in ("reset", "block"):
                    state = 2
                    lifecycle_kind = kind
                elif state == 2 and kind == "done":
                    state = 3
                    second_done_idx = i
            dependent_after = second_done_idx is not None and any(
                k == "done" and t == dependent and i > second_done_idx
                for i, (k, t) in enumerate(events)
            )
            lifecycle_ordered = state == 3 and dependent_after
        r["lifecycle_ordered"] = lifecycle_ordered
        r["lifecycle_kind"] = lifecycle_kind
        r["prereq_task"] = prereq
        r["dependent_task"] = dependent
        dims = [
            r["spec_created"],
            n_tasks >= 2,
            r["has_dependency"],
            r["lifecycle_ordered"],
            r["all_tasks_done"],
            r["evidence_ok"],
            r["tests_green"],
            not bad,
            r["src_committed"],
            r["tests_committed"],
        ]
    else:  # slugify (single-task)
        src_rel = "src/slugify.py"
        r["src_present"] = (d / src_rel).exists()
        r["src_committed"] = committed_and_clean(src_rel)
        r["tests_committed"] = committed_and_clean("tests/test_slugify.py")
        dims = [
            r["spec_created"],
            r["any_task_done"],
            r["evidence_ok"],
            r["tests_green"],
            not bad,
            r["src_committed"],
            r["tests_committed"],
        ]

    score_num = sum(bool(x) for x in dims)
    score_max = len(dims)
    r["score"] = f"{score_num}/{score_max}"
    r["passed"] = score_num == score_max  # every scored dimension satisfied
    print(json.dumps(r))


if __name__ == "__main__":
    main()
