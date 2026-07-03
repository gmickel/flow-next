# Worker-anchor comprehension-equivalence eval (fn-83.3) — the bundle merge gate

> **This eval backs the shipped `flowctl anchor` command** (live — unlike
> the sibling `optimization/plan-sync-gate/` harness, whose gate was proven
> non-viable and removed; see that README's ARCHIVED banner). The bundle
> passed both this comprehension eval and the deterministic superset test,
> and `/flow-next:work`'s worker anchors via the single call since fn-83.4.

Proof that `flowctl anchor <task-id> --md` — the single-call worker anchor
bundle — loses ZERO comprehension versus the legacy discrete worker Phase-1
read sequence (show/cat task+spec, git status/log, memory flag, memory
index, glossary — replaced by the single anchor call in fn-83.4). The bundle's win is round-trips, not
content reduction — this harness is the proof, alongside the deterministic
superset test ([`plugins/flow-next/tests/test_anchor_bundle.py`](../../plugins/flow-next/tests/test_anchor_bundle.py))
which locks byte-for-byte verbatim-ness in CI forever. Pattern lineage:
[`optimization/plan-sync-gate/`](../plan-sync-gate/README.md) /
[`optimization/review-prompt/`](../review-prompt/README.md) per
[`agent_docs/optimizing-skills.md`](../../agent_docs/optimizing-skills.md).

## Layout

| File | Role |
|---|---|
| `gen_inputs.py` | Freezes the two arms per task from ONE working-tree state |
| `inputs/<task>/bundle.md` | FROZEN — `flowctl anchor <id> --md` output |
| `inputs/<task>/statusquo.md` | FROZEN — worker Phase-1 transcript (`$ cmd` + verbatim output, worker.md order) |
| `inputs/manifest.json` | Generation SHA + date (inputs frozen @ `7d62856467be`) |
| `questions.json` | **COMMITTED ANSWER KEY** — 7 binary questions per task + accept/reject regexes |
| `run_eval.py` | Subject runner (headless `claude -p`, no tools, empty cwd) + deterministic grader |
| `runs/<task>-<arm>.json` | Raw subject outputs (auditability) |
| `results.tsv` | Scores + merge-gate verdict rows |

## Design

**Frozen tasks (≥3, varied size, three different specs, all with deps):**

| Short | Task | Size | Non-satisfies question targets |
|---|---|---|---|
| `fn-64.3` | fn-64-tracker-sync-project-flow-spec.3 | S (3.2k task md) | spec R6 (fn-64.3 covers R1/R3 per the coverage table) |
| `fn-74.2` | fn-74-cursor-review-backend-cursor-agent-cli.2 | M (5.6k) | spec R2 (satisfies: R5,R6,R7,R8,R11,R14) |
| `fn-81.2` | fn-81-skill-runtime-token-plumbing-single.2 | L (8.1k) | spec R12 (satisfies: R8,R9,R10,R11,R13) |

**Question set per task (K=7, binary, key-graded):** acceptance-criteria
ids · files to touch · a boundary/non-goal · dependency status · requirement
contents · a question answerable ONLY from a spec section OUTSIDE the
task's satisfies/coverage list (guards any future bundle-filtering
regression) · one more requirement-content detail. fn-64.3 predates
`satisfies:` frontmatter — its "outside" question targets an R-ID the
spec's own Requirement-coverage table assigns to a DIFFERENT task, the same
outside-own-scope guarantee.

**Two arms per task, same state:** both docs are generated back-to-back by
`gen_inputs.py` from one working-tree state, so the ONLY difference is
packaging (one bundle vs. nine command outputs). Questions are answerable
from BOTH arms by construction — the bundle's extra dependency
done-summaries are deliberately NOT quizzed (that would unfairly favor the
bundle; dependency STATUS is in `show <spec> --json` in both arms).

**Grading — against the committed key, never agreement:** the subject
(fixed recorded model — resolved id `claude-sonnet-5`, alias `sonnet`,
claude CLI 2.1.199) answers `qN:` lines strictly from the supplied
document; `run_eval.py` grades each answer deterministically with the key's
accept/reject regexes. Bundle-vs-statusquo agreement is NOT the metric —
both-wrong fails both arms.

## Merge gate

On EVERY question set:

1. bundle score ≥ status-quo score, AND
2. bundle score ≥ the key threshold (**6/7**).

## Results (2026-07-03, inputs @ `7d62856467be`)

**PASS — zero comprehension loss measured.** Bundle 7/7 on all three sets;
status-quo 7/7 on all three sets (bundle ≥ statusquo everywhere, ≥ 6/7
everywhere). All 21 bundle-arm answers key-correct, including every
non-satisfies-section question — the full-spec-verbatim design (no R-ID
filtering) holds. See `results.tsv` + `runs/`.

## Re-running / extending (append-only)

```bash
python3 optimization/worker-anchor/run_eval.py               # re-run subjects + grade
python3 optimization/worker-anchor/run_eval.py --grade-only  # regrade saved runs
```

Frozen inputs and the answer key are never edited to make a run pass. To
extend: add a NEW task to `gen_inputs.py` + `questions.json`, regenerate
only the new task's inputs, run, and append rows to `results.tsv`. If a
future bundle change drops a section, the superset CI test fails first;
this harness is the comprehension backstop when a change survives that
(e.g. a render reorder) — re-run it and attach rows before merging.
