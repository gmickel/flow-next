# /flow-next:make-pr — phase reference

Per-phase Done-when checklists. The full execution flow lives in [workflow.md](workflow.md); this file is the at-a-glance map.

| Phase | Owner task | Goal |
|-------|------------|------|
| Phase 0 | fn-42.2 (this task) | Pre-flight — gh ready, epic resolved, base valid, branch ahead, tasks done, no open PR. |
| Phase 1 | fn-42.3 | Gather inputs — single `flowctl epic export-cognitive-aid` call, parse payload. |
| Phase 2 | fn-42.3 + fn-42.4 | Render body — TL;DR, R-ID table, critical changes (.3); decisions, memory, glossary/strategy, open items, where to look (.4). |
| Phase 3 | fn-42.5 | Mermaid generation — gated triggers, hard caps, fallback prose. |
| Phase 4 | fn-42.6 | Push + create PR — `git push`, `gh pr create`, draft/ready, dry-run short-circuit, Ralph behavior. |
| Phase 5 | fn-42.6 | Output + footer — PR URL, breadcrumb, optional `--memory` write. |

---

## Phase 0: Pre-flight (this task — fn-42.2)

**Done when:**

- [ ] Ralph context detected (`RALPH=1` if `FLOW_RALPH=1` or `REVIEW_RECEIPT_PATH` set).
- [ ] `gh` installed AND `gh auth status --hostname github.com` succeeds.
- [ ] `EPIC_ID` resolved (positional arg → branch-match against `.flow/epics/*.json` `branch_name` → interactive prompt / Ralph exit 2).
- [ ] `EPIC_ID` validated via `flowctl show <epic-id> --json` (epic exists).
- [ ] `BASE_REF` resolved through cascade (`--base` → `origin/main` → `main` → `origin/master` → `master` → ask / Ralph exit 2).
- [ ] `BASE_REF` validated via `git rev-parse --verify --quiet`.
- [ ] HEAD resolves; HEAD ≠ BASE; `git merge-base --is-ancestor BASE HEAD`; `git rev-list --count BASE..HEAD >= 1`.
- [ ] Tasks-done check (silent / warn under `--dry-run` / Ralph exit 2 / interactive ask).
- [ ] Existing-PR refusal check: `gh pr view --json url,state,number | jq -r 'select(.state == "OPEN") | .url'` returns empty.
- [ ] `PHASE0_CONTEXT` JSON built with epic / base / head / branch / commits_ahead / open_tasks / flags / draft_force.

**Failure modes:**

- gh missing → exit 1 + install instructions.
- gh unauthenticated → exit 1 + `gh auth login` instructions.
- Epic not resolved + Ralph → exit 2.
- Base not resolved + Ralph → exit 2.
- Base ref invalid → exit 1.
- HEAD == BASE → exit 1.
- HEAD not descendant of BASE → exit 1.
- 0 commits ahead → exit 1.
- Open tasks + Ralph → exit 2.
- OPEN PR exists → exit 1 + `/flow-next:resolve-pr` hint.

---

## Phase 1: Gather inputs (fn-42.3)

**Done when:**

- [ ] `flowctl epic export-cognitive-aid <EPIC_ID> --base <BASE_REF> --json` returns successfully.
- [ ] Payload parsed into in-memory dict matching the epic spec's "Architecture & Data Models" schema.
- [ ] All nine input streams accounted for: `epic`, `tasks`, `memory.{decisions,bugs,patterns}`, `glossary.changes`, `strategy.tracks`, `strategy.alignment_block`, `diff.{stat,name_status,log}`, `reviews.{deferred,suppressed_count,unaddressed}`.

---

## Phase 2: Render body (fn-42.3 + fn-42.4)

**fn-42.3 done when:**

- [ ] Body section order locked: H1 title + summary block + TL;DR + R-ID coverage + Critical changes + (Structural changes from .5) + (Decisions / Memory / Glossary-strategy / Open items / Where to look from .4) + footer breadcrumb. Sections never reorder.
- [ ] Title + summary block renders epic id link, branch / base, task counts, R-ID coverage ratio. Optional 2-line natural-language summary derived from `epic.spec_sections.goal_and_context` first paragraph (truncated to ≈240 chars at sentence boundary).
- [ ] TL;DR renders 3-5 plain-language bullets sourced from `goal_and_context` first sentence + top 5 tasks by churn (their `done_summary` first sentences). Never includes R-IDs. Never quotes raw diff content. Never pads if fewer than 4 substantive changes shipped.
- [ ] R-ID coverage table renders every R-ID from `epic.spec_sections.acceptance_criteria` in spec order (R-ID gaps preserved verbatim — never renumber). Columns exactly: `R-ID | Acceptance criterion | Task | Evidence`. Criterion text truncated to 120 chars + `…`. Task column derives ONLY from `tasks[].satisfies[]` — never inferred from titles or commit messages. Evidence column emits `[\`<sha7>\`](../../commit/<sha40>)` per commit in `tasks[].evidence.commits[]`. Uncovered → `⚠️ uncovered` + `—` evidence.
- [ ] When `tasks_summary.uncovered_r_ids` is non-empty, table is followed by an italic explanatory sentence: `⚠️ **<N> uncovered acceptance criterion(a):** R<i>, R<j>, R<k>. Reviewer should confirm these are intentional gaps before merge.`
- [ ] Critical changes section renders ≤7 bullets in 5-tier priority order: (1) high-churn from `diff_summary.high_churn_files[]`, (2) cross-module from `diff_summary.cross_module_changes[]`, (3) public-interface from `diff_summary.public_exports_changed[]` with `removed[]` items emitted FIRST within tier 3, (4) security-sensitive from `diff_summary.security_sensitive_paths[]`, (5) behavior-visible matching `commands/`, `routes/`, `pages/`, `app/`, `cli/`, `hooks/`, `bin/`. Hard 7-bullet cap.
- [ ] Limited-churn fallback bullet emitted when `<5` files / `<50` LOC / no module-boundary signal / no public-export signal — Critical changes section never omitted entirely.
- [ ] No-weakening rule honored: every `public_exports_changed[].removed` entry surfaced as "potentially breaking" / `removes \`<sym>\``. NEVER paraphrased as "non-breaking", "internal-only", "minor", or "trivial".
- [ ] No fabricated paths: every `<path>` in body comes from `diff_summary.files[]`. No fabricated symbols: every `<symbol>` from `diff_summary.public_exports_changed[]`. No fabricated SHAs: every `<sha>` from `tasks[].evidence.commits[]`.
- [ ] No raw diff content / code snippets in body — paths, churn, modules only.
- [ ] All 10 hallucination guardrails (workflow.md §2.5) hold: no fabricated paths/symbols/SHAs, no "non-breaking" weakening, no copy-pasted diff content, no inflated scope, no R-ID misattribution, no stale references, no invented "why" reasoning, every claim traces to a payload field.
- [ ] Section-omission rule (workflow.md §2.6) honored: empty content → no heading. Never empty placeholder. (Critical changes is the one exception — limited-churn fallback bullet keeps the heading present.)
- [ ] Abort conditions (workflow.md §2.7) checked before any rendering: empty `goal_and_context` AND every task missing `done_summary` → exit 1; every R-ID uncovered → exit 1. Empty `acceptance_criteria` (zero R-IDs in spec) is NOT an abort — coverage table is omitted, body proceeds with TL;DR + Critical changes pair.

**fn-42.4 done when:**

