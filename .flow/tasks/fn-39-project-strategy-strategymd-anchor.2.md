# fn-39-project-strategy-strategymd-anchor.2 flow-next-strategy skill + slash command + references

## Description
Create the `/flow-next:strategy` skill: canonical `SKILL.md`, two reference files (`interview.md`, `strategy-template.md`), and the slash-command file. The skill is the editor — runs the interview via host agent's `AskUserQuestion`, applies pushback rules, writes `STRATEGY.md` via `Write` per-section atomically.

**Size:** M
**Files:**
- `plugins/flow-next/skills/flow-next-strategy/SKILL.md` (new)
- `plugins/flow-next/skills/flow-next-strategy/references/interview.md` (new)
- `plugins/flow-next/skills/flow-next-strategy/references/strategy-template.md` (new)
- `plugins/flow-next/commands/flow-next/strategy.md` (new)

Depends on Task 1 (consumes `flowctl strategy status` JSON shape).

## Approach

Build the skill around the locked Rumelt-derived template (5 required + 2 optional sections, no Marketing) with these flow-next conventions:

- **Bare `AskUserQuestion`** in canonical `SKILL.md` — NO inline cross-platform tables (multi-platform listings naming `AskUserQuestion / request_user_input / ask_user / pi-ask-user` are forbidden by flow-next CLAUDE.md). Optional parenthetical breadcrumb `(sync-codex.sh rewrites this to request_user_input in the Codex mirror)` is fine for maintainer clarity — sync-codex strips it.
- **No `Marketing` optional section** in `strategy-template.md` — over-rotated for OSS-tools repo. Keep `Milestones` + `Not working on` as the two optional sections.
- **Lead-with-recommendation only on routing questions** — the substance questions (Target problem / Approach / Persona / Metrics / Tracks) stay free-form so the user's own language is preserved. The "which section to revisit?" question on re-run uses lead-with-recommendation pattern.
- **Foreign-file refusal** — Phase 0 calls `flowctl strategy status --json`; if `exists: true AND generator_match: false`, fire `AskUserQuestion` ("migrate / keep / rewrite?"). Migrate = exit (defer to v2). Keep = exit. Rewrite = second confirmation prompt then proceed.
- **Per-section atomic writes** — each completed section's body lands on disk via `Write` before the next prompt fires. Re-runs read existing sections via `flowctl strategy status` and ask which empty/stale to fill next.
- **Subdirectory walk-up** — Phase 0 detects via `flowctl strategy status` (which uses `find_strategy_file`); surfaces "Using repo-root STRATEGY.md at `<path>`" line in chat before any question fires.
- **Ralph block** — Phase 0 first check: if `FLOW_RALPH=1` or `REVIEW_RECEIPT_PATH` is set, exit 2 with stderr `[STRATEGY: user-triggered only — Ralph cannot run /flow-next:strategy]` (mirrors `/flow-next:prospect` precedent).

`SKILL.md` structure:
- Frontmatter: `name: flow-next-strategy`, `description`, `user-invocable: false`, `allowed-tools: AskUserQuestion, Read, Write, Bash`
- Phase 0: route by file state via `flowctl strategy status` (Ralph block check first; foreign-file check second; husk vs exists vs absent routing third)
- Phase 1: first-run interview (5 required sections in Rumelt-kernel order, then optional sections gated by `AskUserQuestion`)
- Phase 2: update run (which-section-to-revisit, preserve untouched sections, bump `last_updated`)
- Phase 3: downstream handoff (suggest `/flow-next:prospect` or `/flow-next:plan` as next step if nothing has run yet on this repo)

