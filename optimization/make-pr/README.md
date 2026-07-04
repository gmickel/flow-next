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

**Frozen inputs** (`fixtures/`): `payload-rich.json` + `payload-sparse.json` are real
`export-cognitive-aid` payloads captured from this repo (`payload-rich` = fn-52 tracker-sync: 11 tasks,
R1–R16, 1 decision + 7 bugs, 26 diff files — most body sections; `payload-sparse` = fn-50, the lean case).
**`payload-risky.json` (fn-84.4) is SYNTHETIC** — payload-rich with ONLY its `diff_summary` swapped for a
risk-differentiated set (a core high-churn `flowctl.py`, a security `credentials.py` with
`security_sensitive_paths[]`, a public-export add/remove on an exporter-faithful `__init__.py`, vs a
high-churn test file + low-risk docs). It exists to give **E6 (Where-to-look risk prioritization)** a
diff with clear risk tiers, which the real captured payloads (all low-risk scaffolding) lack. The `diff_summary`
is exporter-faithful in shape but its counts/modules are hand-authored (a render fixture, not a live export).

**Capture-lesson constraint (carried from the capture loop):** make-pr's body is hallucination-
guarded (§2.5: every claim traces to a payload field). Per the capture finding (accuracy-critical
prose is proximity-sensitive — trimming it regresses behavior), this loop does NOT trim the
field-rules of the 5-tier critical-changes priority or the where-to-look categories. **fn-84.4 update:**
E6 now guards the where-to-look reviewer-focus, and the fn-84.4 pass MEASURED (not asserted) a **−189 tok**
safe trim — render-irrelevant rationale asides PLUS a *structural* omission-clause dedup (redundant
"omit if empty" clauses removed once the authoritative §2.13 table covered them), verified body-equivalent
on rich (E1–E5) + risky (E1–E6). The measured boundary is the per-section **unique imperatives** (e.g.
§2.8's "no fallback no-decisions line", which the §2.13 table lacks) and the field-rules themselves —
those remain the accuracy-risky per-section backlog.

Files: test-inputs(=fixtures) · evals.md · results.tsv · changelog.md · baseline/{4 files} · fixtures/
