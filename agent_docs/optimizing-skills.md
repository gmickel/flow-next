# Optimizing flow-next skills & agents (eval-driven prompt optimization)

How to make a flow-next skill/agent prompt **measurably leaner and/or more accurate** using
eval-driven hill-climbing — a baseline, binary evals, one mutation at a time, keep-if-better.

> **This is a how-to, not a vendored capability.** We deliberately do **not** ship an
> `optimize-skill` skill inside flow-next. The methodology lives in an external repo; this file
> is the bridge to it plus our local conventions. Run it ad-hoc when a hot-path prompt is bloated
> or a judgment skill is flaky.

## Source / tooling (external — not in this repo)

- **Methodology + eval guide:** [`olelehmann100kMRR/autoresearch-skill`](https://github.com/olelehmann100kMRR/autoresearch-skill)
  (Karpathy "autoresearch" — autonomous experimentation applied to prompts).
  Cloned locally at **`~/repos/autoresearch-skill`** — read its `SKILL.md` + `eval-guide.md`.
- The host agent **follows** that methodology manually; nothing is installed. Re-`git pull` the
  clone before a run to pick up upstream changes.

## Where experiments live (local conventions, Gordon's machine)

- **Harness lives in:** `~/work/gmickel-claude-marketplace` (this repo — the `opt/*` branch + `optimization/<target>/`).
- **What the prompt is tested AGAINST — representative repos, NOT flow-next-on-itself.** A repo-context skill (scout / `plan` / code-aware `capture` / review) does its real job in a *user's* app repo, so evaluate it there:
  - **Primary:** `~/work/DocIQ-Sphere` (~442k LOC; TS/TSX + Python + XSD schemas + Docker — a conventional multi-stack app).
  - **+ ≥1 contrasting repo** (different size/stack) for variety — the eval-guide's "varied inputs" rule extends to *repo* variety. flow-next itself can serve as the small/unconventional contrast point.
  - flow-next-on-itself is acceptable **only** for repo-agnostic output-**format** mutations (relative paths, caps, no code blocks — the repo-scout budget win). It **overfits** for accuracy/coverage evals and prompt-trims: flow-next is one ~24k-LOC `flowctl.py` + markdown skills, not the multi-file app structure a scout actually has to navigate.
  - **Run mechanic:** dispatch the `Explore` subagent with the target repo as its working context and an absolute path to the prompt-under-test (`…/plugins/flow-next/agents/<target>.md`) — it reads the flow-next prompt but scouts the *other* repo.
- **Branch:** `opt/<name>` (e.g. `opt/autoresearch-tier1`). **Experimental — NO version bump,
  no release** until a kept mutation is promoted (see bottom).
- **Harness dir:** `optimization/<target>/` at **repo root** (NOT under `plugins/` — it must not
  ship in the plugin). Contains:
  - `README.md` — what's being optimized + how to resume
  - `test-inputs.md` — 3–5 **frozen**, repo-specific inputs (variety across use cases)
  - `evals.md` — 3–6 **binary** evals
  - `results.tsv` — `experiment  score  max_score  pass_rate  status  description`
  - `changelog.md` — per-experiment log (the most valuable artifact — a future agent resumes from it)
  - `<target>.md.baseline` — backup of the original prompt for revert
- **External eval suites / testbeds:** reuse where they exist — e.g. the review skills have a
  frozen clean-vs-slop testbed at **`~/work/slop-testbed`** (+ answer key at
  `~/work/agent-scripts/slop-testbed-answer-key.md`). That IS the frozen-input + eval suite for
  `impl-review`; don't rebuild it.

## The loop

1. **Pick the target** — a skill (`plugins/flow-next/skills/<skill>/*.md`) or an agent
   (`plugins/flow-next/agents/<agent>.md`).
2. **Freeze 3–5 test inputs** — real, repo-specific, varied (cover different use cases so you don't
   overfit to one). Write them to `test-inputs.md`.
3. **Write 3–6 binary evals** (`evals.md`). Each is yes/no — no scales (scales compound variance).
   See the eval-guide for good-vs-bad. **Mandatory:** ≥2–3 of them are *accuracy* evals
   (grounded / coverage / correctness / format), not just a token cap — see "Accuracy guard".
   `max_score = evals × runs`.
4. **Baseline (experiment 0)** — back up the prompt, run the target N times on the frozen inputs
   **as-is**, score every output, record. **Never mutate before measuring.**
5. **Experiment loop** — analyze failures → form ONE hypothesis → make ONE targeted edit →
   run N times → score → **keep if the score rose, else revert** to the baseline backup.
   Log every experiment (kept or discarded) in `results.tsv` + `changelog.md`.
6. **Stop** at the ceiling (100%, or 95%+ for 3 straight) or a budget cap. If you pass all evals
   but quality isn't actually better, your **evals** are weak — fix them, not the skill.

## How to "run" a flow-next skill/agent for scoring (the practical trick)

A skill/agent *is* a prompt + tool restrictions. To test a **candidate prompt whose edits are
live**, do **not** dispatch the registered agent (`flow-next:repo-scout` etc.) — it uses the
installed/cached copy, so your edits may not take effect. Instead:

- Dispatch a **read-only `Explore`** (or `general-purpose`) subagent with: *"Read `<prompt-file>`,
  that is your complete operating instructions — follow it exactly. Here is the input: `<frozen
  input>`. Output ONLY the result your instructions specify."*
- The prompt file is the **variable you control**: baseline reads `<target>.md.baseline`;
  experiments read the live (mutated) `plugins/flow-next/agents/<target>.md`.
- **Hold the model constant** (= the target's frontmatter `model`, e.g. `opus`) so scores compare
  apples-to-apples. Run the **same** N inputs every experiment.

## Scoring — deterministic where possible

- **Grounded:** extract every cited `path[:line]`, `test -f` it; spot-check line refs / claims.
- **Lean (token cap):** `words × 4/3 ≤ cap`.
- **Tagged / Focused / format:** grep for required tags, fenced-block length, mandatory sections.
- **Coverage / correctness:** host-agent judgment against the eval's explicit pass condition —
  still **binary** (yes/no), still recorded.

## The two token levers

- **Output budget** — cap what the skill *emits* (repo-relative paths, top-N items/section, one
  line/finding, no code blocks, omit empty sections). Cuts downstream context.
  *Proven: `repo-scout` exp 1 → ~40–50% smaller output, 83% → 100% on the eval set, accuracy held.*
- **Prompt trim** — remove instructions/examples that don't move the score
  (simplify-while-holding). Pure **input** savings on every invocation — the biggest single-prompt
  prizes are `make-pr` (~31k tok), `audit`/`capture`/`impl-review` (~14–15k each).

## Accuracy guard — why a trim can't quietly lose accuracy

Keep/revert is a **ratchet**: a mutation is kept **only if the score doesn't drop**, and the score
**includes the accuracy evals**. So accuracy cannot regress **by construction** — *as long as the
suite actually has accuracy evals.* The failure mode is a token-only suite. **Rule: every suite
carries ≥2–3 real accuracy evals.** The guarantee is exactly as strong as the evals.

## Accuracy-critical skills: `spec.md` is USER-AUTHORITATIVE

`capture` / `interview` **generate or edit** `spec.md`; `plan` / `*-review` **consume** it. The user
can hand-edit `spec.md` at any time — **it is the source of truth, not the skill's output.** Evals
for these must measure *fidelity + respect-for-override*, never "is the skill's spec correct":

- **Generators (`capture` / `interview`):** all 7 canonical sections present? every acceptance
  criterion source-tagged (`[user]`/`[paraphrase]`/`[inferred]`)? **read-back shown before write?**
  **does it refuse to silently overwrite a user-edited spec** (`--rewrite`-gated, no clobber)?
  conversation evidence preserved? → faithful synthesis + the user stays in control.
- **Consumers (`plan` / `*-review`):** the frozen input must be a **real, possibly hand-edited**
  `spec.md`; eval that the skill grounds its output in the spec **as written** (cites the actual
  sections / R-IDs, **including user edits**), and that a token-trim does **not** make it skim past
  user-edited sections. The user's spec — overrides included — **is** the ground truth the eval
  scores against. Bake a **"respects user spec override"** eval into every accuracy-critical suite.

## Target map (highest ROI first)

| Tier | Targets | Lever | Risk |
|---|---|---|---|
| Hot-path agents | `repo-scout` ✅, `context-scout` ✅ (2.8k), plan scouts | Output budget | low (generic mutation) |
| Accuracy-critical | `capture`, `impl/plan/completion-review` (use `~/work/slop-testbed`) | accuracy-first, token 2nd | medium |
| Heavy prompts | `make-pr` (31k), `audit`, `interview`, `prospect` | Prompt trim | higher — strong behavioral evals required |

**Empirical note (which scouts the output-budget lever actually pays on):** the lever pays on the
**free-form, local** scouts whose prose flows into the planner — `repo-scout` ✅ and `context-scout`
✅ are both done (60–70% leaner, accuracy held). It has **little headroom on the prime scouts**
(`build`/`testing`/`security`/`tooling`/`env`/`observability`/`workflow`/`docs`/`agents-md`): their
output is already a **bounded template** (fixed sections, ✅/❌ flags, a scores checklist), and
`prime` is a once-per-onboarding command (low frequency → low ROI per the cost rule). The
**research scouts** (`practice-scout`, `github-scout`) are **external/non-deterministic** (live
web/`gh` search, sources are URLs not local files) — noisy to score and not groundable against a
fixed repo; treat them as smoke-test territory, not this loop. Net: the scout-tier budget prizes
are `repo-scout` + `context-scout`; don't burn a loop re-confirming the templated/external ones.

**Field-tested lesson — accuracy-critical & heavy prompts resist trimming (proximity is load-bearing).**
Two findings from running the loop on `capture` (R5) and `make-pr` (R6):

- **`capture` baseline scored 15/15** — a mature accuracy-critical skill is often already correct
  (the override guard held: an existing *user-edited* spec invoked without `--rewrite` refused, exit
  2, hand-edit preserved). With no accuracy headroom, the only lever is a token-trim that *holds*
  the score. A "self-evidently safe" DRY trim (move `workflow.md`'s duplicated source-tag +
  biz-routing tables to the cross-linked `phases.md`) **regressed one input** — the success-metric
  signal got under-routed and Decision Context came out FLAT instead of the spec-correct
  SUBSTRUCTURED. 15→14 → revert. **The "duplication" was accuracy-load-bearing *proximity*:** a
  routing/taxonomy table read right beside the drafting step is applied more reliably than the same
  table one indirection away. **Do not trim routing/taxonomy/guardrail tables out of the phase that
  uses them**, even when a copy exists elsewhere. The ratchet caught it — which is the whole point of
  R3 (real accuracy evals make the guarantee real).
- **`make-pr` (~31k) is mostly load-bearing** — 5 phases, ~11 conditional body sections, 10
  hallucination guardrails, mermaid rules, push/retry, memory templating. The only cleanly-safe trim
  was **~170 tokens of `fn-42.N` build-scaffolding archaeology** (stale "implemented in fn-42.3" task
  refs in headings/parentheticals/a table column) — render-irrelevant by construction, body held
  5/5. Its verbose *render prose* is accuracy-shaping (same proximity rule), so deeper trims are an
  **accuracy-risky per-section backlog** (one eval-guarded experiment per section), not a one-shot.

Takeaway: lead with the **output-budget** lever on free-form scouts (big, low-risk wins); treat
prompt-trims on accuracy-critical/heavy skills as **archaeology-first, then careful per-section
work** — and never relocate a table out of the phase that consumes it.

**Where the big wins actually live — the uncapped-free-form-output agents.** The output-budget lever
(40-70% leaner) pays wherever an agent emits **uncapped, free-form prose that flows into another
prompt's context** — NOT on heavy *prompts* (those are load-bearing; trims are modest) and NOT on
agents whose output is already a **bounded template**. The win pool, by inspection of the fleet:
- **Done ✅:** `repo-scout`, `context-scout`, `flow-gap-analyst` (the last: 50-70% leaner, 26/27 gaps
  preserved — proof the lever generalizes past the scouts).
- **Next (uncapped free-form, no budget yet):** `quality-auditor` (full code-review report — per-finding
  Risk/Fix prose); the smaller plan scouts (`spec-scout`, `memory-scout`, `docs-scout`) if their output
  is verbose.
- **Skip:** the prime scouts (`build`/`testing`/`security`/…) — already a bounded ✅/❌ template;
  `practice-scout`/`github-scout` — external/non-deterministic.

**Feature-preservation rule for any free-form-output budget (load-bearing):** trim **per-item
verbosity, never the item COUNT**. For a gap-analyst that means every gap still surfaced; for a
reviewer, every finding still flagged. The **coverage eval IS the no-feature-loss guarantee** — bake
in a per-input answer key of must-find items and revert any mutation that drops below it. The biggest
single bloat source is **cross-section duplication** (the same finding restated as a flow + edge case
+ priority); killing that — not dropping items — is where most of the tokens come from. Note the real
**lean↔exhaustive knob**: a hard token cap can pressure the agent to enumerate fewer items; frame the
budget as "leanness via de-duplication, coverage is the job" and let the gap-richest inputs run a bit
longer rather than drop coverage (flow-gap-analyst exp1-vs-exp3).

## Promoting a kept mutation to ship

The `opt/*` branch stays experimental. When a mutation is confirmed: apply it to the canonical
file → `scripts/sync-codex.sh` (agent/skill change mirrors to Codex) → **version bump**
(`scripts/bump.sh`) → `CHANGELOG.md` + flow-next.dev → tag + release. Only then does it reach users.
