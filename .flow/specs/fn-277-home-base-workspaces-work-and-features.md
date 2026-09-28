# Home-base workspaces: work and features status read the sibling repos that hold the code

## Conversation Evidence

- Issue #494 (reporter CWayman): "one planning repo per domain holds `.flow/` ... and the product code lives in sibling clones next to it". Work's spec base, `gate classify`, the feature-map update step and `features status` all read only the repo that holds `.flow/`, so a sibling code change can pass as "TIER_B, docs-only". [user]
- The issue proposes a `workspace.siblings` config key read by the four consumers. [user]
- Maintainer: "if valid, best, agentic fix for both". [user]

## Goal & Context

A home-base workspace keeps `.flow/` in a planning repo and the product code in sibling git clones. Four places assume the change lives in the `.flow/` repo: work's persisted spec base, the Phase 4 `gate classify` call, the feature-map update step's diff, and `features status`'s surface-commit count. In a home base each sees the wrong diff, and the gate case is dangerous: a real code change can run lint-only gates. [paraphrase]

The fix follows "Agent first": the agent running work knows which repos it changes, so it records their bases and classifies each of them. `gate classify` already runs in any git repo, including one without `.flow/`. The only code change is a `--repo` input on `features status`, whose callers are agents that can read the project's instructions. [inferred]

## Architecture & Data Models

- **Work, branch setup.** When the spec changes code in git repos beside the `.flow/` repo (the project instructions or the spec name them), work records each repo's merge-base with its base branch next to `.flow/tmp/spec_base`, one `<repo path> <sha>` line per repo in `.flow/tmp/spec_base_repos`. A repo first touched later gets its line before its first edit. No sibling repos means no file, and behaviour is unchanged. [inferred]
- **Work, Phase 4.** `gate classify` runs in the `.flow/` repo as today and again inside each recorded repo against that repo's base. Docs-only tier-B applies only when every repo classifies tier-B. A nonzero result in any repo, including a missing path, a non-repo or an unresolvable base, runs the full gates in that repo. The auditor dispatch names each recorded repo and its base. [inferred]
- **Feature-map update step.** "The spec's diff" is the union of the `.flow/` repo's diff and each recorded repo's diff. [paraphrase]
- **`features status --repo <path>`** (repeatable, relative to the `.flow/` repo root). For each proven feature, it adds each listed repo's surface commits since the proof date to the `.flow/` repo's count. Each listed repo is measured from its own default-branch cascade, because the proof commit belongs to the `.flow/` repo. [paraphrase]
- **Callers.** Maintain's provenance step, flow's no-argument due check, prime's feature-map line and setup's recommendation pass `--repo` for each sibling code repo the project instructions name. [inferred]

## API Contracts

`flowctl features status [--repo <path>]... [--json]`

- Without `--repo`, the output is byte-identical to today's. [paraphrase]
- With `--repo`, each proven feature row's `commits_since` is the sum across repos, and the row gains `commits_since_by_repo`: `{".": <n>, "<path>": <n>, ...}`. The top-level output gains `repos: ["<path>", ...]`. [paraphrase]

## Edge Cases & Constraints

- A `--repo` path that does not resolve to a git work tree, or whose default-branch cascade resolves nothing, exits nonzero naming the path. A wrong path never silently reads as zero commits. [inferred]
- A repo listed twice is counted once. [inferred]
- `--repo` never changes the `.flow/` repo's own count or how it measures from the proof commit. [inferred]

## Acceptance Criteria

- **R1:** Work's branch-setup instructions tell the agent to record each sibling code repo's base in `.flow/tmp/spec_base_repos` (one `<path> <sha>` line). Phase 4 runs `gate classify` in each recorded repo and allows docs-only tier-B only when every repo is tier-B, with any nonzero result meaning full gates for that repo. Errors: no sibling repos means no file and today's behaviour. [paraphrase]
- **R2:** The feature-map update step defines the spec's diff as the union of the `.flow/` repo's diff and every recorded repo's diff (no error surface beyond R1). [paraphrase]
- **R3:** `features status --repo <path>` adds that repo's surface commits since each feature's proof date to the feature's count, reports per-repo counts in `commits_since_by_repo`, and lists the repos in `repos`. Commits before the proof date do not count. Errors: a path that is not a git work tree, or has no resolvable default branch, exits nonzero naming it. [paraphrase]
- **R4:** Without `--repo`, `features status --json` output is unchanged. [paraphrase]
- **R5:** Maintain, flow's no-argument check, prime and setup tell the agent to pass `--repo` for the sibling code repos the project instructions name. The flowctl reference and the features docs describe the flag. [inferred]
- **R6:** A test proves `gate classify` inside a sibling repo that has no `.flow/` reports FULL for a code change. The features-status suite covers sibling commits after and before the proof date, a bad path, and unchanged output without `--repo`. [paraphrase]

## Boundaries

- No config key and no persisted list of siblings; the agent reads the project instructions. [paraphrase]
- `gate classify` gains no multi-repo flag; the agent runs it per repo. [inferred]
- Maintain's entry gate stays single-repo, as the issue asks. [user]

## Decision Context

The issue's `workspace.siblings` key would give four consumers one list. Three of those consumers are skill prose that an agent executes, and the agent already knows which repos it changed. The fourth, `features status`, is a reporting helper whose callers are agents too. A per-call `--repo` input keeps the fact where the agent reads it (the project instructions) and adds no schema or validation to maintain, which matches the "Agent first" track. `gate classify` already works in a repo without `.flow/`, so it needs no change. [inferred]

## Strategy Alignment

Serves "Agent first": the agent records which repos it changed instead of filling a config schema. [strategy:agent-first]

## Strategy Conflicts

None found.
