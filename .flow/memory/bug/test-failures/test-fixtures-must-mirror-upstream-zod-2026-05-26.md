---
title: "Test fixtures must mirror upstream Zod enum, not concept"
date: "2026-05-26"
track: bug
category: test-failures
module: "plugins/flow-next/tests/fixtures/clawpatch-map, plugins/flow-next/scripts/flowctl.py"
tags: [fn-50, clawpatch, zod-schema, fixture-drift, confidence-enum, codex-review, duck-typing]
problem_type: test-failure
symptoms: "Codex impl-review flagged fixture 'confidence: 0.92' (numeric) vs upstream Zod enum 'high|medium|low' — fixture locked an impossible 'valid' record shape"
root_cause: Fixture authored from inferred field shapes instead of reading upstream Zod source as ground truth
resolution_type: fix
---

## Problem

When wrapping an upstream third-party CLI's data schema in a flowctl reader, test fixtures and docs examples drifted from the real upstream `Zod` schema. Codex impl-review caught it immediately — the fixture used `confidence: 0.92` (numeric), but upstream clawpatch's `featureRecordSchema` defines `confidence: z.enum(["high", "medium", "low"])`. The fixture was an "impossible valid record."

A second residual note from the same review flagged `kind: "module"` where upstream `featureKinds` does not include "module" (the canonical kinds are `cli-command, route, ui-flow, service, job, agent-tool, library, config, release, test-suite, infra, unknown`).

The reader code itself was correct (duck-typed, didn't validate the enum), but tests and docs would have anchored the wrong mental model in users' heads.

## What Didn't Work

Building fixtures from "what feels reasonable for a feature record" rather than reading the upstream Zod source. The fields and shapes were intuitive guesses (numeric confidence 0-1, broad `kind: "module"`) that happened to match the *concept* but not the *contract*.

## Solution

1. **Fetch upstream Zod source before writing fixtures.** For `clawpatch`, that's `https://raw.githubusercontent.com/openclaw/clawpatch/main/src/types.ts`. Search for the schema name in the spec (`featureRecordSchema`) and read the actual enum definitions.
2. **Lock the enum value in a test assertion.** Added `self.assertEqual(feat["confidence"], "high")` and `self.assertEqual(feat["kind"], "service")` so future drift surfaces as a test failure rather than silently propagating.
3. **Note duck-typing in the reader docstring.** The reader code intentionally does NOT validate `kind` (only `schemaVersion`), so forward-compat with future enum members is automatic — but the fixture should still reflect today's truth.

## Prevention

When the task spec includes an "investigation target" pointing at an upstream Zod / TypeScript / JSON-schema source (this spec listed `https://github.com/openclaw/clawpatch/blob/main/src/types.ts` as required reading), **fetch it as raw text and grep for the schema name BEFORE writing any fixture**. Don't infer shapes from prose — read the source.

For the `flow-next:capture` / `flow-next:plan` flow: when a spec references an upstream schema URL, the investigator should record the *full enum domain* (not just one example value) in the task spec's "Key context" so the implementer can't accidentally invent a value.
