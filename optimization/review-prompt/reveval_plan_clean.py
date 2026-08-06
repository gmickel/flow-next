#!/usr/bin/env python3
"""Plan over-flag check: run baseline vs plan_lean on a GOOD spec (test strategy,
observability, sized/ordered tasks, NFRs all present). Does the checklist falsely
flag present items? Metric = verdict + finding count + false-missing flags."""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reveval as R  # noqa
import reveval_plan as P  # noqa
import flowctl  # noqa
# fn-169 R4: `build_review_prompt` carries identities (paths + a commit
# range). This harness has no repo for the reviewer to read, so — like the
# `export` review mode — it appends its own payload blocks after the builder.
# Production paths never do this; the eval's variable is prompt WORDING, and
# holding the payload constant across variants is what keeps that comparable.


def _embed_payload(prompt, *, spec="", diff_summary="", diff_content="", task_specs=""):
    """Append the payload blocks the identity builder no longer emits.

    Eval-harness only: there is no repository to fetch from here. Ordering matches
    the pre-fn-169 production builder so variant-to-variant deltas stay
    attributable to the wording under test rather than to a layout change.
    """
    blocks = []
    if diff_summary:
        blocks.append(f"<diff_summary>\n{diff_summary}\n</diff_summary>")
    if diff_content:
        blocks.append(f"<diff_content>\n{diff_content}\n</diff_content>")
    if spec:
        blocks.append(f"<spec>\n{spec}\n</spec>")
    if task_specs:
        blocks.append(f"<task_specs>\n{task_specs}\n</task_specs>")
    if not blocks:
        return prompt
    return prompt + "\n\n" + "\n\n".join(blocks)


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
    p = _embed_payload(
        flowctl.build_review_prompt(
            "plan", context_hints="Contacts CRM; existing single-add UI."),
        spec=CLEAN, task_specs="(tasks inline in the spec)")
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