- [ ] Decisions made section (workflow.md §2.8): one bullet per `memory_during_epic.decisions[]` entry — `**<title>** ([<id>](.flow/memory/<id>.md)) — <first_sentence>. Alternatives considered: <parsed alternatives>.` Section omitted entirely when array empty (no sentinel "No decisions" line per §2.14). `alternatives_considered` parsed from the stringified-Python-list shape (`"['a', 'b']"` → `a, b`); empty / `"[]"` → trailing clause omitted; plain prose → emitted verbatim.
- [ ] Memory left behind section (workflow.md §2.9): renders when `memory_during_epic.bugs[]` OR `memory_during_epic.architecture_patterns[]` non-empty. Two sub-lists with bold preambles ("**Bugs captured during this epic:**" / "**Architecture patterns captured during this epic:**") when both populated; one sub-list when only one. Each bullet: ``` `<id>` — <first_sentence> ```. Section omitted when both empty.
- [ ] Glossary / strategy notes section (workflow.md §2.10): renders when `glossary_changes` has any non-empty array OR `strategy_alignment.tracks_served[]` non-empty OR `strategy_alignment.drift_flagged[]` non-empty. Glossary line: `**Glossary:** added \`<term>\`; renamed \`<old>\` → \`<new>\` (<N> files); removed \`<term>\`.` (clauses omitted per empty source array; rename clause documented but always empty in v1 per export `_export_glossary_diff` docstring). Strategy lines: `**Strategy:** served tracks \`<track-1>\`, ...` and/or `**Strategy drift:** \`<track>\` — <reason>; ...`. Section heading omitted when all contributions empty.
- [ ] Open items section (workflow.md §2.11): aggregates 3 sources with provenance breadcrumbs:
  - Source A — `epic.spec_sections.open_questions[]` → `- [ ] <question> — open question from spec`
  - Source B — `deferred_findings[].items[]` (branch-slug sink, no per-task attribution) → `- [ ] <stripped raw> — deferred from impl-review (\`<sink-relpath>\`)`
  - Source C — `flowctl show <epic-id> --json | jq '.completion_review_status'` returns `needs_work` → `- [ ] Epic-review verdict was \`needs_work\` (last reviewed <ts>) — flagged by epic-review`
  - Section omitted when all three sources empty. Source order A → B → C.
- [ ] Where to look section (workflow.md §2.12): 5 categories, **questions not labels**:
  - Architecture (≤3 bullets) from `epic.spec_sections.decision_context[]` — anchored to a `diff_summary.files[]` path; bullet dropped when no anchor.
  - Security (≤3 bullets) from `diff_summary.security_sensitive_paths[]` — question whitelist by path heuristic (`auth/`/`crypto/` → trust boundary; `.github/workflows/` → CI scope; `scripts/hooks/` → bypass; `*.pem`/`secret`/`token`/`credential` → safe-to-commit; default → trust boundary).
  - Business correctness (≤2 bullets) when `diff_summary.files[].path` matches `commands/`/`routes/`/`pages/`/`app/`/`cli/`/`hooks/`/`bin/` (same prefixes as Critical changes tier 5).
  - Performance (≤2 bullets) when host agent identifies hot-path heuristics (loops, DB queries, render-body calls) in source-extension files.
  - Tests (1 bullet) when zero `*.test.*` / `*_test.*` / `tests/` / `__tests__/` / `spec/` files in diff. Suppressed when diff is docs-only OR `files_changed < 3 AND lines_added+removed < 30`.
  - Section-level cap: 8 bullets total, trim in reverse-category order (Tests → Performance → Business → Security; Architecture never trimmed).
  - Section omitted when no category fires. Every focus prompt ends with `?`.
- [ ] Each of the 5 sections includes a "What this section MUST NOT do" callout (echo-chamber risk mitigation). Read-only mirror of source data — no paraphrasing, no extending, no inventing rationale to fill gaps.
- [ ] §2.14 honest-empty-state rule honored: NO sentinel "*No decisions for this epic*" / "*No open items*" lines emitted. Absence of section IS the signal.
- [ ] §2.13 section-omission table covers all five context sections.
- [ ] No code snippets in workflow.md prose that would actually generate sections — the prose tells the host agent WHAT to render, not HOW to render programmatically.

---

## Phase 3: Mermaid (fn-42.5)

**Done when:**

- [ ] `--no-mermaid` short-circuits before any trigger evaluation; body has no `## Structural changes` heading and no standalone prose summaries (workflow.md §3.0).
- [ ] Trigger evaluation walks the 5 conditions: (1) `cross_module_changes[]` non-empty, (2) `public_exports_changed[]` non-empty, (3) new top-level dir, (4) removed top-level dir, (5) >15 files in >3 modules. ≥1 fires → emit section; zero fire → omit entirely.
- [ ] Skip rules engage when applicable: pure additive within one module + <50 LOC; repo has no detectable module structure (no `src/`/`plugins/`/`app/`/etc.); stderr breadcrumb `Phase 3 skipped: <reason>` emitted.
- [ ] Hard caps enforced: max 3 diagrams per PR (collapse to `graph TB` overview when exceeded), max 12 nodes per diagram (group by module/abstraction when exceeded — `scouts (5)` not five sibling nodes), max 25 edges, max 12K chars per codefence.
- [ ] Shape selection picks from 4 shapes: `flowchart LR` (default for trigger 1, function-shape exports), `classDiagram` (class-shape exports — composition / inheritance), `sequenceDiagram` (route handlers / protocol flows), `graph TB` (default for trigger 5, default when collapsing 4+ to 1).
- [ ] Prose-summary-precedes-diagram rule (R13) honored: every codefence preceded by 3-5 sentence plain-language paragraph anchored to `diff_summary.files[]` paths. Self-contained — diagram-removable without losing structural-change signal.
- [ ] Pre-emission validation runs `mermaid-rules.md` §6 checklist (8 rules: quotes balanced, no reserved-word bare ids, no emoji, no MathJax, no relative click links, no inheritance cycles, arrow-char preference, ≤12K chars). Re-render loop on any failure — never emit known-broken codefence.
- [ ] Hallucination guardrails honored: no invented modules / edges / symbols; "fewer nodes, more honest" over "context nodes for clarity"; every node and edge traces to `diff_summary.modules_touched[]` / `diff_summary.files[]` / `cross_module_changes[]` / `public_exports_changed[]`.
- [ ] `mermaid-rules.md` ref file exists with: §1 reserved words (10 entries), §2 special-character escapes + HTML-entity fallback (decimal codes only), §3 shape decision matrix (4 examples — flowchart LR, classDiagram, sequenceDiagram, graph TB), §4 hard caps recap, §5 prose-summary rule, §6 8-item validation checklist.

---

## Phase 4: Push + create PR (fn-42.6)

**Done when:**

- [ ] `--dry-run` short-circuits: body printed to stdout, no `git push`, no `gh pr create`. Exit 0.
- [ ] `git push -u origin HEAD` runs (silent skip if already up-to-date).
- [ ] Draft/ready resolved: Ralph forces `--draft`; `OPEN_ITEMS_COUNT > 0` defaults to `--draft`; `--draft` forces draft; `--ready` forces non-draft (last flag wins).
- [ ] Interactive preview via `AskUserQuestion`: `create / dry-run / edit-body / abort` (skipped under Ralph).
- [ ] `gh pr create --title --body` invoked with heredoc body (preserves all formatting including mermaid).

---

## Phase 5: Output + footer (fn-42.6)

**Done when:**

- [ ] PR URL printed to stdout (single line for harness capture).
- [ ] Footer breadcrumb appended to body: `Generated by /flow-next:make-pr from <epic-id> against <base-ref> on <YYYY-MM-DD>`.
- [ ] `--memory` flag triggers idempotent `flowctl memory add --track knowledge --category architecture-patterns ...` (skip if entry already exists for this epic id).
- [ ] Ralph mode: PR URL is the sole stdout artefact; everything else routes through stderr.

---

## Cross-phase invariants

- **Hallucination guardrails** (see SKILL.md): every body claim traces to a payload field. Honest "unclear" beats plausible "wrong".
- **No raw diff content in body**: paths, churn, modules only.
- **No `gh pr merge`**: skill creates and exits.
- **NOT Ralph-blocked**: skill runs under Ralph; only behavior changes (no preview, force draft).
- **Body ≤8000 chars**: hard cap. Collapse in priority order (drop full file list → trim TL;DR → collapse mermaid to overview-only).
