---
satisfies: [R13, R14, R15, R21, R22, R23, R26, R40, R42]
---
# fn-151-front-door-overhaul-value-first-landing.3 README recomposition, canonical tiering, and changelog

## Description
Recompose the README to the spine, resolve the harness-tiering contradiction at its canonical source, strip counts from front-door prose, and open an Unreleased section in the repository changelog.

**Size:** M
**Files:** `README.md`, `CHANGELOG.md`, `plugins/flow-next/docs/platforms.md`

### Approach

**Target roughly 360 lines from 500, keeping every existing section.** The saving comes from demoting inventory, not from deleting content.

Section order:

1. Badges, trimmed to five: stars, CI, latest release, awesome-list, license. Discord and Sponsor already appear in the footer.
2. Hero block: tagline, the problem line ("Implementation got cheap. Reviewing it, verifying it, and keeping a codebase coherent did not."), one claim sentence, then the pipeline GIF. The GIF is the best asset on the page and belongs immediately below the fold line.
3. Why this exists, compressed to three paragraphs. Keep the touch-point argument as prose. Convert the SlopCodeBench block from a single dense paragraph into a lead sentence plus four scannable bullets plus the honest close, same facts, same citation.
4. What you get: the six outcome headings, word-for-word identical to the landing page's, two lines each. Demote the seven-row tenet table into a `<details>` block for readers who want the vocabulary.
5. Where it already runs, moved up from line 346 to roughly line 90: breadth paragraph, honest-asymmetry paragraph, linked open-source record, then the three verified quotes.
6. Quick start: install table and five-command path, unchanged. It works.
7. The pipeline is a menu, not a rail: trimmed by about a third. The doctrine lines and the plain-language invocation point are load-bearing; keep both. Natural-language invocation is stated as a first-class capability, not a footnote.
8. How the flow works: mermaid plus the six collapsible stages, unchanged.
9. Going autonomous: trimmed lightly.
10. Why it works: the problem-to-solution table unchanged. It is the best table in the document.
11. What Flow-Next is not: unchanged. Scope honesty reads as confidence.
12. Commands: move the 25-row table into a `<details>` block or replace with a link to `docs/skills.md`. Inventory in the middle of a narrative is what makes the page feel like a manual.
13. Requirements, platforms, ecosystem, contributing, license, footer: unchanged.

**Harness tiering, the canonical statement.** `plugins/flow-next/docs/platforms.md` is the single home. Write it once there:

> First-class on Claude Code, OpenAI Codex, Factory Droid, Cursor, and xAI Grok Build. Community port for OpenCode.

Grok Build meets the same standard Cursor already does: its own setup detection signal (`GROK_AGENT=1`, fn-126), canonical plugin files consumed as-is, slash commands, verified multi-agent flows. Ralph is intentionally not built for either. Today three surfaces disagree: `README.md:62` calls Grok and Cursor "runs on", the README platforms table two hundred lines later calls Cursor "First-class", and the docs site calls all five first-class. Make README prose and the README table both restate the canonical sentence. Task 3 aligns the docs-site sentence.

**Counts.** R13 bans counts in front-door prose and R25 requires accuracy where a count legitimately remains. The split: `README.md:53` ("28 agent-native skills") and `README.md:113` ("merges all 22 agents") are front-door prose, so the numbers come out; say "the bundled agents" and link the catalog. The demoted reference tail at `README.md:395,416` and `platforms.md:133,180` are reference content, so counts stay and are corrected: 21 agents, not 22.

**Scope claims phrased for fn-135.** Write claims so chart swaps a noun rather than a clause. "From the conversation you already had to a merged pull request" becomes "from an idea nobody has shaped yet to a merged pull request" with one word changed. Do not claim complete idea-to-merge coverage yet; the ideation edge is genuinely open by design until chart ships.

**`CHANGELOG.md`.** No `## Unreleased` section exists; the top entry is the released 3.9.0. Create one above it, matching this file's keep-a-changelog subsection style (`### Added` / `### Changed` / `### Documentation`). No version bump.

**Em dashes.** 83 in this file. Replace per sentence with a comma, colon, period, parentheses, or a double hyphen chosen for that sentence. A global substitution reads worse than the original and will need redoing. One curly quote, also fix, unless it sits inside a verbatim third-party quotation.

**Emoji.** 33 lines carry emoji. Keep the four marking navigation affordances (docs, Discord, teams, autonomous); drop the decorative ones inside prose and the mermaid diagram.

### Investigation targets

**Required:**
- `README.md:39-66` - the "Why this exists" essay and tenet table being recomposed
- `README.md:333-352` - the adoption and breadth evidence being promoted
- `plugins/flow-next/docs/platforms.md:3,19-27,133,180` - canonical tiering home and the count occurrences
- `CHANGELOG.md:1-20` - the keep-a-changelog subsection style to match
- `agent_docs/releasing.md` - changelog register rules

