#!/usr/bin/env python3
"""Autoresearch loop for PLAN review — the impl loop's analog. Quality lever
under test: an always-on 'spec-quality baseline' (plan smells) analogous to the
Fowler code-smell baseline. Corpus = spec_corpus.md with 10 planted weaknesses."""
import sys, os, re, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reveval as R  # noqa: E402  (run_codex, verdict_of, HERE)
import flowctl  # noqa: E402

SPEC = open(os.path.join(R.HERE, "spec_corpus.md")).read()
RUNS = int(os.environ.get("REVEVAL_RUNS", "2"))

# planted weaknesses + detection keywords (OR-matched, case-insensitive)
PW = {
 "P1": ("untestable acceptance criteria (R2 'fast', vague R1/R3)",
        ["untestable", "not testable", "unmeasurable", "not measurable", "vague", "no metric", "how fast", "\"fast\"", "measurable", "quantif", "r2"]),
 "P2": ("missing error handling for malformed rows",
        ["error handling", "malformed", "invalid row", "invalid email", "parse error", "bad data", "validation", "invalid input", "failure mode", "reject"]),
 "P3": ("ambiguous / underspecified interface",
        ["interface", "signature", "underspecified", "ambiguous", "return type", "result shape", "contract", "importcontacts", "what does result", "unspecified"]),
 "P4": ("unhandled edge cases (empty/duplicate/oversized/encoding)",
        ["empty file", "duplicate", "large file", "oversized", "huge", "encoding", "edge case", "boundary", "size limit", "max size"]),
 "P5": ("Task 1 too large for one iteration",
        ["too large", "too big", "won't fit", "entire pipeline", "end-to-end", "split", "decompose", "break", "one iteration", "single task", "scope of task 1", "task 1 does"]),
 "P6": ("wrong task dependency ordering (Task 2 -> Task 3)",
        ["ordering", "out of order", "depends on task 3", "dependency order", "reorder", "task 2 depends", "before task 3", "task 3 before", "sequencing", "overlap"]),
 "P7": ("no test strategy",
        ["test strategy", "no test", "missing test", "testing plan", "no mention of test", "test coverage", "how.*tested", "unit test"]),
 "P8": ("missing idempotency / rollback for partial failure",
        ["idempoten", "rollback", "partial import", "partial failure", "re-upload", "re-import", "transaction", "atomic", "inconsistent state", "resume", "retry"]),
 "P9": ("missing observability for batch/async job",
        ["observability", "logging", "metrics", "progress", "monitor", "audit trail", "status of the import", "track the import"]),
 "P10": ("internal contradiction (synchronous vs background job)",
        ["contradic", "conflict", "synchronous.*background", "background.*synchronous", "sync.*async", "both sync", "inconsistent approach", "which one", "sync or"]),
}


def detect(review):
    r = review.lower()
    out = {}
    for k, (_, kws) in PW.items():
        hit = False
        for kw in kws:
            if ".*" in kw:
                if re.search(kw, r):
                    hit = True; break
            elif kw in r:
                hit = True; break
        out[k] = hit
    return out


INTRO = "Conduct a John Carmack-level review of this plan."
PLAN_CHECKLIST = """
## Spec-quality baseline (always-on, judgement calls — a strong plan should clear these)
Beyond the criteria above, check the plan for these common weaknesses; name any you find and quote the spec:
Untestable/unmeasurable acceptance criteria · Missing error/failure handling · Ambiguous or underspecified interfaces/contracts · Unhandled edge cases (empty, duplicate, oversized, malformed, concurrent inputs) · Task too large for one iteration · Wrong task dependency ordering · Missing test strategy · Missing idempotency/rollback for partial failures · Missing observability (logging/metrics/progress) for batch/async work · Internal contradictions · Unstated non-functional requirements (performance, security, privacy).
"""


def _plan_prompt():
    return flowctl.build_review_prompt("plan", SPEC, "Contacts CRM; existing single-add UI.",
                                       task_specs="(tasks are inline in the spec above)")


def v_plan_baseline():
    return _plan_prompt()


def v_plan_checklist():
    return _plan_prompt().replace(INTRO, INTRO + PLAN_CHECKLIST, 1)


# leaner: target only the items the baseline reliably MISSES (test strategy,
# observability, task sizing/ordering, non-functional reqs) — fewer tokens.
PLAN_LEAN = """
## Also explicitly verify (commonly-missed): a stated **test strategy**; **observability** (logging/metrics/progress) for any async/batch work; each task **sized for one iteration and correctly ordered** by dependency; and stated **non-functional requirements** (performance, security, privacy).
"""


def v_plan_lean():
    return _plan_prompt().replace(INTRO, INTRO + PLAN_LEAN, 1)


VARIANTS = {"plan_baseline": v_plan_baseline, "plan_checklist": v_plan_checklist,
            "plan_lean": v_plan_lean}


def main():
    which = [a for a in sys.argv[1:] if a in VARIANTS] or list(VARIANTS)
    print(f"# plan reveval — runs={RUNS} variants={which}\n")
    rows = []
    for name in which:
        prompt = VARIANTS[name]()
        agg = {"caught": [], "out": [], "t": [], "v": []}
        per = {k: 0 for k in PW}
        for i in range(RUNS):
            review, usage, dt, st = R.run_codex(prompt)
            if st != "OK":
                print(f"  [{name} run{i+1}] {st}"); continue
            d = detect(review)
            for k, h in d.items():
                per[k] += int(h)
            agg["caught"].append(sum(d.values())); agg["out"].append(usage.get("output_tokens", 0))
            agg["t"].append(dt); agg["v"].append(R.verdict_of(review))
            open(os.path.join(R.HERE, f"plan_out_{name}_{i+1}.md"), "w").write(review)
            print(f"  [{name} run{i+1}] caught {sum(d.values())}/10  out={usage.get('output_tokens',0)}tok {dt:.0f}s {R.verdict_of(review)}")
        n = len(agg["caught"]) or 1
        rows.append((name, len(prompt)//4, sum(agg["caught"])/n, sum(agg["out"])/n, sum(agg["t"])/n, {k: f"{per[k]}/{len(agg['caught'])}" for k in PW}))
    print("\n## SUMMARY")
    print(f"{'variant':16}{'ptok':>7}{'caught/10':>11}{'out_tok':>9}{'time':>7}")
    for nm, pt, c, o, t, _ in rows:
        print(f"{nm:16}{pt:>7}{c:>11.1f}{o:>9.0f}{t:>7.0f}")
    print("\n## per-weakness (hits/runs)")
    print(f"{'variant':16}" + " ".join(f"{k:>4}" for k in PW))
    for nm, _, _, _, _, per in rows:
        print(f"{nm:16}" + " ".join(f"{per[k]:>4}" for k in PW))
    print("\nkey:", ", ".join(f"{k}={PW[k][0][:28]}" for k in PW))


if __name__ == "__main__":
    main()
