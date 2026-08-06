#!/usr/bin/env python3
"""Over-flag check: run baseline vs fowler_trim on CLEAN idiomatic code (no
planted issues). Measures whether the smell baseline invents noise on clean code.
Metric = # of findings emitted (each carries a **Severity** line) + verdict."""
import sys, os, re, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reveval as R  # noqa: E402
import flowctl  # noqa: E402
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


HERE = os.path.dirname(os.path.abspath(__file__))
CLEAN = open(os.path.join(HERE, "orders_clean.py")).read()
RUNS = int(os.environ.get("REVEVAL_RUNS", "3"))
SMELL_WORDS = ["feature envy", "data clump", "primitive obsession", "long method",
               "duplicat", "large class", "long parameter", "shotgun", "message chain",
               "middle man", "speculative", "temporary field", "refused bequest", "smell"]


def _prompt(code, fowler_trim):
    if not fowler_trim:
        return _embed_payload(
            flowctl.build_review_prompt(
                "impl", context_hints="orders.py — a new single-file module."),
            spec=R.BASE_SPEC, diff_summary="1 file changed, +80", diff_content=code)
    saved = {k: getattr(flowctl, k) for k in R.TRIM}
    try:
        for k, v in R.TRIM.items():
            setattr(flowctl, k, v)
        p = _embed_payload(
            flowctl.build_review_prompt(
                "impl", context_hints="orders.py — a new single-file module."),
            spec=R.BASE_SPEC, diff_summary="1 file changed, +80", diff_content=code)
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