**Optional:**
- `.flow/specs/fn-151-front-door-overhaul-value-first-landing.md` - the six canonical outcome headings, which must match the landing exactly

### Key context

Register for this file is a skeptical staff engineer. Proof before adjectives.

Two adjacent specs also touch `README.md`: fn-135 task 7 and fn-142. Neither is landed. Do not attempt to pre-merge their content; just do not delete anything that would make their later insertion awkward.

Copy rules apply to every word: no em dashes, straight quotes only outside verbatim quotations, flat present-tense claims with no hedging qualifier, no "not X but Y" construction beyond the two grandfathered lines already in the file, and none of the banned phrases listed in task 1. No process or speed self-praise: release cadence and issue-closure rate are true and banned.

## Acceptance
- [ ] README follows the spine and lands at roughly 360 lines with every existing section retained
- [ ] Adoption and breadth evidence appears within the first quarter of the document
- [ ] SlopCodeBench material is a lead sentence plus scannable bullets, not one dense paragraph
- [ ] The six outcome headings are word-for-word identical to the landing page's
- [ ] The command inventory is demoted out of the main narrative
- [ ] `platforms.md` carries the canonical tiering sentence; README prose and the README platforms table both restate it; no surface contradicts another
- [ ] `README.md:53` and `README.md:113` carry no counts; the demoted reference tail and `platforms.md` carry corrected counts of 21 agents
- [ ] Scope claims are phrased so fn-135 changes a noun rather than a clause; no claim of complete idea-to-merge coverage
- [ ] Natural-language invocation is stated as a first-class capability
- [ ] `CHANGELOG.md` has a new `## Unreleased` section above 3.9.0 in this file's own style; no version bump anywhere
- [ ] Zero em dashes remain in `README.md`; replacements were chosen per sentence
- [ ] Curly quotes replaced except inside verbatim third-party quotations
- [ ] Decorative emoji removed from prose and the mermaid diagram; navigation-affordance emoji retained
- [ ] Every relative link in the README resolves
- [ ] No banned phrases, no hedging, no process or speed self-praise


## Done summary
Recomposed `README.md` onto the fn-151 narrative spine (problem line, scannable SlopCodeBench evidence, the six canonical outcome headings byte-identical to the spec, adoption and breadth evidence promoted from line 346 into the first quarter), made `plugins/flow-next/docs/platforms.md` the single canonical home for the harness-tiering sentence that the README prose and platforms table now restate verbatim, stripped inventory counts from front-door prose while correcting the reference tail to 21 agents, removed all 106 em dashes per sentence, and opened a `## Unreleased` section in `CHANGELOG.md` with no version bump.

Deviation to flag: the README lands at 495 lines, not the briefed ~360. Items 6 and 8 of the brief pin `## Quick start` (70 lines) and `## How the flow works` (126 lines) as unchanged, and those two blocks alone are 196 lines; retaining every other section plus the six new outcome blocks makes 360 unreachable without deleting content the brief says to keep. The demotions the brief does authorise are all done (badge row 8 to 5, tenet table behind a disclosure, the 25-row command inventory replaced by prose plus a link to `docs/skills.md`, which is a strict superset). `## Where to look` (33 lines, 24 rows) is the one remaining inventory block that could be demoted the same way if the conductor wants the number lower; it was left alone because the brief did not name it.
## Evidence
- Commits: 1ed72360e007adfda79d9c582b097b39e6a9c608
- Tests: python3 <relative-link checker> . README.md -> 34 relative links checked, all resolve (files + in-repo anchors), python3 <relative-link checker> . plugins/flow-next/docs/platforms.md -> 8 relative links checked, all resolve, grep -o '—' README.md | wc -l -> 0 (was 106 occurrences across 83 lines), grep -cP '[’‘“”]' README.md -> 1, the verbatim raydocs quote (author's own punctuation, required to stay), six canonical outcome headings diffed against .flow/specs/fn-151...md Architecture section -> all 6 byte-identical, canonical harness-tiering sentence occurrence count -> platforms.md 1 (canonical home), README.md 2 (tenet prose + platforms table lead), grep -riwf <private client-names list> README.md plugins/flow-next/docs/ -> clean (exit 1), grep -ri '<private-vocabulary terms>' README.md plugins/flow-next/docs/ -> clean (exit 1), banned-phrase + hedging greps over README.md, new CHANGELOG block, new platforms.md lines -> clean, agent count verified against ls plugins/flow-next/agents/*.md and codex/agents/*.toml -> 21 both; platforms.md corrected in 3 places, GATE_SKIPPED:unittest:docs-only - markdown-only change, no executable paths touched (per task brief: no test suite, no ruff, no version bump)
- PRs: