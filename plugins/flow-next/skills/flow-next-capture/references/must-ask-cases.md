# capture — must-ask cases (R9), with examples (loaded on demand)

> Loaded ONLY when at least one of the three Phase-3 must-ask conditions actually fires. A capture
> with an unambiguous title, testable criteria, and no scope conflict never reads this file.
> Interactive asks (one question per turn); autofix exits 2 with which case fired.

## Interactive question shape (3.1)

Use `AskUserQuestion` with the lead-with-recommendation pattern:

- **header**: short tag (`Title?`, `Criterion R3`, `Boundary?`)
- **body**: `<Context — what's ambiguous and why>. Recommended: <X> — <one-sentence rationale>. Confidence: [<tier>].`
- **options**: frozen neutral labels (no recommendation markers on the options themselves)

Confidence tier rules (the full table is in phases.md §Confidence tiers):

- `[high]` — agent has strong codebase signal or convention match
- `[judgment-call]` — slight lean but reasonable people disagree
- `[your-call]` — agent has no signal; user's domain knowledge / priority decides

The third tier matters: it prevents the "always recommend" failure mode that trains users to defer.

## One question per turn (3.3)

Even when multiple must-ask cases fire, ask **one at a time**. Subsequent questions adapt based on prior answers. Multi-question violates the `AskUserQuestion` contract and overwhelms users (practice-scout F4.3).

## Case (a) — Ambiguous title

**Trigger:** Phase 1.3 candidate title is `[inferred]` AND the conversation supports multiple plausible titles, none load-bearing.

**Why hard-error:** an ambiguous title leads to bad spec ids, bad branch names, bad git history. The cost of asking is one question; the cost of guessing wrong is renaming the spec later.

**Examples:**

- Conversation: "let me think about this rate limiting problem... maybe we need throttling... or queue depth... or per-tenant quotas". Candidate titles: `Rate limiting`, `Request throttling`, `Per-tenant quotas`. None of those is load-bearing in the conversation. → must-ask.
- Conversation: "the OAuth callback is broken when X happens". Candidate title: `Fix OAuth callback X bug`. Specific. → no must-ask.

**Interactive question shape:**

- header: `Title?`
- body: `Conversation supports multiple titles. Recommended: <X> — <one-sentence rationale>. Confidence: [<tier>]. (Other plausible: <Y>, <Z>.)`
- options: `<X>`, `<Y>`, `<Z>`, `custom`

**Autofix:** exit 2 with: `Must-ask (a): spec title genuinely ambiguous from conversation. Candidates: <X>, <Y>, <Z>. Re-run interactively to choose.`

## Case (b) — Untestable acceptance

**Trigger:** Phase 2.4 flagged ≥1 acceptance criterion that fails the testability check. A criterion is testable if a reviewer can point at code / behavior / config and say "satisfied" or "not satisfied" with two engineers agreeing.

**Why hard-error:** untestable acceptance criteria turn into "done when the user feels good", which never closes. Capture's purpose is producing a usable spec; vague acceptance defeats that.

**Examples:**

- Untestable: `- **R3:** Make it fast.` (fast how?)
- Untestable: `- **R4:** Improve UX.` (improve how — measured how?)
- Testable: `- **R3:** Median p95 latency under 200ms for the OAuth callback path.`
- Testable: `- **R4:** Form errors render inline within 100ms of input blur.`

**Interactive question shape (per-criterion):**

- header: `Criterion R<n>`
- body: `"<criterion>" can't be made testable as written. Recommended: <reword candidate> — <rationale>. Confidence: [<tier>]. (Or drop / clarify in your own words.)`
- options: `<reword candidate>`, `drop`, `clarify`

If user picks `clarify`, follow-up question accepts free text → re-run testability check on the new wording.

**Autofix:** exit 2 with: `Must-ask (b): <N> criteria failed testability check: <list>. Re-run interactively to reword or drop.`

## Case (c) — Scope-conflict with existing spec

**Trigger:** Phase 0.5 went `supersede` or `proceed-anyway` (user accepted a duplicate-ish spec), AND the new spec's drafted scope (Phase 2) still substantively overlaps the existing spec's scope on a load-bearing axis (same module + same problem domain, even if framed differently).

**Why hard-error:** if the new spec is "in addition to" the old one, the boundaries between them must be explicit. Otherwise the next time someone runs `/flow-next:plan`, both specs fight over the same tasks.

**Examples:**

- Old spec: `OAuth callback rate limiter` (in progress, 2 tasks done). New conversation: "we need rate limiting on the API". User picks `proceed-anyway`. New scope drafted as "all API endpoints" — explicit superset of old. → must-ask: how do the two specs carve up the rate-limit space?
- Old spec: `OAuth callback rate limiter`. New conversation: "we need rate limiting on the GraphQL endpoint". New scope: GraphQL only. → no must-ask. Boundaries are clear.

**Interactive question shape:**

- header: `Boundary?`
- body: `Old spec <id> "<title>" overlaps new spec on <axis>. Recommended: <X> (carve out <bound>) — <rationale>. Confidence: [<tier>].`
- options: `carve-by-module`, `carve-by-feature`, `mark-old-as-subsumed`, `keep-overlap-and-let-plan-resolve`

**Autofix:** exit 2 with: `Must-ask (c): scope conflict with existing spec <id>. Re-run interactively to disambiguate.`
