---
title: Docs for a hash-identity fix inherit the hash's precision
date: "2026-08-01"
track: bug
category: data
module: plugins/flow-next/docs/flowctl.md
tags: [chart, fingerprint, changelog, docs-pin, review-feedback]
problem_type: data
symptoms: Review rejects changelog/docs prose as overstating a fixed defect; a new docs test claims to pin a contract it only greps for
root_cause: Prose written from the spec summary instead of the hash payload; the pin greps the whole file instead of the section that owns the contract
resolution_type: documentation
related_to: [bug/data/adding-a-key-to-a-content-hash-orphans-2026-08-01, bug/data/migrationrollback-cli-10-review-cycle-2026-05-08]
---

## Problem

The docs task for a content-hash fix (fn-154: reopen epoch folded into
`_briefing_fingerprint`) shipped prose that was true in spirit and wrong in
scope, twice in a row. Review round 1: the CHANGELOG said the command had been
"idempotent on proposal content alone" and that a reopened-and-finished chart
would echo the stale briefing - but the fingerprint hashes chart revision,
proposal, AND rendered evidence, so the defect only fired when none of the
three had moved. Round 2: the same entry claimed the new `supersedes_stale`
key kept "every envelope that exists today byte-unchanged" - false for a fresh
superseding emission, a result class that already existed (change a decision
after reopen) and now carries the key.

The same round also caught the new docs-inventory test: it grepped the WHOLE
of `flowctl.md` for paragraphs containing `supersedes_stale`, then asserted
loose tokens (`array`, `noop`, `absent`). It would have passed with the
contract moved out of the `### v1 JSON envelope` section, or with the
fresh-only and non-empty clauses deleted, while its own docstring claimed to
pin exactly those.

## What Didn't Work

Writing the changelog from the spec's Overview instead of from the identity
function. The spec's own repro is precise ("with the decision ledger
untouched - the only path on which the fingerprint still matches"); the
customer-facing retelling dropped the qualifier to make a cleaner story, and
the cleaner story described a bigger bug than the one that was fixed.

## Solution

- Read the hash's payload before describing the bug it caused. Name every
  input (`plugins/flow-next/scripts/flowctl.py` `_briefing_fingerprint`:
  chart_revision + proposal + evidence_digest, now + reopened_at) and state the
  bound: which inputs had to be unchanged for the defect to fire, and which
  route always worked.
- For an additive envelope key, claim byte-identity for the classes that
  actually keep their shape ("every non-superseding envelope"), and name the
  one class whose shape changes. "Nothing changed" is almost never true of a
  field that is emitted at all.
- Scope a docs pin to the section that OWNS the contract. The rewritten
  `test_supersedes_stale_discriminator_documented` slices
  `### v1 JSON envelope` .. `### Subcommands`, normalizes hyphens/whitespace so
  a reflow does not break it, then asserts each clause by name (array of B-ID
  strings, `noop: false`, non-empty, absent from idempotent-retry /
  first-emission / error envelopes, sidecar `briefings[]`).
- Prove the pin is non-vacuous before committing it: in a scratch copy, move
  the paragraph out of the section and delete a clause, and check both fail.

## Prevention

- **Docs for a hash/identity fix inherit the hash's precision.** Before writing
  the entry, open the hash function and list its inputs. A changelog sentence
  that implies a broader trigger than the payload allows is a false bug report
  shipped to users.
- **"Byte-unchanged" needs a subject.** Say WHICH envelope classes are
  unchanged. An additive field always changes at least one.
- **A whole-file grep is not a contract pin.** If the docstring says "must be
  documented where consumers look", the assertion must slice that section;
  otherwise it certifies presence, not location - and the contract can drift
  out from under it silently.
- Cheap check that would have caught both: run the real CLI once (throwaway
  repo, reopen -> re-brief), observe the envelope classes, and write the prose
  from what you saw rather than from the spec's summary.
