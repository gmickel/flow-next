# Scoped review execution provider integration

## Goal & Context

Hosts such as MergeFoundry can execute Flow-Next reviews through their registered provider accounts while Flow-Next retains workflow and receipt ownership. Ordinary standalone Flow-Next users keep their current execution behavior. Deliver the generic hook in an installable supported artifact and prove the normal host integration; broader MF provider testing remains separate.

## Architecture & Data Models

Port the reviewed development prototype onto current upstream, adapting to existing review dispatch machinery. Only inference crosses a scoped local HTTP boundary. Review reservations, prompts, verdict parsing and receipts stay in Flow-Next. Use the existing environment handoff and managed-required CLI flag rather than adding a new workflow engine or cloud API.

## API Contracts

Preserve the prototype version-1 request and response contract and FLOW_REVIEW_EXECUTION_URL/TOKEN handoff. An unset execution URL uses normal CLI execution. A configured malformed/unavailable provider fails closed. --require-managed-execution requires valid scoped configuration before a reservation or execution begins. Installed help must advertise the supported flag so a host can check compatibility without inference.

## Edge Cases & Constraints

No configured provider; malformed/empty endpoint or token; non-loopback URL; proxy/redirect leakage; malformed/oversized response; timeout; resume ownership; retries/fanout identity; backend CLI preflight that should not run for hosted execution; installed named-file layout; direct standalone reviews. Keep credential data out of diagnostics. No profile paths or MF account-specific configuration become mandatory upstream fields.

## Acceptance Criteria

- **R1:** When the provider environment is absent, existing review backends retain their ordinary CLI behavior and receipts, covered by regressions. No MF installation or config is needed.
- **R2:** A configured local scoped execution provider runs inference for review paths while Flow-Next writes its ordinary receipts. Invalid configuration, response or execution fails closed without CLI fallback or secret disclosure.
- **R3:** Managed-required mode refuses missing configuration before reserving/launching work and its presence is discoverable from installed CLI help. Pre-hook installations remain distinguishable without invoking inference.
- **R4:** Real installer output includes the hook and runs it through the installed launcher. Test successful/negative receipt behavior and standalone behavior from a disposable install; retain exact installation provenance.
- **R5:** Focused and full Python tests, Ruff, generated manifest and deterministic Codex sync pass; affected upstream docs and docs-site references agree. Release and CI status remain explicit, with no public availability claim before publication.

## Boundaries

No MF-specific workflow rules, cloud agent framework, new review backend, broad skill changes, global plugin reinstall, or modification of Gordon's active Flow-Next checkout. Do not start the held MF provider matrix or two-Cursor setup. Versioning/publication follows separately gated release policy; stage implementation notes under Unreleased until then.

## Decision Context

Reuse development commits b9313d5a and 4348268f after inspecting their diff. The generic provider boundary lets a host broker remote execution later without uploading local credentials or adding cloud-specific requirements now. Apply standing G1/G2 criteria.
