---
satisfies: [R7, R8]
---

## Description
Add the single lean **BRB-borrow reference** (the QA discipline) and wire the **prepare phase** (target URL, test accounts, session hygiene, device matrix). Borrow discipline only — never the driver prose.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-qa/references/qa-discipline.md` (new), `plugins/flow-next/skills/flow-next-qa/workflow.md` (prepare phase)

## Approach
- **The five-thing lean borrow (R8)** into one reference, credited Apache-2.0:
  1. P0/P1/P2 taxonomy + tie-break ("P0 if a user could lose data or land non-recoverable").
  2. Evidence rules (console verbatim / screenshot-at-failure / full URL / server row).
  3. Five session-hygiene rules + persona suffixing (`qa-…+runMMDD-N@…`).
  4. Write-path-first / one-tab-per-shard caution (a paragraph, NOT the coordinator machinery).
  5. YES/NO verdict + paste-ready handoff.
- **Prepare phase (R7):** resolve target URL/app, test accounts, session hygiene (clear localStorage/sessionStorage + cookies for fresh-user scenarios), device matrix (one desktop + one mobile viewport — v1 viewport-emulation only per the spec decision). **Ask the user (AskUserQuestion) when accounts/URL are undocumented.**
- **Do NOT copy BRB's browser-playbook prose** — it names cursor-ide-browser / browser-use, which fn-51 does not lead with. Point QA at fn-51's `references/agent-browser.md`, `auth.md`, `session-management.md` for the actual driving.
- Hold the ≤500-line cap; this is the bulk of the borrowed material, kept to one thin reference.
- **Merge-safety:** edit ONLY the *prepare*-phase section anchor 53.1 laid in `workflow.md` — `references/autonomy.md` and the *execute/autonomy* section belong to 53.4 (serial, disjoint).

## Investigation targets
**Required:**
- `~/repos/rayfernando-skills/.../references/session-hygiene.md` — the highest-dividend borrow (compress, don't port)
- `~/repos/rayfernando-skills/.../references/bug-filing.md` + `SKILL.md` — taxonomy + evidence + verdict-table wording
- `plugins/flow-next/skills/flow-next-drive/references/` — `agent-browser.md`, `auth.md`, `session-management.md` (point QA here, don't duplicate)

**Optional:**
- `plugins/flow-next/skills/flow-next-drive/SKILL.md:46-78` — the ladder QA inherits

## Key context
- BRB is ~2,500 lines / 18 refs; the spec forbids porting the full surface. Drop discovering-the-app, HTML dashboard, iOS-sim, Clerk/Auth0 playbooks, triage-heuristics catalog, tracker adapters — flow-next already has the spec, bug memory, receipts, make-pr table, fn-52.
- Attribution precedent: `flow-next-drive/SKILL.md` already credits BRB Apache-2.0 — mirror that exact phrasing.

## Acceptance
- [ ] `references/qa-discipline.md` covers the five lean borrows (taxonomy+tie-break, evidence rules, 5 hygiene rules + persona suffixing, shard caution, verdict+handoff); credits rayfernando-skills Apache-2.0
- [ ] Prepare phase resolves URL / accounts / session hygiene / device matrix (1 desktop + 1 mobile viewport); asks the user when undocumented
- [ ] No BRB browser-playbook prose copied; driving specifics defer to fn-51's references
- [ ] Reference + skill stay within the ≤500-line discipline

## Done summary
Added references/qa-discipline.md (the lean BRB borrow: 5 session-hygiene rules + persona suffixing, write-path-first / one-tab-per-shard caution, YES/NO verdict + paste-ready handoff discipline — cross-linking bug-filing.md for the P0/P1/P2 taxonomy + evidence rules rather than duplicating them, credited rayfernando-skills Apache-2.0). Wired the Phase 3 (prepare) section of workflow.md to resolve target URL / test accounts / session hygiene / device matrix (1 desktop + 1 mobile viewport, emulation-only), asking the user when undocumented and deferring all driving specifics to fn-51's references.
## Evidence
- Commits: f35081ee5ea0e1f4ed4f55691df1864d76df0d38
- Tests: wc -l (≤500-line skill cap: workflow.md 418, qa-discipline.md 186), cross-link resolution check (bug-filing.md + fn-51 commands/agent-browser/auth/session-management all resolve), scoped-diff confined to Phase 3 section (no sibling-phase collision), impl-review (rp backend): triage-skip docs-only fast-path → SHIP
- PRs: