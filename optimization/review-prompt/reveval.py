#!/usr/bin/env python3
"""reveval.py — autoresearch loop for review-prompt QUALITY vs EFFICIENCY.

Method (per the user's rules): baseline -> small tweak -> run via codex (our
default model) on a fixed ground-truth corpus -> score QUALITY (detection vs an
answer key) + EFFICIENCY (prompt size, review output tokens, wall time) ->
compare to baseline -> keep tweaks that improve one goal without regressing the
other; throw the rest away.

Corpus: orders.py — a realistic module with 10 planted issues:
  4 correctness bugs (any competent review must catch) + 6 Fowler smells
  (tests whether an always-on smell baseline improves the Standards catch).

Usage: python3 reveval.py [variant1 variant2 ...]   (default: all)
Env:   REVEVAL_RUNS=N (default 2), REVEVAL_MODEL=gpt-5.5, REVEVAL_EFFORT=high
"""
import sys, os, re, json, time, subprocess

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root (optimization/review-prompt/ -> root)
sys.path.insert(0, os.path.join(REPO, "plugins/flow-next/scripts"))
os.chdir(REPO)
import flowctl  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = open(os.path.join(HERE, "orders.py")).read()
MODEL = os.environ.get("REVEVAL_MODEL", "gpt-5.5")
EFFORT = os.environ.get("REVEVAL_EFFORT", "high")
RUNS = int(os.environ.get("REVEVAL_RUNS", "2"))

# ---------------------------------------------------------------- answer key
# (category, human name, detection keywords — OR-matched, case-insensitive)
GROUND = {
 "G1": ("correctness", "mutable default arg",
        ["append_audit", "mutable default", "shared list", "log=[]", "default arg", "default mutable", "shared across calls"]),
 "G2": ("correctness", "off-by-one",
        ["line_total", "off-by-one", "off by one", "range(len", "out of range", "out-of-range", "indexerror", "len(qtys) + 1", "past the end", "one past"]),
 "G3": ("correctness", "None-deref",
        ["discounted", "coupon", "none", "null", "guest"]),
 "G4": ("correctness", "resource leak",
        ["write_receipt", "leak", "never closed", "not closed", "isn't closed", "context manager", "with open", "file handle", "unclosed"]),
 "G5": ("smell", "Long Method",
        ["process_order", "long method", "too much", "too many responsib", "god function", "does everything", "decompos", "extract ", "single responsib", "split into"]),
 "G6": ("smell", "Feature Envy",
        ["format_greeting", "feature envy", "reaches into", "envy", "belongs on", "method on customer"]),
 "G7": ("smell", "Data Clumps",
        ["data clump", "clump", "address type", "street", "postcode", "travel together", "parameter object", "group of param", "dataclass", "address object"]),
 "G8": ("smell", "Primitive Obsession",
        ["apply_fee", "primitive obsession", "bare float", "money type", "currency", "primitive", "decimal", "money as float"]),
 "G9": ("correctness", "SQL injection",
        ["injection", "sql inject", "customer_tier", "parameteriz", "parametriz", "string concat", "concatenat", "bind param", "sql string", "sanitiz"]),
 "G10": ("smell", "Duplicated Code",
        ["tier_discount", "duplicat", "dupe", "dry", "repeated logic", "same logic", "copy of"]),
}
CORRECT = [g for g, v in GROUND.items() if v[0] == "correctness"]
SMELLS = [g for g, v in GROUND.items() if v[0] == "smell"]


def detect(review):
    r = review.lower()
    return {g: any(k.lower() in r for k in kws) for g, (_, _, kws) in GROUND.items()}


