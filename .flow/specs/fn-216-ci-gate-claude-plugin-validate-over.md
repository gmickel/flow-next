# CI gate: claude plugin validate over plugins/flow-next

## Conversation Evidence

> user (turn 1): "a new issue and PR just appeared on github, check it if it's valid, no action, review only for now"
> user (turn 2): "go ahead"
> user (turn 3): "yea queue it as a spec"
> [external — PR #390 body, @acebytes]: "Same class as #235 and #332, so it may be worth a CI step running `claude plugin validate` over `plugins/flow-next` to catch the next one."
> [external — issue #389, @acebytes]: "Because the failure is silent at runtime — only `claude plugin validate` surfaces it — the skill appears installed but never activates."

## Goal & Context

<!-- Source-tag breakdown: 20% [user], 50% [paraphrase], 30% [inferred] -->

Issue #389 shipped in every release from 4.9.1 to 4.11.0: one unquoted YAML frontmatter `description` containing a colon-space made `flow-next-features` load with empty metadata on hosts with strict frontmatter parsing — silently, because only `claude plugin validate` surfaces the failure and nothing in CI runs it. This is the third instance of the class (#235, #332, #389): a plugin-file defect invisible to the unit suite, caught only by an external reporter after release. The fix is the reporter's own suggestion, accepted at merge: run the official validator in CI so the next one fails the build instead of shipping.

## Architecture & Data Models

<!-- Source-tag breakdown: 100% [inferred] -->

A CI job in the existing test workflow (or a sibling workflow) that installs the Claude Code CLI on the runner and runs the official validator against the plugin root, failing the build on any validation error. No custom YAML linting — the validator is the single source of truth for what the host loader accepts, so the gate can never drift from the real contract.

## Edge Cases & Constraints

- **Validator unavailability fails loud, never open:** a runner where the CLI cannot be installed or the validate verb errors for environmental reasons must fail the job with a distinguishable message — a silent skip recreates the exact gap this closes. [inferred]
- **Validator version drift:** the CLI's validation strictness varies by version (2.1.251 validated only the manifest; the reporter's version validated skill frontmatter). The job should install a current CLI, not pin an old one — the point is matching what real hosts enforce. [paraphrase]
- **No auth dependency:** the gate must run on fork PRs, so it cannot require an authenticated Claude session; verify `claude plugin validate` runs unauthenticated on a bare runner. [inferred]
- **Path filter:** the job needs to trigger on changes under `plugins/flow-next/**` including skills, agents, commands, and manifests — and the repo's `test_ci_trigger_coverage` pins workflow path filters, so extend them consistently. [inferred]

## Acceptance Criteria

- **R1:** CI runs `claude plugin validate plugins/flow-next` on pushes and PRs that touch plugin files, and a validation error fails the build. Errors: CLI install failure or validator crash → job fails with a message distinguishing environment failure from validation failure; no silent-skip path. [paraphrase]
- **R2:** The gate catches the #389 class: a skill frontmatter that a spec-compliant YAML parser rejects (e.g. an unquoted `description` containing `: `) turns the job red. Errors: no error surface beyond R1 — the demonstration is a test or a documented one-off verification, not a permanently broken fixture. [paraphrase]
- **R3:** Repo docs note the gate where contributors will find it (the CI section of the contributor-facing docs), and `test_ci_trigger_coverage` stays green with the new/extended path filters. Errors: no error surface beyond the existing CI pins. [inferred]

## Boundaries

- No custom YAML linter or hand-rolled frontmatter checks — the official validator only. [paraphrase]
- No version bump — CI and docs changes only. [inferred]
- No validation of consumer installs (`$CODEX_HOME`, Cursor snapshots) — this gate covers the canonical plugin tree; the sync-codex guards keep owning the mirror. [inferred]

## Decision Context

Accepted from the contributor's suggestion on PR #390 at merge time (thanks @acebytes) — third instance of the silent-plugin-breakage class (#235, #332, #389), each found post-release by an external reporter. The validator-in-CI shape was chosen over a custom lint because the validator is the loader's own contract; a re-implementation would drift. [paraphrase]

## Parked unknowns

- Whether `claude plugin validate` runs cleanly on a bare CI runner (unauthenticated, headless) and how the CLI is best installed there — resolved by trying it in the implementation branch's CI run. [inferred]

## Requirement coverage

| R-ID | Task |
|---|---|
| R1 | fn-N.M (TBD — populate via /flow-next:plan) |
| R2 | fn-N.M (TBD — populate via /flow-next:plan) |
| R3 | fn-N.M (TBD — populate via /flow-next:plan) |
