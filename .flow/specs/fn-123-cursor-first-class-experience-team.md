## Conversation Evidence

> user: "we recently did a bunch of work optimizing the plugin setup for claude code and fixing issues with the codex mirror ... what can we do to make the cursor experience better, as good as posible, we have a company joining soon that will use flow-next only in cursor and i want to make it great"
> user: "i think at least the .cursor/marketplace stuff could help and so far our tests have shown that cursor is largely compatible with claude code plugins"
> user: "we dont need to support ralph in cursor imo"
> user: "subagents work i have tested that"
> user: "read the publisher terms, if too draconic, then we can stay on the enterprise can install from a repo story" (terms reviewed: verdict too one-sided; public marketplace rejected)
> user: "when we capture the spec we need to redo usage.md and cursor host aware stuff during setup to still allow the other backends but also a new option, review backend host or something that would then use the cursor model pins and everything?"
> user: "they can also just use AGENTS.md to define default behaviour, perhaps if our orchestration piece that we CAN influecne during setup in a sspecific host harness using the correct model ides, the fastJudge stuff etc is set correctly then it would work?"
> user (re frontmatter-alias translation): "Document the degrade ... yea i agree"
> Dogfood evidence (live Cursor session, 2026-07-22, scratch repo): AskUserQuestion renders natively (single + multi-question batches, auto "Other...", Skip honored - cancelled interview made no spec changes); subagent dispatch + parallel fan-out work; explicit subagent model pins honored via Cursor slugs (e.g. `claude-opus-4-8-thinking-high`; host self-corrects near-miss ids); `agents/*.md` frontmatter family aliases IGNORED - subagents inherit the session model; `disallowedTools` not consumed by Cursor (its native field is `readonly: true`); slash autocomplete lists commands in hyphenated form (`/flow-next-plan`); natural-language skill triggering works; `/flow-next-setup`, plan (scouts + spec/task writes via `.flow/bin/flowctl`), and interview all green end-to-end; cross-family pinned reviewer subagent over a dirty diff works.

## Goal & Context

<!-- Source-tag breakdown: 60% [user], 35% [paraphrase], 5% [inferred] -->

A company is onboarding soon that will use flow-next exclusively inside Cursor. Make the Cursor experience first-class: frictionless team-wide install with automatic updates, and the full orchestration doctrine (model tiering, cross-family review) surviving on the Cursor host.

Dogfooding (see Conversation Evidence) confirmed Cursor is largely at parity with Claude Code for flow-next: native structured asks, subagent dispatch with honored model pins, working plan/interview/flowctl flows. The real gaps are install mechanics, host-aware model routing, a silent read-only-agent enforcement hole, and stale limitation claims in our own docs.

Cursor Teams/Enterprise can import a GitHub repo directly as a team marketplace, with Default Off / Default On / Required install modes and auto-refresh on push (Cursor GitHub App) - this replaces the local `install-cursor.sh` copy + restart + manual re-run cycle for the onboarding company.

Public-marketplace publishing is REJECTED on publisher-terms review: uncapped one-sided publisher indemnification (including "any claim by a User arising from the Plugin" and "any security vulnerability related to the Plugin") against a $100 Anysphere liability cap, a clause making Anysphere's granted rights control over the OSS license where they conflict, promo-material rights surviving removal, and unpaid use of the publisher's name/marks. The team-marketplace repo-import story delivers the same install value with none of those terms.

## Architecture & Data Models

<!-- Source-tag breakdown: 50% [user], 40% [paraphrase], 10% [inferred] -->

- Cursor consumes canonical plugin files AS-IS (no rewrite pass exists, unlike the Codex mirror). Everything shipped for Cursor must be canonical-safe on all hosts. [paraphrase]
- Orchestration doctrine relocates on Cursor: agent-frontmatter tiering (ignored there) is replaced by setup-scaffolded AGENTS.md routing rules + caller-side dispatch pins using Cursor model slugs (verified honored). [user]
- Cursor-native agent frontmatter facts (dogfood + Cursor docs): `model:` accepts `inherit` or Cursor model ids with bracket params; unknown/unavailable ids silently fall back; `readonly: true` restricts writes; `tools`/`disallowedTools` are not consumed. [paraphrase]

## Boundaries

- NO Ralph support on Cursor - explicitly out of scope. [user]
- NO public Cursor marketplace submission - rejected on publisher terms; revisit only if discovery demand appears later. [user]
- NO frontmatter alias-to-slug rewrite pass in installers - the recommended install path (marketplace repo import) consumes canonical files with no rewrite hook; document the degrade instead. [user]
- Existing review backends (codex, copilot, cursor CLI, rp) all remain available; `host` is additive, never a replacement. [user]
- Cursor hooks work (full agent-hook set + Claude Code hook compat exists upstream) but flow-next builds nothing on them in this spec; only false "hooks don't fire on Cursor"-style claims get corrected as part of R10. [paraphrase]

## Acceptance Criteria

