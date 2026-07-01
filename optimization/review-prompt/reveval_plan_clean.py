#!/usr/bin/env python3
"""Plan over-flag check: run baseline vs plan_lean on a GOOD spec (test strategy,
observability, sized/ordered tasks, NFRs all present). Does the checklist falsely
flag present items? Metric = verdict + finding count + false-missing flags."""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reveval as R  # noqa
import reveval_plan as P  # noqa
import flowctl  # noqa

CLEAN = open(os.path.join(R.HERE, "spec_clean.md")).read()
RUNS = int(os.environ.get("REVEVAL_RUNS", "3"))
# a false-missing flag = the review claims one of these is ABSENT though the clean spec has it
FALSE_MISSING = {
    "test strategy": ["no test", "missing test", "test strategy is (absent|missing|not)", "lacks test", "without test"],
    "observability": ["no observability", "missing observability", "no logging", "no metrics", "lacks observability"],
    "idempotency": ["not idempotent", "no idempoten", "missing idempoten", "lacks idempoten"],
    "error handling": ["no error handling", "missing error handling", "lacks error handling"],
}


def _prompt(lean):
    p = flowctl.build_review_prompt("plan", CLEAN, "Contacts CRM; existing single-add UI.",
                                    task_specs="(tasks inline in the spec)")
    return p.replace(P.INTRO, P.INTRO + P.PLAN_LEAN, 1) if lean else p


def n_findings(review):
    return len(re.findall(r"(?im)^\s*[-*\d.]+\s*\*?\*?(severity|gap|issue|problem)\*?\*?\s*[:*\-]", review)) \
        or len(re.findall(r"(?im)\bGAP\b", review))


def false_missing(review):
    r = review.lower()
    hits = []
    for item, pats in FALSE_MISSING.items():
        for pat in pats:
            if re.search(pat, r):
                hits.append(item); break
    return hits


def main():
    print(f"# plan over-flag on GOOD spec — runs={RUNS}\n")
    for name, lean in [("plan_baseline", False), ("plan_lean", True)]:
        prompt = _prompt(lean)
        verds, finds, falses = [], [], []
        for i in range(RUNS):
            review, usage, dt, st = R.run_codex(prompt)
            if st != "OK":
                print(f"  [{name} run{i+1}] {st}"); continue
            open(os.path.join(R.HERE, f"planclean_{name}_{i+1}.md"), "w").write(review)
            v = R.verdict_of(review); nf = n_findings(review); fm = false_missing(review)
            verds.append(v); finds.append(nf); falses.append(len(fm))
            print(f"  [{name} run{i+1}] {v} findings~{nf} false-missing={fm} {dt:.0f}s")
        n = len(verds) or 1
        ships = sum(1 for v in verds if v == "SHIP")
        print(f"  => {name}: SHIP {ships}/{len(verds)}  avg findings~{sum(finds)/n:.1f}  "
              f"avg false-missing={sum(falses)/n:.1f}\n")


if __name__ == "__main__":
    main()
