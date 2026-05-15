---
satisfies: [R4, R5]
---

## Description

Split the existing technical-heavy `questions.md` into scope-specific banks. Create `questions-business.md` covering nine business-context dimensions. Rename `questions.md` to `questions-technical.md`. Hoist Pre-Question Taxonomy + Interview Guidelines to `questions-shared.md` referenced by both banks. SKILL.md updates references.

**Size:** M
**Files:**
- `plugins/flow-next/skills/flow-next-interview/questions-business.md` (NEW)
- `plugins/flow-next/skills/flow-next-interview/questions-technical.md` (renamed from `questions.md`)
- `plugins/flow-next/skills/flow-next-interview/questions-shared.md` (NEW; hoisted shared blocks)
- `plugins/flow-next/skills/flow-next-interview/SKILL.md` (update file references)

## Approach

Business question bank covers nine topic-prompt buckets in the SAME structural format as `questions-technical.md` — H2 heading per bucket, 4-5 short bullet-point topic prompts per bucket, NO decoration. Dynamism lives in SKILL.md (Pre-Question Taxonomy, Lead-with-Recommendation, Walk-the-Decision-Tree, Interview Guidelines), NOT in the bank itself — same architecture as the technical bank.

The nine buckets (header text only; bucket bodies are short bullet topic prompts the implementer writes following the tech-bank pattern):
- Problem framing / why-now
- Target user / persona
- Success metrics / definition of done
- MVP scope / what's NOT in this pass
- Business constraints (regulatory / deadlines / budget)
- What NOT to build (explicit non-goals)
- Prioritization rationale
- Business risks
- UX expectations / tone

**Do NOT annotate buckets with routing destinations.** Routing rules live in capture skill workflow.md (per R24); the question bank stays a pure topic-prompt scaffold. The biz bank must be structurally indistinguishable from `questions-technical.md` aside from bucket names and topics — same heading levels, same bullet density, same prose tone.

Pre-Question Taxonomy block from `questions.md:5-27` (3-axis classifier) hoists to `questions-shared.md`. Same for Interview Guidelines at `questions.md:101-108`. Both banks reference shared.

Renamed `questions-technical.md` keeps existing technical buckets unchanged.

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-interview/questions.md` (full file, 108 lines) — current bank layout
- fn-44 spec Architecture: question banks subsection

**Optional:**
- Volere requirements template + BABOK biz-vs-tech classification for biz bucket vocabulary

## Acceptance

- [ ] `questions-business.md` created with the 9 dimensions; question buckets use `## H2` headings matching tech bank style
- [ ] Biz bank is structurally indistinguishable from `questions-technical.md` (same heading levels, same 4-5-bullet density per bucket, same prose tone) — NO routing-destination annotations on buckets (routing rules live in capture workflow.md per R24)
- [ ] `questions.md` renamed to `questions-technical.md`; content unchanged
- [ ] `questions-shared.md` created with Pre-Question Taxonomy + Interview Guidelines; both banks reference it
- [ ] `SKILL.md` references the correct bank by scope
- [ ] No questions in the biz bank ask about technical details (avoid scope leak)

## Done summary
Split the technical-heavy `questions.md` into scope-specific banks: new `questions-business.md` with 9 biz buckets (problem framing, target user, success metrics, MVP scope, business constraints, what-NOT-to-build, prioritization, business risks, UX expectations), renamed legacy `questions.md` → `questions-technical.md`, and hoisted shared Pre-Question Taxonomy + Interview Guidelines into `questions-shared.md` referenced by both banks. SKILL.md updated; codex mirror regenerated; first-pass SHIP from codex:gpt-5.5:high.
## Evidence
- Commits: d9c691cc54dc4b4a7e6e0d7a8669c488ac01045f
- Tests: python3 -m unittest discover -s plugins/flow-next/tests -p 'test_*.py' (463 passed), bash scripts/sync-codex.sh (all R-guards pass), flowctl scope bank business|technical|both → resolves to existing files, codex impl-review SHIP verdict (gpt-5.5:high, 1 pass)
- PRs: