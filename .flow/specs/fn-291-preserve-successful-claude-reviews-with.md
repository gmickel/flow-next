# Preserve successful Claude reviews with unknown-model diagnostics

## Goal & Context

Claude Code can return a successful JSON result for a custom gateway model while emitting an unrecognized-model diagnostic on stderr. The native review backend currently discards that terminal review and refunds its attempt. Preserve valid successful reviews without weakening transport failures.

## Architecture & Data Models

Keep the shared review driver, backend registry, receipt schema and finalizers. Correct only Claude result classification and update the existing transport documentation.

## API Contracts

The sole JSON result envelope remains the reviewer output authority. Stderr stays diagnostic. Explicit models never fall back to another model.

## Edge Cases & Constraints

Invalid JSON, wrong envelopes, error envelopes, nonzero process exits and timeouts remain failures even if their text contains a verdict. Preserve genuine unavailable-model fallback and its cache semantics.

## Acceptance Criteria

- **R1:** A successful Claude JSON result accompanied by an unrecognized-model diagnostic can finalize official plan, implementation and completion reviews. Errors: malformed or wrong-type output and error envelopes cannot become verdicts.
- **R2:** Explicit custom models are retained on success, with no fallback or false availability-cache entry. Errors: genuine unavailable-model responses keep the existing bounded ladder; explicit selections fail without substitution.
- **R3:** A failed process cannot finalize a verdict found in its output, and attempts are refunded through the official handler. Errors: nonzero exits, timeouts and unavailable/error envelopes publish no new valid receipt.
- **R4:** Implementation re-review retains its session and previous findings after a successful warning-bearing result. Errors: stale identity and failed re-review retain existing safeguards.
- **R5:** Existing transport documentation accurately distinguishes successful custom-model diagnostics from failures. No error surface beyond the documented result contract.

## Boundaries

No new backend, model-specific option, new config key, prompt rewrite, provider fallback, global installation or evaluation trace in the public branch. Standing G1/G2 remain applicable.

## Decision Context

A real terminal custom-model response and a native official review demonstrate the false failure. Documented aliases do not remove the diagnostic. Fixing the existing backend preserves the current architecture and avoids a redundant integration.
