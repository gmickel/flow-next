# Autoresearch — make-pr (Heavy prompt, R6)

Eval-driven optimization of `/flow-next:make-pr` (~31.6k tokens across SKILL.md + workflow.md
(23k!) + phases.md + mermaid-rules.md). Lever per fn-54/FLOW-5 R6: **prompt-trim** for input-token
savings every invocation — guarded by **behavioral evals** (the rendered PR body stays equivalent).

**Run-trick = `--dry-run` render from a frozen export payload.** make-pr renders the body from a
`flowctl spec export-cognitive-aid <spec> --json` payload; `--dry-run` renders to stdout and
short-circuits before any `git push` / `gh pr create`. So a read-only subagent told to "follow
make-pr in --dry-run and render the body from THIS frozen payload" produces exactly the artifact the
behavioral evals score — zero side effects, no PR created. Baseline reads
`optimization/make-pr/baseline/SKILL.md`; experiments read the live skill.

**Frozen inputs** (`fixtures/`): real `export-cognitive-aid` payloads captured from this repo.
`payload-rich.json` (fn-52 tracker-sync: 11 tasks, R1–R16 satisfied, 1 decision + 7 bug memory
entries, 26 diff files) exercises the most body sections. `payload-sparse.json` (fn-50) is the
lean case. (Note: `diff_summary` reflects the opt-branch diff, not the spec's historical diff —
fine for a render fixture since it is identical across baseline + experiment.)

**Capture-lesson constraint (carried from the capture loop):** make-pr's body is hallucination-
guarded (§2.5: every claim traces to a payload field). Per the capture finding (accuracy-critical
prose is proximity-sensitive — trimming it regresses behavior), this loop does NOT trim the
guardrails, the 5-tier critical-changes priority, the where-to-look categories, or the omission
rules. The only cleanly **render-irrelevant** trim is the `fn-42.N` build-scaffolding archaeology
(stale "implemented in fn-42.3"-style task refs in headings/parentheticals — the render logic never
references them). Deeper prose trims are an accuracy-risky per-section backlog, not a one-shot.

Files: test-inputs(=fixtures) · evals.md · results.tsv · changelog.md · baseline/{4 files} · fixtures/
