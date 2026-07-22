---
satisfies: [R4]
---
# fn-126-grok-build-host-fidelity-positive.3 Validate Grok command discovery after fn-124

## Description
Validate Grok command discovery AFTER fn-124 is incorporated. Do NOT change command shims/manifests/Cursor installers/fn-124-owned tests here (no double-fix). Once fn-124's flattened commands/*.md surface is in the branch: in a real Grok session, inventory slash-menu discovery and directly invoke `/flow-next:setup` + one more representative command; record the fn-124 commit + live result in the spec. If under-listing REMAINS, record that it is not fully explained by the shim root and open/link a SEPARATE follow-up - do not grow fn-126 into a second shim fix.

## Acceptance
- fn-124 incorporation proven before the live smoke; flattened-shim regression tests pass.
- Live evidence distinguishes menu VISIBILITY from successful TYPED invocation.
- Spec records one conclusion: fixed-by-fn-124 OR residual Grok-specific gap with a linked follow-up.
- No duplicate command-shim implementation lands in fn-126.
- NEEDS-HUMAN: slash-menu inventory + typed execution in real Grok Build.


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