# ---------------------------------------------------------------- codex runner
def run_codex(prompt, timeout=420):
    t0 = time.time()
    try:
        p = subprocess.run(
            ["codex", "exec", "--json", "--model", MODEL,
             "-c", f"model_reasoning_effort={EFFORT}", prompt],
            capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return "", {}, time.time() - t0, "TIMEOUT"
    dt = time.time() - t0
    msgs, usage = [], {}
    for line in p.stdout.splitlines():
        try:
            o = json.loads(line)
        except Exception:
            continue
        if o.get("type") == "turn.completed":
            usage = o.get("usage", {})
        it = o.get("item", {})
        if it.get("type") == "agent_message" and it.get("text"):
            msgs.append(it["text"])
    text = "\n".join(msgs)
    # A non-zero exit (auth failure, bad model/config, CLI error) or an empty
    # response is NOT a real review — return a non-OK status so callers SKIP the
    # run instead of scoring it as 0 detections, which would silently corrupt the
    # variant comparison (a good prompt could look worse purely from a flaky call).
    # Mirrors the TIMEOUT path above; callers already gate on `st != "OK"`.
    if p.returncode != 0:
        return text, usage, dt, f"FAIL(rc={p.returncode})"
    if not text.strip():
        return text, usage, dt, "EMPTY"
    return text, usage, dt, "OK"


def verdict_of(review):
    m = re.findall(r"<verdict>(\w+)</verdict>", review)
    return m[-1] if m else "?"


# ---------------------------------------------------------------- variants
BASE_SPEC = ("Order-fulfilment + pricing module. Acceptance: "
             "- **R1:** line/price/tax/ship math is correct; "
             "- **R2:** DB access is safe; "
             "- **R3:** structure is clean and maintainable.")


def _base_prompt():
    return flowctl.build_review_prompt(
        "impl", BASE_SPEC, "orders.py — a new single-file module.",
        diff_summary="1 file changed, +117", diff_content=CODE)


# The experimental Fowler smell baseline (Fowler, _Refactoring_ ch.3). Terse:
# name-as-leading-word carries the definition; explicit "judgement call" framing.
FOWLER_BLOCK = """
## Code-smell baseline (always-on, judgement calls — repo standards override; skip what tooling enforces)
Beyond correctness, name any of these you spot and quote the hunk (each a heuristic, never a hard violation):
Long Method · Large Class · Long Parameter List · Duplicated Code · Feature Envy (uses another object's data more than its own) · Data Clumps (same values always passed together — wants a type) · Primitive Obsession (bare primitives where a small type belongs) · Shotgun Surgery · Divergent Change · Message Chains · Middle Man · Speculative Generality · Temporary Field · Refused Bequest.
"""

INTRO = "Conduct a John Carmack-level review of this implementation."


def v_baseline():
    return _base_prompt()


def v_fowler():
    return _base_prompt().replace(INTRO, INTRO + FOWLER_BLOCK, 1)


# --- efficiency lever: tight rewrites of the 4 big rubric blocks (~6.0KB -> ~1.9KB).
# Every machine-parsed marker kept (verdict tags, the four tally lines, R-ID logic).
TRIM = {
"CONFIDENCE_RUBRIC_BLOCK": """## Confidence (pick ONE anchor; no interpolation)
- **100** — definitive from code alone (mechanical: off-by-one, wrong type, swapped args).
- **75** — full path traced; a normal caller hits it; reproducible from the diff.
- **50** — depends on conditions visible but not confirmable here (e.g. can this be null? callers not in diff).
- **25** — needs runtime conditions with no direct evidence.
- **0** — speculative; don't file.
Suppression gate: drop findings below 75, EXCEPT P0 at 50+ (those survive). Emit a `Suppressed findings:` count when any dropped.""",
"CLASSIFICATION_RUBRIC_BLOCK": """## Introduced vs pre-existing
Classify each finding: **introduced** (this diff caused or newly exposed it) or **pre_existing** (already on base, untouched — a finding on an unchanged line is pre_existing by default; confirm with `git blame`/base-file read when cheap).
Verdict gate: only `introduced` findings affect the verdict — a review whose survivors are all `pre_existing` ships. List pre-existing under `## Pre-existing issues (not blocking this verdict)` as `[sev, confidence N, introduced=false] file:line — summary`; never drop them. End with `Classification counts: N introduced, M pre_existing.`""",
"PROTECTED_ARTIFACTS_BLOCK": """## Protected artifacts
NEVER recommend deleting / gitignoring / removing these committed pipeline paths (flag bad CONTENT inside them, never their existence): `.flow/*`, `.flow/bin/*`, `.flow/memory/*`, `.flow/specs/*.md`, `.flow/tasks/*.md`, `docs/plans/*`, `docs/solutions/*`, `scripts/ralph/*`. Discard any such finding during synthesis; emit a `Protected-path filter:` count when any dropped.""",
"R_ID_COVERAGE_BLOCK": """## Requirements coverage (only if the spec has R-IDs like `- **R1:** ...`)
If R-IDs are present, read the epic's `## Acceptance Criteria` (tolerate legacy `## Acceptance` / `## Acceptance criteria`) and emit:
| R-ID | Status | Evidence |
Status ∈ met / partial / not-addressed / deferred. After the table emit `Unaddressed R-IDs: [...]`. A non-deferred `not-addressed` R-ID forces NEEDS_WORK. If no R-IDs anywhere, skip this block entirely.""",
}


def _prompt_with_blocks(overrides, fowler=False):
    saved = {k: getattr(flowctl, k) for k in overrides}
    try:
        for k, v in overrides.items():
            setattr(flowctl, k, v)
        p = _base_prompt()
    finally:
        for k, v in saved.items():
            setattr(flowctl, k, v)
    if fowler:
        p = p.replace(INTRO, INTRO + FOWLER_BLOCK, 1)
    return p


def v_trim():
    return _prompt_with_blocks(TRIM)


def v_fowler_trim():
    return _prompt_with_blocks(TRIM, fowler=True)


# round 2 efficiency pushes (all keep the proven smell baseline + rubric trim)
FOWLER_LEAN = """
## Code-smell baseline (always-on, judgement calls — repo standards override; skip what tooling enforces)
Beyond correctness, name any of these you spot and quote the hunk (each a heuristic, never a hard violation):
Long Method · Large Class · Long Parameter List · Duplicated Code · Feature Envy (uses another object's data more than its own) · Data Clumps (same values always passed together — wants a type) · Primitive Obsession (bare primitives where a small type belongs) · Speculative Generality.
"""

# collapse the output-format's redundant tally re-listing (the trimmed blocks
# already name Suppressed findings / Classification counts / Protected-path filter).
_OFMT_RE = re.compile(
    r"After the findings list, emit:.*?(?=\*\*Verdict gate:\*\*)", re.S)
_OFMT_TIGHT = ("After the findings, add (only when applicable): the `## Requirements coverage` "
               "table + `Unaddressed R-IDs:` line, and the `Suppressed findings:` / "
               "`Classification counts:` / `Protected-path filter:` tally lines named above.\n")


def v_fowler_lean():
    return _prompt_with_blocks(TRIM).replace(INTRO, INTRO + FOWLER_LEAN, 1)


def v_ft_tighter():
    p = _prompt_with_blocks(TRIM).replace(INTRO, INTRO + FOWLER_LEAN, 1)
    return _OFMT_RE.sub(_OFMT_TIGHT, p)


VARIANTS = {
    "baseline": v_baseline,
    "fowler": v_fowler,
    "trim": v_trim,
    "fowler_trim": v_fowler_trim,
    "fowler_lean": v_fowler_lean,
    "ft_tighter": v_ft_tighter,
}


# ---------------------------------------------------------------- main
def main():
    which = [a for a in sys.argv[1:] if a in VARIANTS] or list(VARIANTS)
    print(f"# reveval — model={MODEL} effort={EFFORT} runs={RUNS} variants={which}\n")
    rows = []
    for name in which:
        prompt = VARIANTS[name]()
        pchars = len(prompt)
        agg = {"caught": [], "correct": [], "smell": [], "out_tok": [], "time": [], "verdict": []}
        per_g = {g: 0 for g in GROUND}
        for i in range(RUNS):
            review, usage, dt, st = run_codex(prompt)
            if st != "OK":
                print(f"  [{name} run{i+1}] {st}")
                continue
            d = detect(review)
            for g, hit in d.items():
                per_g[g] += int(hit)
            agg["caught"].append(sum(d.values()))
            agg["correct"].append(sum(d[g] for g in CORRECT))
            agg["smell"].append(sum(d[g] for g in SMELLS))
            agg["out_tok"].append(usage.get("output_tokens", 0))
            agg["time"].append(dt)
            agg["verdict"].append(verdict_of(review))
            # persist raw review for inspection
            with open(os.path.join(HERE, f"out_{name}_{i+1}.md"), "w") as fh:
                fh.write(review)
            print(f"  [{name} run{i+1}] caught {sum(d.values())}/10 "
                  f"(corr {sum(d[g] for g in CORRECT)}/{len(CORRECT)}, "
                  f"smell {sum(d[g] for g in SMELLS)}/{len(SMELLS)}) "
                  f"out={usage.get('output_tokens',0)}tok {dt:.0f}s {verdict_of(review)}")
        n = len(agg["caught"]) or 1
        rows.append({
            "name": name, "pchars": pchars, "ptok": pchars // 4,
            "caught": sum(agg["caught"]) / n, "correct": sum(agg["correct"]) / n,
            "smell": sum(agg["smell"]) / n, "out_tok": sum(agg["out_tok"]) / n,
            "time": sum(agg["time"]) / n,
            "per_g": {g: f"{per_g[g]}/{len(agg['caught'])}" for g in GROUND},
        })
    print("\n## SUMMARY (avg over runs)")
    print(f"{'variant':10} {'prompt_tok':>10} {'caught/10':>10} {'corr/5':>7} "
          f"{'smell/5':>8} {'out_tok':>8} {'time_s':>7}")
    for r in rows:
        print(f"{r['name']:10} {r['ptok']:>10} {r['caught']:>10.1f} {r['correct']:>7.1f} "
              f"{r['smell']:>8.1f} {r['out_tok']:>8.0f} {r['time']:>7.0f}")
    print("\n## per-goal detection (hits/runs)")
    hdr = " ".join(f"{g:>4}" for g in GROUND)
    print(f"{'variant':10} {hdr}   ({', '.join(g+'='+GROUND[g][1] for g in GROUND)})")
    for r in rows:
        print(f"{r['name']:10} " + " ".join(f"{r['per_g'][g]:>4}" for g in GROUND))
    json.dump(rows, open(os.path.join(HERE, "results.json"), "w"), indent=2)


if __name__ == "__main__":
    main()
