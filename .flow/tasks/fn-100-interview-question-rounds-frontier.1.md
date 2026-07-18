---
satisfies: [R1, R2, R3, R4, R8, R9]
---

## Description

Apply the fn-100 rounds protocol to the interview skill and regenerate the Codex mirror.

**Size:** M
**Files:** plugins/flow-next/skills/flow-next-interview/SKILL.md, plugins/flow-next/skills/flow-next-interview/references/doc-aware.md, plugins/flow-next/codex/ (regenerated)

The spec's "Exact SKILL.md edits" sections are the verbatim source of truth for Edit A (Interview Process bullet, SKILL.md ~line 266), Edit C (append one bullet to the Plain-language question contract list: questions citing a spec R-ID inline the criterion text in full at first mention, never a bare R-ID pointer - exact text in the spec's "Exact SKILL.md edit C" section) and Edit B (replace the whole "### Question Order: Walk the Decision Tree" section, ~lines 335-352 heading-through-example inclusive; the blank separator line before "### Investigate Codebase Before Asking" stays). Rules 1-5 + the example flow in Edit B are an eval-validated artifact: apply byte-for-byte, do not reword. Rule 6 is the additive interruption-recovery rule, also verbatim from the spec.

Then apply R8 in references/doc-aware.md: redefine the four genuine throttle/cadence sites (~lines 55, 76, 131, 171) as per-ROUND - one glossary question per round, glossary re-read note per round, one decision write per round, one strategy-conflict question per round, combined doc-aware budget stays "3 max" per round. The two behavior-(b) trigger sites (~63, 78) stay observation-based: sharpening body says `<count> replies`, skip heuristic becomes "<=6 user replies" (impl-review r1 correction - "<=6 rounds" would have made sharpening unreachable since a full rounds interview is 3-5 rounds). Keep each edit minimal (word-level substitution plus the smallest grammatical fixups); the budget never multiplies by calls within a round.

Finally regenerate the mirror: `./scripts/sync-codex.sh` (full regen, commit the resulting codex/ diff together with the canonical edits).

Token measurement (feeds task .2's ledger row): IMMEDIATELY before and after applying Edits A/B/C run `cat plugins/flow-next/skills/flow-next-interview/SKILL.md plugins/flow-next/skills/flow-next-interview/questions-shared.md plugins/flow-next/skills/flow-next-interview/questions-technical.md | wc -c` and record both byte counts (tok-equiv = bytes/4, the repo convention). Put both numbers in the task completion summary so task .2 can copy them into results.tsv.

## Approach

- Follow the exact-text blocks in `.flow/specs/fn-100-interview-question-rounds-frontier.md` section "Exact SKILL.md edits".
- Mirror audit lessons from `.flow/memory` (sync-codex R2-injection): after regen, grep the mirror for the injected plain-text-ask instruction and eyeball each site's surrounding lines - it must land at genuine ask sites only, never mid-sentence, never inside negation or example prose. No literal `AskUserQuestion` outside sanctioned transforms. Run sync-codex.sh a second time and confirm a byte-identical tree (idempotency).

## Investigation targets

**Required** (read before coding):
- `.flow/specs/fn-100-interview-question-rounds-frontier.md` - the verbatim edit blocks + edge cases
- `plugins/flow-next/skills/flow-next-interview/SKILL.md:259-267` - Edit A site
- `plugins/flow-next/skills/flow-next-interview/SKILL.md:335-352` - Edit B site
- `plugins/flow-next/skills/flow-next-interview/references/doc-aware.md:50-80,125-135,165-175` - the six throttle sites
- `scripts/sync-codex.sh:1-30` - regen contract (idempotent, full-tree)

**Optional:**
- `plugins/flow-next/codex/skills/flow-next-interview/SKILL.md` - current mirror shape for before/after comparison

## Acceptance

- [ ] R1: Edit A applied verbatim; rest of the CRITICAL block untouched
- [ ] R2: Edit B applied verbatim (rules 1-6 + example); heading now "Rounds over the Decision Tree"
- [ ] R9: Edit C bullet appended verbatim to the plain-language contract
- [ ] R3: `git diff` over SKILL.md shows ONLY the three edit blocks changed
- [ ] R8: four throttle/cadence doc-aware.md sites read per-round; two behavior-(b) trigger sites reply-based; budget still "3 max"
- [ ] R4: mirror regenerated; no stray `AskUserQuestion` literal; every injected ask-block at a genuine ask site (audited, not just grepped); second sync run byte-identical
- [ ] tokens_before/tokens_after byte counts measured (same command, before + after) and recorded in the completion summary
- [ ] Commit(s) include canonical + mirror together

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
