---
satisfies: [R6, R7, R14]
---
# fn-122-harden-verdict-graduate-recurring.1 flowctl: hardened status + memory mark-hardened plumbing

## Description
Add the `hardened` memory status and the `mark-hardened` command to flowctl — the thin persistence layer the audit skill's Harden outcome will call. No judgment lives here: this task teaches the schema a new status value plus one optional field, adds a sibling of `mark-stale`, and makes the existing status filters exclude hardened by default.

This is the spec's **early proof point**. It validates Decision 4: that extending `MEMORY_STATUS` gives `memory list` / `memory search` / memory-scout exclusion for free through the existing status-filter path, with no scout-side change. If exclusion turns out to need scout changes, or the status enum is load-bearing somewhere that makes a third value unsafe, STOP and report — do not proceed to the audit-skill task, because every sentence of that skill prose names this CLI surface.

**Size:** M
**Files:**
- `plugins/flow-next/scripts/flowctl.py` and its byte-identical dogfood copy `.flow/bin/flowctl.py`
- `plugins/flow-next/scripts/flowctl_bootstrap.py` and `.flow/bin/flowctl_bootstrap.py` (`SOURCE_SHA256` / `HELP_SHA256` re-pin)
- `plugins/flow-next/scripts/flowctl-help.txt` and `.flow/bin/flowctl-help.txt` (regenerated argparse help snapshot)
- `plugins/flow-next/tests/test_memory_mark_hardened.py` (new)
- `plugins/flow-next/tests/test_flowctl_surface.py` (CLI surface snapshot)
- `plugins/flow-next/tests/test_memory_mark_fresh.py` and `test_memory_mark_stale.py` (both handlers change — see field invariants below)

**In scope beyond the new command:** the EXISTING `mark-stale` and `mark-fresh` handlers change too. Per-status field invariants must hold after every mutation, not just after the new one.

### Approach

- Extend `MEMORY_STATUS` (flowctl.py:9252) with `"hardened"`; add `hardened_into` to `MEMORY_OPTIONAL_FIELDS` (:9210-9222) and place it in `MEMORY_FIELD_ORDER` (:9259-9280) near the `status` / `stale_reason` region so writes stay deterministic.
- Clone `cmd_memory_mark_stale` (:11862-11924) for the new command. Reuse `_memory_resolve_categorized_entry` (:11826) for id resolution and legacy-flat-file rejection — do not reimplement either. Write through `write_memory_entry` (:9601) so validation and atomicity are inherited.
- **Field invariants per status — enforce the whole set in every mutation.** The three statuses own disjoint optional fields: `active` has neither `hardened_into` nor `stale_reason`/`stale_date`; `stale` has the stale pair and no `hardened_into`; `hardened` has `hardened_into` and no stale pair. So:
  - `mark-hardened` sets `hardened_into` AND clears `stale_reason` / `stale_date` (this is what makes `stale -> hardened` legal without leaving contradictory frontmatter).
  - `mark-fresh` (`cmd_memory_mark_fresh`, :11952) already pops `status, stale_reason, stale_date, audit_notes` — add `hardened_into` to that tuple.
  - `mark-stale` (`cmd_memory_mark_stale`, :11890-11901) currently clears nothing — it must now drop `hardened_into`, so a hardened entry marked stale stops pointing at a gate it no longer claims.
- **`last_audited` is a UTC date (`YYYY-MM-DD`)**, matching both existing handlers (`:11893`, `:11947`) and `_MEMORY_QUOTED_STRING_FIELDS` (`:9516`). Do NOT introduce a full timestamp. Consequence for tests: a same-day re-mark does not change `last_audited`, so assert idempotency on `hardened_into` replacement, never on an observable stamp change.
- `--gate-ref` is stored **verbatim**. The audit skill composes a `<path>#<rule-id> -- <note>` string, but flowctl does not parse, split, or validate that convention — only non-emptiness. Parsing it here would be judgment leaking into plumbing.
- The two status filters — `cmd_memory_list` (:11479-11485) and `cmd_memory_search` (:11700-11705) — are near-identical and MUST change in lockstep. Default (`active`) excludes both `stale` and `hardened`; `--status hardened` selects only hardened; `--status all` includes everything.
- argparse (:30171-30410): add `"hardened"` to BOTH `--status` choice lists, and add the `mark-hardened` subparser using the `mark-stale` subparser (:30338-30383) as the template, with `--gate-ref` in the role `--reason` plays there.
- Surface `hardened_into` in `memory list` / `search` / `read` JSON output when present.

Follow the repo's agentic-vs-deterministic split: this command stores what it is told. It never decides whether an entry should be hardened, never inspects the gate, never generates artifact text.

### Investigation targets

