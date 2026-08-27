---
satisfies: [R1, R3]
---
# fn-207-prose-contract-for-agent-emitted.1 Author docs/prose.md + index rows + releasing.md cite

## Description
Author the prose-contract reference doc and register it, then collapse releasing.md's generic prose-craft restatements into a cite (R1, R3). Split this way because the doc must exist (and its final path/shape be settled) before pointer links land in .2.

**Size:** M
**Files:** `plugins/flow-next/docs/prose.md` (new), `plugins/flow-next/docs/README.md`, `CLAUDE.md`, `agent_docs/releasing.md`
**Touches:** [plugins/flow-next/docs/prose.md, plugins/flow-next/docs/README.md, CLAUDE.md, agent_docs/releasing.md]

### Approach
- Shape: compact reference like `plugins/flow-next/docs/glossary.md` (intro, rules, scope boundary, `## See also`). Relative links only; register a row in the README "Subsystem references" table (row format matches the `review-findings.md` / `pr-cognitive-aid.md` rows) and a row in root CLAUDE.md "Where to look".
- Rule set (~10 rules, spec §Architecture): portability test; mechanism-or-number not feeling; negative-parallelism ban; no inline-header restating (with the legitimate bold-lead-in carve-out); active voice with named actor; adverb → measured delta; plain word; user-outcome-first ordering, machinery last; no em dashes / colon-as-connector in artifact prose; honesty (never soften a failure). Each rule one short paragraph max; evasion-blocking clause where the obvious workaround exists.
- Precedence rule (spec §Architecture, review-hardened): the doc states explicitly that the emitting surface's structural contracts supersede prose-shape rules — dedup markers first-line and unchanged, envelopes/projection-only source-truth never overridden, outcome-first only when a sourced outcome exists (never invent outcome prose).
- Scope-boundary paragraph: artifact prose only, no code-quality claim (cite SlopCodeBench, arXiv 2603.24755, as the reason the claim stays narrow).
- Cross-link (never re-derive) make-pr's hallucination guardrails (workflow.md §2.5) as the fabrication-side contract.
- releasing.md ownership-by-layer (R3, review-hardened — NOT byte-intact): prose.md owns generic principles; releasing.md keeps its changelog-specific machinery — the ordering algorithm, the hard rejection test with its worked examples (`agent_docs/releasing.md:65-124`), and the docs-site register (`:154-214`) — explicitly labeled as a changelog specialization of the generic rules, plus a one-line cite of prose.md. Generic restatements (e.g. the standalone "user-outcome-first" phrasing at `:72-82`, `:176-189`) are replaced by the cite; the specialization text that operationalizes them for changelogs stays. Cite direction check: prose.md must NOT link agent_docs/* (dangles on installs).

### Investigation targets
**Required** (read before writing):
- `plugins/flow-next/docs/README.md:21-58` — index tables + row format; `:131-135` conventions (R17 cross-link discipline)
- `plugins/flow-next/docs/glossary.md` — reference-shape pattern anchor
- `agent_docs/releasing.md:65-124` — changelog writing gate (specialization that stays); `:154-214` — docs-site register (specialization that stays); `:72-82`, `:176-189` — generic restatements to replace with the cite
- `plugins/flow-next/skills/flow-next-make-pr/workflow.md:685-732` — hallucination guardrails to cross-link

**Optional:**
- `GLOSSARY.md:196-198` — "Emission point" term (pointer discipline this doc anchors)
- `plugins/flow-next/skills/flow-next-tracker-sync/references/comments-sync.md:75-80,206-210,234-238` — the structural contracts the precedence rule protects

### Key context
- The doc's own prose must pass its own rules (R1) — dogfood read before handoff.
- Pure docs change: no version bump; CHANGELOG entry is .2's job (single `## Unreleased` entry for the whole spec).

### Acceptance
- [ ] `plugins/flow-next/docs/prose.md` exists: ~10 rules + precedence rule + scope-boundary paragraph + `## See also`; passes its own rules on a read-through
- [ ] README index row + CLAUDE.md "Where to look" row added
- [ ] releasing.md cites prose.md; changelog-specific machinery (ordering, rejection test + worked examples, docs-site register) stays and is labeled as a changelog specialization; generic restatements replaced by the cite; no generic rule spelled out in both files
- [ ] prose.md contains no links to `agent_docs/*`
- [ ] Focused suites green: `cd plugins/flow-next/tests && python3 -m unittest test_prompt_text_pinned -q`
## Acceptance
- [ ] `plugins/flow-next/docs/prose.md` exists: ~10 rules + precedence rule + scope-boundary paragraph + `## See also`; passes its own rules on a read-through
- [ ] README index row + CLAUDE.md "Where to look" row added
- [ ] releasing.md cites prose.md; changelog-specific machinery (ordering, rejection test + worked examples, docs-site register) stays and is labeled as a changelog specialization; generic restatements replaced by the cite; no generic rule spelled out in both files
- [ ] prose.md contains no links to `agent_docs/*`
- [ ] Focused suites green: `cd plugins/flow-next/tests && python3 -m unittest test_prompt_text_pinned -q`
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