`references/interview.md` — pushback rules and anti-pattern taxonomy:
- Five Overall Rules (ask-don't-prescribe, push back once-or-twice, quote the user's own words back, cap each answer at 1-3 sentences, do not leak anti-pattern names to user)
- Per-section structure: opening question → strong-answer signature → named anti-patterns + sharper follow-up → 2-round cap → capture rule
- Anti-patterns per section (Rumelt's bad-strategy hallmarks: goal-stated-as-problem / fluff/values / vanity metrics / feature-list-as-track / etc.)

`references/strategy-template.md` — literal markdown skeleton:
- Frontmatter with `name`, `last_updated`, `generator: flow-next-strategy`
- 5 required H2 sections in locked order (Rumelt kernel + persona + metrics), with placeholder bodies showing the right shape
- 2 optional sections (Milestones, Not working on) — Marketing deliberately excluded
- Post-write checklist: metrics 3-5, tracks 2-4, no section >4 sentences except Tracks, Target problem ↔ Approach connected

`commands/flow-next/strategy.md` — 14-line minimal forwarder, mirror `commands/flow-next/audit.md` shape. Pass `$ARGUMENTS` verbatim to skill. Argument hint: `[optional: section to revisit, e.g. 'metrics' or 'approach']`.

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-audit/SKILL.md` — canonical agent-native skill template, blocking-question canonical phrasing (model for SKILL.md frontmatter + tool-name conventions)
- `plugins/flow-next/skills/flow-next-prospect/SKILL.md` — Ralph-block pattern (search for `FLOW_RALPH` / `REVIEW_RECEIPT_PATH`)
- `plugins/flow-next/commands/flow-next/audit.md` — slash-command 14-line forwarder shape
- Richard Rumelt — *Good Strategy Bad Strategy* — kernel structure (diagnosis / guiding policy / coherent action) and the "fluff / mistaking goals for strategy / bad strategic objectives" hallmark labels used in pushback rules

**Optional:**
- `plugins/flow-next/skills/flow-next-interview/SKILL.md:141-162` — lead-with-recommendation pattern (apply to routing questions only)
- `plugins/flow-next/skills/flow-next-capture/workflow.md` — mandatory read-back before write convention

## Key context

- Canonical skill files use Claude-native tool names: `AskUserQuestion`, `Read`, `Write`. NO inline cross-platform tables. sync-codex.sh rewrites for Codex.
- Substance questions stay free-form (ask, don't prescribe). Routing questions get lead-with-recommendation.
- Anti-pattern labels (vanity / fluff / feature-list) used internally to formulate questions, NEVER shown to user.
- 2-round pushback cap per section. After round 2: capture user's words verbatim + add `<!-- worth revisiting -->` HTML comment.
- Foreign-file detection: `generator_match: false` from `flowctl strategy status` → blocking question. v1 refusal stance, no migration.
- Ralph block fires before any other Phase 0 logic.
## Acceptance
- [ ] `plugins/flow-next/skills/flow-next-strategy/SKILL.md` created with frontmatter (`name: flow-next-strategy`, `description`, `user-invocable: false`, `allowed-tools: AskUserQuestion, Read, Write, Bash`); Phase 0 (route + Ralph block + foreign-file check), Phase 1 (first-run interview), Phase 2 (section-revisit update), Phase 3 (downstream handoff).
- [ ] Canonical SKILL.md uses bare `AskUserQuestion` — NO inline cross-platform table (no `request_user_input` / `ask_user` / `pi-ask-user` listings in canonical prose). Optional parenthetical maintainer breadcrumb is fine.
- [ ] `references/interview.md` (~150 lines) loaded non-optionally — improvising pushback from memory produces passive transcription. Five Overall Rules: ask-don't-prescribe, push back once-or-twice, quote the user's own words, cap each answer at 1-3 sentences, do not leak anti-pattern names to user. Per-section pushback rules with named anti-pattern labels (internal-only) for all 5 required sections + 2 optional.
- [ ] `references/strategy-template.md` (~90 lines) — frontmatter (`name`, `last_updated`, `generator: flow-next-strategy`), H1 `# {{product_name}} Strategy`, 5 required H2 sections in locked Rumelt-kernel order, 2 optional sections (Milestones, Not working on). Marketing section explicitly NOT included.
- [ ] `plugins/flow-next/commands/flow-next/strategy.md` created — 14-line forwarder mirroring `commands/flow-next/audit.md` shape. Frontmatter has `argument-hint: [optional: section to revisit, e.g. 'metrics' or 'approach']`. Body says "MUST invoke flow-next-strategy skill, pass $ARGUMENTS verbatim."
- [ ] Phase 0 Ralph-block check fires first: when `FLOW_RALPH=1` OR `REVIEW_RECEIPT_PATH` is set, skill exits 2 with stderr `[STRATEGY: user-triggered only — Ralph cannot run /flow-next:strategy]`.
- [ ] Phase 0 calls `flowctl strategy status --json`. Routes:
      - File absent → Phase 1 (first-run interview)
      - File exists + `generator_match: false` → foreign-file `AskUserQuestion` (migrate / keep / rewrite); migrate exits "deferred to v2"; keep exits without writing; rewrite confirms via second prompt
      - File exists + `generator_match: true` → Phase 2 (section-revisit interview)
- [ ] Phase 0 surfaces "Using repo-root STRATEGY.md at `<path>`" in chat when invoked from a subdirectory (path differs from cwd).
- [ ] Phase 1 runs interview in section order: Target problem → Our approach → Who it's for → Key metrics → Tracks. Optional sections (Milestones, Not working on) gated by `AskUserQuestion` "include this section?" routing question with lead-with-recommendation (`[your-call]` confidence).
- [ ] Substance questions (problem/approach/persona/metrics/tracks) use FREE-FORM responses — no menu options, no recommendation in question body. Routing questions (which section to revisit, include optional section) use single-select with lead-with-recommendation pattern + confidence tier.
- [ ] Per-section atomic writes: each completed section's content written via `Write` before next question fires. `last_updated` bumps on every save. Verify by reading file mid-flow — partial state is on disk.
- [ ] Pushback discipline: 2 rounds maximum per section. After round 2, capture user's words verbatim + append HTML comment `<!-- worth revisiting -->` to section body. Anti-pattern labels (vanity / fluff / feature-list) NEVER appear in question bodies.
- [ ] Phase 2 (re-run on existing flow-next-generated file): asks "which section to revisit?" via `AskUserQuestion` with lead-with-recommendation favoring sections without populated body or with `<!-- worth revisiting -->` markers. Untouched sections preserved byte-identical.
- [ ] Phase 3 (downstream handoff): if no `.flow/` epics or prospects exist, suggest `/flow-next:prospect` as next step. If `.flow/` populated, just note that prospect/plan/interview/capture will pick up the strategy on next invocation.
- [ ] Mandatory read-back before final commit: after all sections answered (first run) or section update (re-run), show full draft in chat via `Read` of the candidate file, offer one round of edits, then commit (mirrors `/flow-next:capture` pattern).
- [ ] Skill follows CLAUDE.md "agentic vs deterministic" rule — host agent runs interview directly, no subprocess to other LLMs, no Python parsing engines (uses `flowctl strategy read/status/list` for atomic reads).
## Done summary
Authored flow-next-strategy skill (canonical SKILL.md + 2 references files + 14-line slash-command forwarder). Section structure derived from Rumelt's strategy kernel (diagnosis / guiding policy / coherent action) extended with persona + metrics. flow-next conventions: Marketing section deliberately excluded, bare AskUserQuestion in canonical, lead-with-recommendation only on routing questions, foreign-file refusal via generator sentinel, Ralph-block exit-2, per-section atomic writes, mandatory read-back. Phase 0 logic validated against Task 1 flowctl strategy status JSON contract via fixture round-trip.
## Evidence
- Commits: 0f50ea96219f44e933ae70cb5e0c6d8f8a883e86
- Tests: grep -nE 'request_user_input|ask_user|pi-ask-user' canonical files (only allowed parenthetical breadcrumb on SKILL.md line 18), grep -niE 'synergy|pivot|disrupt|thought-leadership|best-in-class|world-class|10x' (PASS — none in canonical), wc -l on 4 files (SKILL.md 266, interview.md 151, strategy-template.md 86, strategy.md 13), fixture round-trip: flowctl strategy status --json against absent / husk / valid / foreign-generator STRATEGY.md (all 8 documented fields present + match Phase 0 routing logic)
- PRs: