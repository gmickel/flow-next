---
satisfies: [R28]
---

## Description

Update all 5 documentation surfaces (CHANGELOG, plugin README, root CLAUDE.md, .flow/usage.md, public marketing site at ~/work/mickel.tech). The README has 9 distinct update points (per docs-gap-scout); the website has 4. Total ~14 doc updates.

**Size:** M (5 files, but many small edits across them)
**Files:** `CHANGELOG.md`, `plugins/flow-next/README.md`, `CLAUDE.md`, `.flow/usage.md`, `~/work/mickel.tech/app/apps/flow-next/page.tsx`

## Approach

### CHANGELOG.md (one new entry)

- Insert `## [flow-next 0.42.0] - <date>` block above the current top entry. Format follows recent entries (`### Added` / `### Changed` / `### Notes`). Entry highlights:
  - **`/flow-next:make-pr` — PR-as-cognitive-aid skill.** Five phases (pre-flight → gather → build body → mermaid → push+create). Renders a reviewable PR body from epic spec + tasks + decisions/bug/architecture-patterns memory + glossary changes + strategy alignment + deferred review findings + the diff. Mermaid codefences when diff crosses module boundaries (max 3 diagrams × 12 nodes). Uses `gh pr create --body-file` (not heredoc — LLM markdown safety). Default `--draft` if open items > 0 or under Ralph.
  - **`flowctl epic export-cognitive-aid` plumbing.** Aggregates 9 input streams into structured JSON. Reusable from skills + scripts.
  - **NOT Ralph-blocked.** PR creation is the autonomous-loop terminus; Ralph defaults to `--draft` for human review.
  - **NO cross-model review of the PR body.** Each harness's own model identifies critical changes from the structured input. `/flow-next:impl-review` already covers the *code itself*; doing it again on the PR description is double-counting.

### plugins/flow-next/README.md (9 update points per docs-gap-scout)

(a) **What's new banner** — line 24: update to 0.42.0, describe make-pr.

(b) **Lifecycle lede** — line 58: `"Seventeen slash commands"` → `"Eighteen"`. Insert `→ PR creation (\`make-pr\`)` after `epic-review` and before `resolve-pr`.

(c) **Commands count** — line 1821: `"Seventeen commands"` → `"Eighteen commands"`.

(d) **Commands table** — lines 1823-1841: insert new row after `/flow-next:epic-review`, before `/flow-next:resolve-pr`:
```
| `/flow-next:make-pr [<epic-id>] [flags]` | Render a cognitive-aid PR body from flow-next state (R-ID coverage, critical changes, decisions, deferred findings, mermaid) and open the PR via `gh pr create` |
```

(e) **Flags table** — lines 1870-1882: add row for make-pr with `--draft`, `--no-mermaid`, `--base <ref>`, `--memory`, `--dry-run`.

(f) **Command Reference section** — lines 2057+: add `#### \`/flow-next:make-pr\`` block. Mirror `/flow-next:resolve-pr` structure (input table, fenced usage, prose).

(g) **Table of Contents** — line ~43: add `- [PR Creation](#pr-creation) — \`/flow-next:make-pr\``.

(h) **New section** — `## PR Creation` (parallel to `## PR Feedback Resolution` at line 692): prose explaining cognitive-aid concept, 9 input streams, flags, safety (user-triggered + Ralph-safe + hard-errors on existing PR).

(i) **Codex invocation table** — lines 2509-2520: add `/flow-next:make-pr | Flow Make PR | $flow-next-make-pr` row.

### CLAUDE.md (1 update point)

- Lines 20-30 (Plugins → Commands): add `/flow-next:make-pr [<epic-id>] [--draft] [--no-mermaid] [--base <ref>] [--memory] [--dry-run]` entry. Insert at the natural lifecycle position (after `epic-review`, before `resolve-pr`).

### .flow/usage.md (1 update point)

- Add `flowctl epic export-cognitive-aid <epic-id> [--base <ref>] [--section <name>] [--json]` entry to the Common Commands section, grouped with other epic subcommands.

### ~/work/mickel.tech/app/apps/flow-next/page.tsx (4 update points — maintainer-only)

(a) **`commands` array** — lines 609-689: add new object after `/flow-next:epic-review` and before `/flow-next:resolve-pr`:
```typescript
{
  title: '/flow-next:make-pr',
  description: 'Render a cognitive-aid PR body from nine flow-next input streams (R-ID coverage, critical changes, decisions, memory, glossary, strategy, deferred findings, mermaid when modules cross), then open the PR via `gh`. NOT Ralph-blocked — autonomous-loop terminus, defaults to --draft for human review.',
},
```

(b) **Eyebrow** — line 1124: `"14 / Commands"` → `"15 / Commands"`.

(c) **Lede** — line 1125: `"Fourteen verbs. One disciplined workflow."` → `"Fifteen verbs. One disciplined workflow."`.

(d) **FAQ** — line 86+ (FAQS array): add new entry:
```typescript
{
  question: 'What is PR-as-cognitive-aid?',
  answer: '/flow-next:make-pr is the SDLC step between "all tasks done" and "human reviews the PR". It synthesizes nine flow-next state streams — epic spec with R-IDs, per-task done_summary + evidence commits, decisions / bug / architecture-patterns memory, glossary changes, strategy alignment, deferred impl-review findings, and the diff itself — into a structured PR body that maps every R-ID to its satisfying task + commit, surfaces critical changes (high-churn / cross-module / public interface / security-sensitive / behavior-visible), includes mermaid diagrams when the diff crosses module boundaries, and provides an explicit "where to look" reviewer-focus list. The framing comes from a simple observation: don\'t ask a human to skim a 10K-line diff — ask the agent to make those 10K lines reviewable. Each harness (Claude Code, Codex, Droid) is competent enough to identify critical changes from the structured input, so there\'s no second-model review pass on the body itself; /flow-next:impl-review already reviews the code. Uses gh pr create --body-file (not heredoc) for LLM-markdown safety. Default --draft when there are open items or running under Ralph; --ready overrides.',
},
```

## Investigation targets

**Required:**
- `CHANGELOG.md:5` — top entry to insert above; format pattern from 0.40.0 / 0.41.0 / 0.41.1
- `plugins/flow-next/README.md:24, 58, 692, 906, 1821-1841, 1870-1882, 2057+, 2509-2520` — all 9 update points
- `CLAUDE.md:20-30` — Plugins → Commands list
- `.flow/usage.md` — Common Commands section
- `~/work/mickel.tech/app/apps/flow-next/page.tsx:86, 609-689, 1124-1125` — website surfaces

**Optional:**
- `~/work/mickel.tech/app/apps/flow-next/page.tsx:142, 160` — existing FAQ structure (for the new FAQ entry's tone)
- `plugins/flow-next/README.md:906-948` — workflow mermaid diagram (could add make-pr branch but not required for v1)

## Design context

The website page is a Next.js / React component (`page.tsx`). Updates are TypeScript object additions to existing arrays — no new components, no styling changes. Match existing entries' tone (single-paragraph descriptions, no markdown formatting in `description` field).

## Acceptance

- [ ] `CHANGELOG.md` has new `## [flow-next 0.42.0]` entry above the current top, describing the skill + flowctl plumbing + key design choices (no cross-model review, NOT Ralph-blocked, mermaid).
- [ ] `plugins/flow-next/README.md` has all 9 update points applied: banner, lifecycle lede, commands count, commands table row, flags table row, Command Reference block, ToC entry, new PR Creation section, Codex invocation table row.
- [ ] `CLAUDE.md` Plugins → Commands list includes the new `/flow-next:make-pr` entry.
- [ ] `.flow/usage.md` Common Commands includes `flowctl epic export-cognitive-aid` entry.
- [ ] `~/work/mickel.tech/app/apps/flow-next/page.tsx` has 4 updates applied: commands array entry, eyebrow `14 → 15`, lede `Fourteen → Fifteen`, new FAQ entry.
- [ ] All Markdown files render correctly (`mdcat` or similar smoke check).
- [ ] No broken intra-repo links (R-ID coverage table links resolve, `.flow/specs/...` links work).
- [ ] Website page TypeScript compiles cleanly (no syntax errors in commands array / FAQS array additions).

## Done summary

_(populated by /flow-next:work after task completes)_

## Evidence

_(populated by /flow-next:work after task completes)_
