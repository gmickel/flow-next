#!/usr/bin/env python3
"""Over-flag check: run baseline vs fowler_trim on CLEAN idiomatic code (no
planted issues). Measures whether the smell baseline invents noise on clean code.
Metric = # of findings emitted (each carries a **Severity** line) + verdict."""
import sys, os, re, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reveval as R  # noqa: E402
import flowctl  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CLEAN = open(os.path.join(HERE, "orders_clean.py")).read()
RUNS = int(os.environ.get("REVEVAL_RUNS", "3"))
SMELL_WORDS = ["feature envy", "data clump", "primitive obsession", "long method",
               "duplicat", "large class", "long parameter", "shotgun", "message chain",
               "middle man", "speculative", "temporary field", "refused bequest", "smell"]


def _prompt(code, fowler_trim):
    if not fowler_trim:
        return flowctl.build_review_prompt("impl", R.BASE_SPEC, "orders.py — a new single-file module.",
                                           diff_summary="1 file changed, +80", diff_content=code)
    saved = {k: getattr(flowctl, k) for k in R.TRIM}
    try:
        for k, v in R.TRIM.items():
            setattr(flowctl, k, v)
        p = flowctl.build_review_prompt("impl", R.BASE_SPEC, "orders.py — a new single-file module.",
                                        diff_summary="1 file changed, +80", diff_content=code)
    finally:
        for k, v in saved.items():
            setattr(flowctl, k, v)
    return p.replace(R.INTRO, R.INTRO + R.FOWLER_BLOCK, 1)


def n_findings(review):
    # each surviving finding carries a "**Severity**" (or "Severity:") line
    return len(re.findall(r"(?im)^\s*[-*]?\s*\*?\*?severity\*?\*?\s*[:*]", review))


def n_smellmentions(review):
    r = review.lower()
    return sum(r.count(w) for w in SMELL_WORDS)


def main():
    print(f"# over-flag check on CLEAN code — runs={RUNS}\n")
    for name, ft in [("baseline", False), ("fowler_trim", True)]:
        prompt = _prompt(CLEAN, ft)
        finds, smells, verds, outs = [], [], [], []
        for i in range(RUNS):
            review, usage, dt, st = R.run_codex(prompt)
            if st != "OK":
                print(f"  [{name} run{i+1}] {st}"); continue
            nf, ns = n_findings(review), n_smellmentions(review)
            finds.append(nf); smells.append(ns)
            verds.append(R.verdict_of(review)); outs.append(usage.get("output_tokens", 0))
            with open(os.path.join(HERE, f"clean_{name}_{i+1}.md"), "w") as fh:
                fh.write(review)
            print(f"  [{name} run{i+1}] findings={nf} smell_mentions={ns} "
                  f"out={usage.get('output_tokens',0)}tok {dt:.0f}s {R.verdict_of(review)}")
        n = len(finds) or 1
        print(f"  => {name}: avg findings={sum(finds)/n:.1f}  avg smell_mentions={sum(smells)/n:.1f} "
              f"verdicts={verds}\n")


if __name__ == "__main__":
    main()
