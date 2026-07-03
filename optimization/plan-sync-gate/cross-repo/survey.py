#!/usr/bin/env python3
"""Survey external flow-managed repos for plan-sync gate replay candidates.

READ-ONLY against the external repos: file reads + git plumbing queries only.
Emits candidate scenarios as JSON: done tasks that (a) carry hash-shaped
evidence commits reachable on main, (b) had >=1 downstream todo sibling at
completion time, (c) have all sibling task bodies present at the derived
checkout SHA.

Derivations (documented per scenario):
- base       = first evidence commit ^ (parent)  [older evidence lacks base_commit]
- head       = last evidence commit
- checkout   = first commit after head (on main) touching .flow/tasks/<T>.md
               (the done-summary sweep commit), else head itself
- done-at-T  = siblings whose own head evidence commit is an ancestor of T's
               head; fallback to state updated_at comparison when a sibling
               has no usable commits
- todo-at-T  = siblings not done-at-T (explicit state reconstruction later)
- faithful   = no OTHER sibling's evidence commits lie inside (head..checkout]
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HASH_RE = re.compile(r"[0-9a-fA-F]{7,64}$")


def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", str(repo)] + list(args),
                       capture_output=True, text=True, encoding="utf-8")
    if check and r.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (args, r.stderr.strip()[:200]))
    return r.stdout.strip()


def commit_exists(repo, sha):
    r = subprocess.run(["git", "-C", str(repo), "cat-file", "-e", sha + "^{commit}"],
                       capture_output=True, text=True)
    return r.returncode == 0


def is_ancestor(repo, a, b):
    """True if a is ancestor of b (or equal)."""
    r = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", a, b],
                       capture_output=True, text=True)
    return r.returncode == 0


def load_states(repo):
    d = Path(repo) / ".git" / "flow-state" / "tasks"
    out = {}
    for f in sorted(d.glob("*.state.json")):
        tid = f.name[: -len(".state.json")]
        try:
            out[tid] = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return out


def spec_of(tid):
    return tid.rsplit(".", 1)[0]


def evidence_commits(state, repo):
    ev = state.get("evidence")
    if not isinstance(ev, dict):
        return []
    commits = ev.get("commits") or []
    if isinstance(commits, str):
        commits = [commits]
    # some evidence shapes: 'commit' singular
    if not commits and ev.get("commit"):
        commits = [ev["commit"]]
    good = []
    for c in commits:
        c = str(c).strip()
        # tolerate "abc1234 message" forms
        first_tok = c.split()[0] if c.split() else ""
        if HASH_RE.fullmatch(first_tok) and commit_exists(repo, first_tok):
            good.append(git(repo, "rev-parse", first_tok + "^{commit}"))
    return good


def survey(repo_path, main_ref="main"):
    repo = Path(repo_path).expanduser()
    states = load_states(repo)
    main = git(repo, "rev-parse", main_ref)
    by_spec = {}
    for tid, st in states.items():
        by_spec.setdefault(spec_of(tid), {})[tid] = st

    candidates = []
    for spec_id, members in sorted(by_spec.items()):
        if len(members) < 2:
            continue
        # Precompute per-sibling commit info
        info = {}
        for tid, st in members.items():
            commits = evidence_commits(st, repo) if st.get("status") == "done" else []
            info[tid] = {
                "status": st.get("status"),
                "commits": commits,
                "updated_at": st.get("updated_at"),
            }
        for tid, st in sorted(members.items()):
            if st.get("status") != "done":
                continue
            commits = info[tid]["commits"]
            if not commits:
                continue
            head = commits[-1]
            first = commits[0]
            if not is_ancestor(repo, head, main):
                continue
            # base = first^
            try:
                base = git(repo, "rev-parse", first + "^")
            except RuntimeError:
                continue
            # checkout: first commit after head touching the task md
            md_rel = ".flow/tasks/%s.md" % tid
            lst = git(repo, "rev-list", "--reverse", head + ".." + main,
                      "--", md_rel, check=False)
            checkout = lst.split("\n")[0].strip() if lst.strip() else head
            # done summary present at checkout?
            md_at = git(repo, "show", checkout + ":" + md_rel, check=False)
            has_summary = bool(md_at) and "## Done summary" in md_at and \
                "TBD" not in md_at.split("## Done summary")[1][:200]
            # siblings
            todo_at, done_at, ambiguous = [], [], []
            foreign_in_range = []
            for sib, sinfo in sorted(info.items()):
                if sib == tid:
                    continue
                if sinfo["commits"]:
                    sib_head = sinfo["commits"][-1]
                    if is_ancestor(repo, sib_head, head):
                        done_at.append(sib)
                    else:
                        todo_at.append(sib)
                        # faithfulness: sibling commits inside (head..checkout]
                        if checkout != head:
                            for c in sinfo["commits"]:
                                if is_ancestor(repo, c, checkout) and not is_ancestor(repo, c, head):
                                    foreign_in_range.append(sib + ":" + c[:8])
                elif sinfo["status"] == "done":
                    # no usable commits: timestamp fallback
                    tu, su = st.get("updated_at"), sinfo["updated_at"]
                    if tu and su:
                        (done_at if su <= tu else todo_at).append(sib)
                        ambiguous.append(sib)
                    else:
                        ambiguous.append(sib)
                        done_at.append(sib)  # conservative doc'd below
                else:
                    todo_at.append(sib)
            if not todo_at:
                continue
            # bodies present at checkout?
            missing = []
            for x in [tid] + todo_at:
                for ext in (".md", ".json"):
                    r = subprocess.run(
                        ["git", "-C", str(repo), "cat-file", "-e",
                         checkout + ":.flow/tasks/" + x + ext],
                        capture_output=True)
                    if r.returncode != 0:
                        missing.append(x + ext)
            candidates.append({
                "task": tid, "spec": spec_id,
                "base": base, "first": first, "head": head,
                "checkout": checkout,
                "n_evidence_commits": len(commits),
                "has_done_summary_at_checkout": has_summary,
                "todo_at_completion": todo_at,
                "done_at_completion": done_at,
                "ambiguous_siblings": ambiguous,
                "foreign_commits_in_sweep_range": foreign_in_range,
                "missing_bodies_at_checkout": missing,
                "updated_at": st.get("updated_at"),
            })
    return candidates


if __name__ == "__main__":
    repo = sys.argv[1]
    cands = survey(repo)
    print(json.dumps(cands, indent=1))
