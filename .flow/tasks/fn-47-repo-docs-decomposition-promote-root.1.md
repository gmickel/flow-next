---
satisfies: [R3, R5]
---

## Description

Extract dev-reference content from the legacy `plugins/flow-next/README.md` (2,719 lines) into 8 new focused files under `plugins/flow-next/docs/` (flat, no subdirs). Each new file is self-contained, reference-grade, and R17-compliant (link to canonical sources, never re-embed blocks).

**Size:** M+ (~700-900 lines of content extraction across 8 files; plus index doc)

**Files:**
- NEW: `plugins/flow-next/docs/architecture.md` (~115 lines)
- NEW: `plugins/flow-next/docs/spec-template.md` (~75 lines)
- NEW: `plugins/flow-next/docs/memory-schema.md` (~205 lines)
- NEW: `plugins/flow-next/docs/glossary.md` (~45 lines)
- NEW: `plugins/flow-next/docs/strategy.md` (~45 lines)
- NEW: `plugins/flow-next/docs/platforms.md` (~135 lines)
- NEW: `plugins/flow-next/docs/sync-codex.md` (~50-80 lines)
- NEW: `plugins/flow-next/docs/troubleshooting.md` (~80 lines)
- NEW: `plugins/flow-next/docs/README.md` (index page listing all 12 files with 1-line descriptions; existing 4 + new 8)
- LIGHT TOUCH: `plugins/flow-next/README.md` is NOT yet stubbed in this phase — the source content stays there for now (Phase 2 stubs it). Cross-link the new docs files INTO their plugin-README counterparts via "↑ Reference: …" lines so the new files reach the README content. Plugin README itself is unchanged in Phase 1.

## Approach

- **R17 cross-link discipline:** each new file's source content is **extracted into a self-contained doc** with its own scope, NOT a copy of the plugin README. Where plugin README explains a concept and the new doc would say the same thing, the new doc cites the canonical and adds detail (or vice versa once Phase 2 stubs the plugin README). For now: extract focused content from each source range; do NOT mechanically copy entire sections.
- **Sequence within Phase 1:** create the 8 leaf files in any order (no cross-file dep), then write `docs/README.md` index last (lists all 12).
- **Memory audit alongside:** `agent_docs/local-dev.md` may have references to plugin README sections being moved. Audit + redirect any matches as part of this task.
- **Codex mirror:** `scripts/sync-codex.sh` mirrors `plugins/flow-next/skills/` but NOT `docs/`. Run sync to verify no validation guard breaks; mirror regeneration should be a no-op for docs additions.
- **No version bump:** Phase 1 is docs-only per CLAUDE.md "For pure docs / agent_docs / README changes, do NOT bump the plugin version."

## Investigation targets

**Required** (read before authoring each file):

For `architecture.md`:
- `plugins/flow-next/README.md` §`.flow/ Directory` (lines 2377-2436), §Task Completion (2505-2535), §Flow vs Flow-Next (2536-2557), §Spec-first task model (81-96), §Separation of Concerns (2432-2436)

For `spec-template.md`:
- `plugins/flow-next/README.md` §Acceptance criteria (lines 1485-1559)
- `plugins/flow-next/templates/spec.md` — canonical scaffold; cross-link, don't re-embed (R17)
- fn-46 4-tier discovery cascade — cross-link to `flow-next-interview/SKILL.md:640-670` (the actual cascade walker)

For `memory-schema.md`:
- `plugins/flow-next/README.md` §Memory System (lines 1609-1813)
- `.flow/memory/` example tree (existing on disk for reference patterns)

For `glossary.md`:
- `plugins/flow-next/README.md` §Project Glossary (lines 1813-1856)
- `GLOSSARY.md` repo file (reference example)

For `strategy.md`:
- `plugins/flow-next/README.md` §Project Strategy (lines 1857-1900)
- `STRATEGY.md` repo file (reference example)

For `platforms.md`:
- `plugins/flow-next/README.md` §Other Platforms (lines 2579-2715) — Factory Droid (2581-2602), OpenAI Codex (2603-2705), Community Ports (2706-2715)
- `scripts/install-codex.sh` (for the install matrix detail)

For `sync-codex.md`:
- `scripts/sync-codex.sh` top-of-file comments (lines 2-141) — primary source
- `plugins/flow-next/README.md` lines 66, 1853, 1895 (cross-platform mentions) — secondary
- R6 grep validation guards (lines 1290+); R17/R19 drift guards
- fn-45 plain-text transform context (recent addition)

For `troubleshooting.md`:
- `plugins/flow-next/README.md` §Troubleshooting (lines 811-876), §Uninstall (877-889)

For `docs/README.md` index:
- `plugins/flow-next/docs/` current contents (`flowctl.md`, `ralph.md`, `teams.md`, `ci-workflow-example.yml`)

**Optional**:
- `.flow/memory/bug/build-errors/fn-44.5-review-r17-enforcement-beyond-2026-05-15.md` — R17 cross-link rule lesson (review-blocking if violated)
- `.flow/memory/bug/build-errors/codex-mirror-smoke-docs-miss-composed-2026-05-18.md` — `agent_docs/local-dev.md` audit reminder

## Key context

- **R17 is review-blocking.** Memory entry confirms: link to canonical sources (e.g. `templates/spec.md`, `scripts/sync-codex.sh` comments), do NOT re-embed blocks. One violation flips review to NEEDS_WORK.
- **`agent_docs/local-dev.md` audit:** smoke procedure may reference plugin README sections being extracted. Update any redirects in `local-dev.md` proactively.
- **Plugin README left untouched** in this phase. Phase 2 stubs it. This phase's mental model: "add focused references alongside the legacy README", not "replace the legacy README".
- **Each new file is offline-readable** and fork-survivable — relative paths only for cross-links (`../README.md`, `../scripts/sync-codex.sh`); never absolute `github.com/...` URLs.
- **Length discipline:** target ranges per file are upper bounds. If a file fits in fewer lines, ship the shorter version — that's better.
- **Sources can be paraphrased, not copy-pasted.** The new files should read as standalone reference docs — context, schema, examples — not as relocated README excerpts. Where plugin README has narrative flow, the new docs have terse reference shape (tables, lists, schemas first).
- **Codex mirror considerations:** sync-codex.sh doesn't mirror `docs/`. No transforms needed.
- **Cross-link patterns to use:** relative repo paths only (`../README.md`, `../scripts/sync-codex.sh`, `templates/spec.md`, `../../STRATEGY.md`). Test all paths render correctly on GitHub web UI before submitting.

## Acceptance

- [ ] 8 new files created in `plugins/flow-next/docs/` with the line-count targets above (upper bounds; ship shorter if natural).
- [ ] `plugins/flow-next/docs/README.md` index lists all 12 files (existing 4 + new 8) with 1-line descriptions each.
- [ ] R17 cross-link discipline verified: no large blocks copied from plugin README; canonical sources (`templates/spec.md`, `scripts/sync-codex.sh`, `STRATEGY.md`, `GLOSSARY.md`) are linked, not re-embedded.
- [ ] All cross-links use relative repo paths; no absolute `github.com/gmickel/flow-next/...` URLs.
- [ ] `agent_docs/local-dev.md` audited for stale references to plugin README sections that moved; any found are updated to point at the new `docs/<file>.md`.
- [ ] `./scripts/sync-codex.sh` runs cleanly (docs additions are not mirrored; no validation-guard breaks).
- [ ] `python3 -m unittest discover -s plugins/flow-next/tests` returns 612/612 (no regressions; tests don't reference docs/ directly).
- [ ] `cd /tmp && bash /Users/gordon/work/gmickel-claude-marketplace/plugins/flow-next/scripts/smoke_test.sh` returns 130/130.
- [ ] Plugin README (`plugins/flow-next/README.md`) is unchanged in this phase.
- [ ] Each new file renders correctly on GitHub web UI (open in browser, verify all cross-links resolve).

## Done summary
Phase 1 of fn-47 complete: added 8 new dev-reference docs (architecture, spec-template, memory-schema, glossary, strategy, platforms, sync-codex, troubleshooting) + `docs/README.md` index listing all 12 files in `plugins/flow-next/docs/`. R17 cross-link discipline observed throughout — canonical sources (`templates/spec.md`, `scripts/sync-codex.sh`, `STRATEGY.md`, `GLOSSARY.md`) are linked, never re-embedded. Each doc is a self-contained reference (tables, lists, schemas first; narrative second), not a copy of the plugin README. All cross-links use relative repo paths (no absolute github.com/... URLs for internal refs). Plugin README untouched (Phase 2 stubs it). `agent_docs/local-dev.md` audited — no stale section refs to redirect. Validation: 612/612 unit tests pass, 130/130 smoke pass, `./scripts/sync-codex.sh` idempotent with all guards (R6/R17/R19/R21/R30) passing. No version bump per CLAUDE.md docs-only policy.
## Evidence
- Commits: 4c2e92f12a67d5ccfe97653d0187bd14774cba9c
- Tests: python3 -m unittest discover -s plugins/flow-next/tests (612/612 passed), cd /tmp && bash /Users/gordon/work/gmickel-claude-marketplace/plugins/flow-next/scripts/smoke_test.sh (130/130 passed), ./scripts/sync-codex.sh (idempotent — 24 skills, 21 agents, hooks.json valid; all guards pass: R6 request_user_input, R17 DDD vocab, R19 strategy fluff, R21 spec-template dup, R30 legacy CLI vocab)
- PRs: