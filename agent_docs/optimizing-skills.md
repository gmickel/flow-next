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
| Hot-path agents | `context-scout` (2.8k), the prime scouts (9, parallel), plan scouts, `repo-scout` ✅ | Output budget | low (generic mutation) |
| Accuracy-critical | `capture`, `impl/plan/completion-review` (use `~/work/slop-testbed`) | accuracy-first, token 2nd | medium |
| Heavy prompts | `make-pr` (31k), `audit`, `interview`, `prospect` | Prompt trim | higher — strong behavioral evals required |

## Promoting a kept mutation to ship

The `opt/*` branch stays experimental. When a mutation is confirmed: apply it to the canonical
file → `scripts/sync-codex.sh` (agent/skill change mirrors to Codex) → **version bump**
(`scripts/bump.sh`) → `CHANGELOG.md` + flow-next.dev → tag + release. Only then does it reach users.
