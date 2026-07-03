#!/usr/bin/env python3
"""Finalize cross-repo scenario selection from survey output.

Selection rules (documented in the committed README):
- prefer scenarios with clean sweeps (done summary at checkout, no foreign
  sibling commits in the sweep range, no timestamp-fallback siblings)
- if downstream sibling bodies CHANGED in (head..checkout], fall back to
  checkout=head (pre-plan-sync faithful state; done summary then absent and
  the key agent uses plan-sync.md's documented git-log inference fallback)
- diversity: cap per spec so >=4 specs contribute per repo where possible
- >=8 per repo target; shortfalls documented with reasons
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from survey import git, is_ancestor, evidence_commits, load_states


def downstream_bodies_changed(repo, head, checkout, spec, downstream):
    """Downstream sibling .md changes in (head..checkout], split by kind.

    Returns (modified, added): M = body existed at head, edited after (revert
    checkout to head for the pre-sync state); A = body first committed inside
    the sweep range (pre-sync state unrecoverable -> reject the scenario).
    """
    if checkout == head:
        return [], []
    out = git(repo, "diff", "--name-status", head, checkout, "--",
              ".flow/tasks/", check=False)
    modified, added = [], []
    for line in out.split("\n"):
        fields = line.strip().split("\t")
        if len(fields) < 2:
            continue
        status, path = fields[0], fields[1]
        for d in downstream:
            if path == ".flow/tasks/%s.md" % d:
                (added if status.startswith("A") else modified).append(d)
    return modified, added


def finalize(repo_path, cands, picks):
    repo = Path(repo_path).expanduser()
    out = []
    for pick in picks:
        c = next((x for x in cands if x["task"] == pick), None)
        if c is None:
            print("MISSING candidate %s" % pick, file=sys.stderr)
            continue
        notes = []
        checkout = c["checkout"]
        modified, added = downstream_bodies_changed(
            repo, c["head"], checkout, c["spec"], c["todo_at_completion"])
        if added:
            print("REJECT %s: downstream bodies %s first committed inside "
                  "the sweep range — pre-sync state unrecoverable"
                  % (pick, ",".join(added)), file=sys.stderr)
            continue
        if modified:
            checkout = c["head"]
            notes.append(
                "downstream bodies %s changed in sweep range; checkout "
                "reverted to head (pre-sync state, done summary absent)"
                % ",".join(modified))
        if checkout == c["head"]:
            if not c["has_done_summary_at_checkout"]:
                notes.append("done summary absent at checkout; key agent uses "
                             "plan-sync.md git-log inference fallback")
        if c["ambiguous_siblings"]:
            notes.append("sibling done-ness via state updated_at timestamp "
                         "fallback (no usable evidence commits): %s"
                         % ",".join(c["ambiguous_siblings"]))
        if not is_ancestor(repo, c["head"], git(repo, "rev-parse", "main")):
            notes.append("evidence commits pre-squash/branch-side (not on "
                         "main); checkout=head branch state")
        out.append({
            "id": None,  # filled by caller
            "task": c["task"], "spec": c["spec"],
            "base_commit": c["base"], "first_commit": c["first"],
            "head_commit": c["head"], "checkout": checkout,
            "downstream": c["todo_at_completion"],
            "done_siblings": c["done_at_completion"],
            "cross_spec": False,
            "derivation": "base=first-evidence-commit^; head=last evidence "
                          "commit; checkout=%s" % (
                              "head" if checkout == c["head"]
                              else "first post-head commit touching task md"),
            "notes": notes,
        })
    return out


if __name__ == "__main__":
    sel = json.loads(Path(sys.argv[1]).read_text())
    scenarios = []
    for repo_key, cfg in sel.items():
        cands = json.loads(Path(cfg["candidates"]).read_text())
        chosen = finalize(cfg["repo"], cands, cfg["picks"])
        for i, s in enumerate(chosen, 1):
            s["id"] = "%s-%02d" % (repo_key, i)
            s["repo"] = cfg["repo"]
        scenarios.extend(chosen)
    print(json.dumps({"scenarios": scenarios}, indent=1))
