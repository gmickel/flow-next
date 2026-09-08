# Python simplification and regression fixes

## Goal & Context

Remove unnecessary Python machinery and fix defects exposed by a broad first-principles review of Flow-Next. Gordon requested GPT-6 Astra subagents, the deletion-first review rubric, regression evidence, and delivery through make-pr.

## Architecture & Data Models

Keep the stdlib CLI, provider package, and existing installer tooling. Delete demonstrably unused paths and consolidate repeated logic within existing boundaries. Preserve the review journal, provider adapters, filesystem guards, and historical evaluation evidence.

## API Contracts

Public CLI commands and output schemas remain compatible. Forced task takeover transfers ownership even with a custom note. Anonymous tracker HTTP requests do not resolve provider credentials. Encoded Basic credentials receive the same redaction protection as raw secrets. TOML normalization preserves unrelated tables. Tracker locks reject symlinked lock directories. Installer verification compares complete copied payloads. Evaluation read coverage derives from measured files.

## Edge Cases & Constraints

Python 3.11+, pure stdlib runtime. Preserve emitted review prompts byte for byte. Test malformed or missing config, takeover ownership transitions, anonymous versus authenticated requests, credential echoes, and commented TOML table boundaries. All tracker tests use fakes; no live tracker writes.

## Acceptance Criteria

- **R1:** Review the core CLI, review machinery, tracker integration, supporting Python tools, and test/evaluation infrastructure with GPT-6 Astra; record accepted and rejected candidates. No error surface beyond read-only inspection and local checks.
- **R2:** Remove confirmed dead paths and simplify duplicate Python logic while preserving supported command and review contracts. Errors: existing invalid-input, storage, backend failure, and no-embed behavior remains covered by focused suites.
- **R3:** Fix reproduced ownership, credential-policy/redaction, lock containment, TOML-preservation, and verification defects with meaningful regressions. Errors: unavailable credentials cannot block anonymous requests; unowned TOML data survives; custom notes preserve ownership transfer; symlinked lock parents cause no external writes; missing or extra installed payloads and missing required evaluation files cannot pass verification.
- **R4:** Run affected regression suites, regenerate required artifacts idempotently, and pass the repository full suite and pinned Ruff check before opening the PR. Failed checks must be repaired or reported without claiming a green result.

Standing criteria: G1 and G2.

## Boundaries

- Skill prose and prompt optimization.
- New CLI commands, dependencies, configuration flags, or architectural extraction.
- Rewriting historical evaluation results or implementing unrelated backlog specs.
- Releases, merges, and live tracker mutations.

## Decision Context

Prefer deletion over simplification, simplification over optimization, and optimization over automation. Each edit needs caller evidence or a reproduced defect. Working journal and provider-specific behavior stays because its contracts justify the machinery. Review findings and regression evidence will be recorded in task summaries; this review does not claim exhaustive proof of all possible regressions.