**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py:11862-11970` — `cmd_memory_mark_stale` and `cmd_memory_mark_fresh`, the exact shape to mirror (including the `--json` vs human output branch)
- `plugins/flow-next/scripts/flowctl.py:11826-11859` — `_memory_resolve_categorized_entry`, the shared resolver + legacy rejection
- `plugins/flow-next/scripts/flowctl.py:11445-11556` and `:11638-11790` — `cmd_memory_list` / `cmd_memory_search` status-filter blocks
- `plugins/flow-next/scripts/flowctl.py:30338-30383` — the mark-stale argparse subparser template
- `plugins/flow-next/tests/test_memory_mark_stale.py` — the test file shape and method-naming convention to mirror

**Optional** (reference as needed):
- `plugins/flow-next/tests/test_startup_bootstrap.py:305-320` — the pin assertions and the byte-identical dogfood check
- `plugins/flow-next/tests/test_flowctl_surface.py:98-106` — the literal `memory <subcmd>` surface list

### Key context

**The flowctl.py edit tax (this is the recurring failure mode — budget for it):** editing `flowctl.py` is never a single-file change. Every edit requires, in the same commit:

1. The dogfood copy `.flow/bin/flowctl.py` kept byte-identical.
2. `SOURCE_SHA256` recomputed against the new `flowctl.py` bytes in `flowctl_bootstrap.py`, and the same in `.flow/bin/flowctl_bootstrap.py`.
3. `flowctl-help.txt` regenerated from the new argparse surface, `HELP_SHA256` re-pinned, and the `.flow/bin/` copy refreshed.
4. `test_flowctl_surface.py`'s literal snapshot updated to include `memory mark-hardened`.

Skipping any of these fails `test_startup_bootstrap` / `test_dogfood_bootstrap_is_byte_identical`. Run the focused suite before declaring done.

**Test the production path, not a parallel construction** — exercise the real argparse routing (two-token `memory mark-hardened` form), not a mock-patched helper that bypasses it.

## Acceptance

- [ ] `MEMORY_STATUS` includes `hardened`; `hardened_into` is an accepted optional frontmatter field on both memory tracks and has a fixed position in `MEMORY_FIELD_ORDER`.
- [ ] `flowctl memory mark-hardened <id> --gate-ref "<text>" [--audited-by ...] [--json]` sets `status: hardened`, sets `hardened_into` verbatim, stamps `last_audited` as a UTC **date** (`YYYY-MM-DD`, same as the sibling handlers), records optional audit notes, and leaves the entry body byte-identical.
- [ ] Idempotent: re-running `mark-hardened` on an already-hardened entry replaces `hardened_into` without error. The test asserts on the replaced `hardened_into`, NOT on a changed `last_audited` (a same-day re-mark cannot change a date-precision stamp).
- [ ] **Full transition matrix with field invariants (R14).** Every mutation leaves frontmatter consistent with exactly one status — no field from the prior status survives:
  - `active -> hardened`: `hardened_into` set.
  - `stale -> hardened`: `hardened_into` set AND `stale_reason` / `stale_date` cleared.
  - `hardened -> stale` (via existing `mark-stale`): stale fields set AND `hardened_into` dropped.
  - `hardened -> active` (via existing `mark-fresh`): `hardened_into` dropped and the stale family cleared.
  Each row has a test asserting both the field that was set and the fields that were cleared.
- [ ] Errors: unknown id exits nonzero with a message naming the id; a missing OR empty `--gate-ref` is a usage error; a legacy flat-file id is rejected with the existing migrate-first message. flowctl does NOT validate the `<path>#<rule-id>` convention — only non-emptiness.
- [ ] Write-side validation: an entry carrying an unknown status value fails `write_memory_entry` validation with a message naming the bad value. Note in evidence that this is a WRITE-side guarantee only — `_memory_read_entry` does not validate, which is the basis of the honest R15 contract documented in task `.3`.
- [ ] Default `memory list` and `memory search` exclude `hardened` entries; `--status hardened` returns only them; `--status all` includes them. Both filters verified, not just list (R7).
- [ ] `hardened_into` appears in `memory list` / `search` / `read` JSON output when set.
- [ ] New `plugins/flow-next/tests/test_memory_mark_hardened.py` covers: round-trip, idempotency, body preservation, both inbound transitions, unknown id, missing/empty `--gate-ref`, legacy-id rejection, human and `--json` output. The `hardened -> stale` and `hardened -> active` clearing assertions live in the existing `test_memory_mark_stale.py` / `test_memory_mark_fresh.py` files, next to the handlers they cover.
- [ ] `test_flowctl_surface.py` snapshot updated; `SOURCE_SHA256` + `HELP_SHA256` re-pinned; `flowctl-help.txt` regenerated; all four `.flow/bin/` dogfood copies byte-identical to their `plugins/flow-next/scripts/` originals.
- [ ] Focused suite green: `cd plugins/flow-next/tests && python3 -m unittest test_memory_mark_stale test_memory_mark_fresh test_memory_mark_hardened test_flowctl_surface test_startup_bootstrap -q`
- [ ] Proof-point check reported explicitly: memory-scout needs NO change because exclusion rides the existing status filter (or, if it does need one, STOP and report before task .2).


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
