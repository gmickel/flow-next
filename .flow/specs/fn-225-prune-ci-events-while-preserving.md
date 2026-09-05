# Prune CI events while preserving platform and release evidence

## Goal & Context
Reduce redundant CI work without losing relevant platform acceptance or allowing untested releases. Implement the authorized CI audit recommendations.

## Architecture & Data Models
Existing change classification chooses matrices for PR and main push ranges. Keep conservative fallbacks. A stable aggregate gate represents required jobs.

## API Contracts
GitHub events and job outputs remain the interface; release requires successful CI for its exact revision.

## Edge Cases & Constraints
Missing history, new branches, failed diffs and empty ranges fail conservatively into full checks. Scheduled compatibility runs remain extensive.

## Acceptance Criteria
- **R1:** Cancel superseded PR runs and bound jobs with timeouts; main and releases are not interrupted by PR cancellation. No additional error surface beyond GitHub concurrency.
- **R2:** Classify main push before-to-after range and PR range, preserving docs prompt-pin and parity units; unknown ranges run full gates.
- **R3:** Scope Windows stub to relevant launcher/installer/runtime paths and run weekly backstop. Retain meaningful Windows unit and installer/config PR coverage; diagnose and fix Windows encoding failures if still present.
- **R4:** Tag publication requires exact revision successful CI evidence; absent, failed or diagnostic-only evidence blocks publication. Provide stable aggregate required check that cannot succeed after mandatory failure.
- **R5:** Focused regression checks and repository full test/lint gates pass; no removal of meaningful coverage to achieve green.

## Boundaries
No release tags or actual publication. No broad product behavior changes or public messaging update. Root conductor owns live rulesets.

## Decision Context
Extend existing pruning rather than relocating useful Windows coverage. Applicable G1/G2 standing criteria govern shape.