- **R1:** Root `.cursor-plugin/marketplace.json` exists (alongside the existing `.claude-plugin/marketplace.json`); the GitHub repo imports cleanly as a Cursor team marketplace with flow-next installable, and Default On / Required install modes + auto-refresh on push work. [user]
- **R2:** `plugins/flow-next/.cursor-plugin/plugin.json` declares explicit component paths (skills, agents, commands) so repo-sourced marketplace installs never discover `codex/` mirror skills or `tests/`. [paraphrase]
- **R3:** Codex-vs-Cursor host detection in setup no longer keys on `codex/` directory ABSENCE (which breaks under whole-repo marketplace import where `codex/` is present); it switches to a positive signal. [inferred]
- **R4:** All read-only agents (scouts, reviewers) carry Cursor-native `readonly: true` frontmatter; Claude Code parsing and the sync-codex mirror tolerate the extra key (sync twice-idempotent, guards green). Closes the gap where `disallowedTools` is silently ignored on Cursor, leaving scouts with write access. [inferred]
- **R5:** New review-backend option `host`: review runs as a fresh-context subagent pinned via the HOST's model slugs to a family that did not write the diff. On Cursor this uses in-prompt slug pins (verified working); on Claude Code it maps to the existing native reviewer-subagent arrangement. All existing backends remain selectable. [user]
- **R6:** Setup is host-aware on platform=cursor: the review-backend menu leads with `host` (recommended) and demotes Cursor CLI (circular from inside Cursor); setup scaffolds the AGENTS.md model-routing section with real Cursor slugs enumerated at setup time (host agent enumeration or `cursor-agent --list-models`) plus dispatch-pin routing rules (cheap slug for read-only scouts, cross-family slug for review, inherit otherwise), date-stamped with a re-run-setup-to-refresh note. [user]
- **R7:** usage.md gains a host=Cursor orchestration section: slug pin grammar, id volatility + enumeration, cross-family pairing rule, and orchestration recipes reframed for a Cursor host. [user]
- **R8:** Docs state the tiering degrade explicitly: on Cursor, `agents/*.md` family aliases resolve to inherit (session model); caller-side pins are the escape hatch. No alias-to-slug rewrite is built. [user]
- **R9:** The plugin ships `rules/flow-next.mdc` - a Cursor-native guidance rail carrying the flowctl lifecycle commands + the `flowctl usage` pull directives (Cursor analog of the fn-121 slim snippet; setup still writes `.flow/bin/flowctl` since Cursor has no plugin-root env vars or bin PATH injection). [inferred]
- **R10:** Stale Cursor caveats corrected everywhere they appear (install-cursor.sh output, platforms.md, flow-next.dev): slash autocomplete DOES list commands (hyphenated form, e.g. `/flow-next-plan`); natural-language skill triggering works; AskUserQuestion is native including multi-question batches; outdated hooks-limitation claims corrected. [paraphrase]
- **R11:** CI validates the Cursor surface: marketplace.json/plugin.json manifest checks plus name/description frontmatter present on every skill/agent/command (mirroring Cursor's marketplace review checklist), extending the existing verify_cursor_install.py / Cursor test suite. [inferred]
- **R12:** Downstream docs walk: platforms.md Cursor section rewritten with team-marketplace repo import as the recommended install (local script retained as fallback), flow-next.dev updated in the same workstream, plus a short admin onboarding runbook (import repo, set install mode, per-repo `/flow-next-setup`). [paraphrase]
- **R13:** Read-back asks never embed long content: skills that show a draft/diff for approval (capture Phase 4, and any other skill embedding multi-paragraph drafts in an ask body) print the full draft as a normal assistant markdown message FIRST, then issue a short AskUserQuestion (one-line pointer + [inferred] tally + options). Rationale: question bodies render as plain collapsed text (no markdown, no newlines - observed in Claude Code desktop during this spec's own read-back), making embedded drafts unreadable on every host. Reuse the existing print-then-ask pattern already used elsewhere; prose-only change, no new machinery. [user]

## Decision Context

### Motivation

- Why now: a company is joining soon that will use flow-next only in Cursor; the experience must be great on day one. [user]
- Team-marketplace repo import chosen over public marketplace submission: same install value (one-click, auto-updating, org-enforceable) with none of the indemnity/license/marks terms. [user]
- Orchestration relocated from agent frontmatter (ignored on Cursor) to setup-scaffolded AGENTS.md routing + in-prompt dispatch pins, which dogfooding verified are honored. [user]
- Strategy alignment: extends the Cross-platform parity track (Cursor is a first-class host in the roster). [strategy:Cross-platform parity]

## Requirement coverage

| R-ID | Task |
|------|------|
| R1 | fn-123-cursor-first-class-experience-team.1 |
| R2 | fn-123-cursor-first-class-experience-team.1 |
| R3 | fn-123-cursor-first-class-experience-team.4 |
| R4 | fn-123-cursor-first-class-experience-team.2 |
| R5 | fn-123-cursor-first-class-experience-team.3 |
| R6 | fn-123-cursor-first-class-experience-team.4 |
| R7 | fn-123-cursor-first-class-experience-team.6 |
| R8 | fn-123-cursor-first-class-experience-team.6 |
| R9 | fn-123-cursor-first-class-experience-team.1 |
| R10 | fn-123-cursor-first-class-experience-team.7 |
| R11 | fn-123-cursor-first-class-experience-team.1 |
| R12 | fn-123-cursor-first-class-experience-team.7 |
| R13 | fn-123-cursor-first-class-experience-team.5 |
