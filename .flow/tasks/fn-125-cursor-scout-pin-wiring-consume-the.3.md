---
satisfies: [R3]
---
# fn-125-cursor-scout-pin-wiring-consume-the.3 Harden fallback semantics + document runtime contract

## Description
Harden fallback semantics + document the runtime contract. Finalize fallback in references/read-only-scout-routing.md + flow-next-plan/steps.md + flow-next-prime/workflow.md. Update templates/usage.md (+ byte-identical .flow/usage.md), docs/orchestration.md, docs/platforms.md, test_cursor_scout_routing.py, test_cursor_host_docs.py. Cases: absent routing block / duplicate-or-damaged markers / missing row / empty pin / placeholder pin -> normal unpinned dispatch; explicit unavailable-or-not-eligible model rejection -> retry ONLY the affected scout once, unpinned; non-model scout failures keep existing behavior (Plan surfaces; Prime retry-then-NOT-ASSESSED). Fallback never mutates AGENTS.md / setup state / persisted config. One concise fallback notice (requested pin + inherited behavior; never claims the actual model). Docs distinguish fail-OPEN scout routing from fail-CLOSED cross-family host review.

## Acceptance
- All degrade cases (absent/duplicate/missing-row/empty/placeholder) fall back to unpinned dispatch; rejected pin retries the one scout once, unpinned.
- Non-model failures unchanged; fallback never mutates AGENTS.md/setup/config.
- Docs draw the fail-open-scout vs fail-closed-host-review distinction.
- templates/usage.md and .flow/usage.md byte-identical.
- test_cursor_scout_routing / test_cursor_host_docs / test_setup_cursor_host green.


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
