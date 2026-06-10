---
satisfies: [R8]
---

## Description

Docs (repo + flow-next.dev), GLOSSARY "Ready" term, Codex mirror regeneration, and the 1.12.0 release mechanics.

**Size:** M
**Files:** repo: `GLOSSARY.md`, `plugins/flow-next/docs/architecture.md`, `plugins/flow-next/docs/flowctl.md`, `plugins/flow-next/docs/tracker-sync.md`, `plugins/flow-next/skills/flow-next-setup/templates/usage.md`, `CHANGELOG.md`, version files (bump.sh), `plugins/flow-next/codex/**`; site: `src/content/docs/specs/writing-specs.mdx`, `flowctl/commands.mdx`, `flowctl/configuration.mdx`, `teams/tracker-sync.mdx`, `skills/{capture,interview,plan}.mdx`, `releases/changelog.mdx`, `src/lib/site.ts` FLOW_NEXT_VERSION, `package.json`

## Approach

- **GLOSSARY.md**: new `## Ready` H2 after `## Spec` — one paragraph, existing format (human-owned/tracker-projected, default false, orthogonal to status, the loop entry gate).
- **Repo docs**: architecture.md spec-JSON field list gains `ready` (+ rewrite-reset note); flowctl.md gains `spec ready`/`unready` H3s (set-branch pattern), the listings-badge + `--json` notes, the `tracker.readyState` config row, epic-alias table rows; tracker-sync.md gains a "Readiness projection" subsection (one-way pull, name/label match, change-only receipts, not-found degradation); usage.md spec-commands block gains both commands.
- **Site**: writing-specs.mdx — give the existing `Ready["Spec ready?"]` mermaid diamond concrete meaning + "Before planning" prose; commands.mdx + configuration.mdx rows; teams/tracker-sync.mdx ceremony + projection notes; capture/interview/plan skill pages gain their one-paragraph behavior notes; changelog `### 1.12.0 — Spec readiness signal` per strict format; FLOW_NEXT_VERSION + package.json. NO new pages → navbars untouched (verify both sources still list edited pages). self-improving page: no change (readiness is a gate, not a compounding loop).
- **Release**: `scripts/bump.sh minor flow-next` (1.11.0 → 1.12.0, all manifests); `./scripts/sync-codex.sh` regen — **mirror audit**: the .2/.3 skill edits include two net-new AskUserQuestion prompts (mark-ready, plan soft-check) — verify both transform to numbered prompts in the mirror; CHANGELOG keep-a-changelog entry. `pnpm build` green; site commits separate; hold site push until the release tag lands (site CLAUDE.md rule).

## Investigation targets

**Required:**
- `agent_docs/releasing.md` — bump → sync-codex → CHANGELOG → site-changelog sequence
- `GLOSSARY.md` — term format to match
- `~/work/flow-next.dev/src/content/docs/releases/changelog.mdx` — 1.11.0 entry as the format model

**Optional:**
- `plugins/flow-next/docs/flowctl.md:104-200, 536-543, 1321` — command/config/alias table shapes
- `scripts/sync-codex.sh:170-296` — rewrite rules the new prompts must pass through

## Acceptance

- [ ] GLOSSARY `## Ready` + all repo-doc edits above land; epic-alias rows included
- [ ] Site pages updated; changelog entry per strict format; versions bumped; `pnpm build` green; navbars verified-untouched
- [ ] Mirror regenerated; both net-new prompts verified transformed; CHANGELOG + bump.sh 1.12.0 (all manifests lockstep)
- [ ] Site commit separate + unpushed until tag (release sequence owns the push)

## Done summary
Shipped the fn-58 readiness docs + 1.12.0 release mechanics: GLOSSARY "Ready" term, architecture/flowctl/tracker-sync/usage.md repo docs (spec ready/unready, explicit-ready JSON + badge, tracker.readyState row, epic alias rows, readiness-projection section), CHANGELOG 1.12.0 entry, version bump across all manifests (lockstep), and the regenerated Codex mirror with all net-new AskUserQuestion sites verified as plain-text numbered prompts. Site repo (flow-next.dev) updated in a separate unpushed commit (c942a44): writing-specs ready-flag section, cli-reference/configuration rows, tracker-sync ceremony + projection, capture/interview/plan behavior notes, strict-format 1.12.0 changelog entry, FLOW_NEXT_VERSION/package.json bumps; pnpm build green; both navbars verified untouched. RP impl-review (merge-base scope, full feature surface): SHIP, all R1-R8 met.
## Evidence
- Commits: 9550a65e593eee614e2d8c5369fed002f3350441, site:c942a448b93335f501fec68db08485db5c47a408
- Tests: cd plugins/flow-next && python3 -m unittest discover -s tests -p 'test_*.py' (1047 tests green after dogfood usage.md parity fix), cd ~/work/flow-next.dev && pnpm build (58 pages, green), mirror byte-idempotency: md5-of-md5s identical across second sync-codex.sh run, mirror ask-site audit: 4 net-new sites (capture mark-ready, interview mark-ready, plan soft-check, ceremony readyState) verified transformed; 1 R2 block per file; no mid-table/mid-codeblock injection
- PRs: