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

- [ ] Decisions made section: per-entry summary from `memory.decisions[]`. "No decisions for this epic" line if empty.
- [ ] Memory left behind section: bug + pattern entries with id + 1-line synopsis + path.
- [ ] Glossary/strategy notes: glossary changes table (term / status / rationale); strategy alignment block verbatim.
- [ ] Open items: deferred review findings, uncovered R-IDs, follow-up tasks.
- [ ] Where to look: top files by churn + reviewer focus list.

---

## Phase 3: Mermaid (fn-42.5)

**Done when:**

- [ ] `--no-mermaid` short-circuits before any generation.
- [ ] Trigger evaluation: ≥1 of (module-boundary crossings, public interface changes, new top-level dir, fan-out epic) fires → continue. Zero triggers → omit `## Structural changes` section entirely.
- [ ] Diagrams capped: max 3 per PR, max 12 nodes per diagram, max 25 edges, max 12K chars per codefence.
- [ ] Fallback prose paragraph above each diagram describes the structural change in plain language.
- [ ] Mermaid syntax avoids reserved words as node IDs and quotes special characters in labels.
- [ ] `mermaid-rules.md` ref file written.

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
