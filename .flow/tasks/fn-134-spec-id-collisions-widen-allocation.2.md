---
satisfies: [R6, R12, R13, R14]
---
# fn-134-spec-id-collisions-widen-allocation.2 flowctl: tracker.specIds, synthetic gh/gl keys, validate + resolver ergonomics

## Description

The flowctl half of move B, plus the two ergonomics fixes. Adds the `tracker.specIds` config leaf, synthetic `gh-` / `gl-` key minting so GitHub and GitLab can use tracker-first, downgrades the duplicate-ordinal validate error to a warning, and verifies (rather than assumes) that bare `fn-N` already disambiguates.

**Size:** M
**Files:**
- `plugins/flow-next/scripts/flowctl.py` (+ byte-identical `.flow/bin/flowctl.py`)
- `plugins/flow-next/scripts/flowctl_bootstrap.py` (+ `.flow/bin/` copy), and `flowctl-help.txt` + `HELP_SHA256` if the argparse surface changes
- `plugins/flow-next/tests/test_tracker_config.py`, `test_validate_all_diagnostics.py`, `test_expand_bare_spec_id.py`

## Approach

**Config leaf.** `tracker.*` defaults live in `get_default_tracker_config()` (`flowctl.py:1069-1080`). Strict-enum precedent: `pipeline.qa` (`:1322`) and `pilot.autonomy` (`:1339`) - only the literal positive value activates, never a coerced bool. There is no central enum registry, so write-time validation follows the ad hoc `cmd_config_set` pattern (`:9032+`, e.g. `review.backend` at `:9043`).

**Decide the materialization question deliberately.** R9 needs `tracker.specIds` to be *unset-detectable* so setup can tell "never asked" from "answered `flow`". A materialized default would make those indistinguishable and silently break the setup question. See `_INIT_UNMATERIALIZED_BLOCKS` (`:1358`). Whichever way you go, state it in the task evidence and cover it with a test.

**Synthetic keys need contextual reservation + preflight, not just type-gating.** Type-gating alone is NOT sufficient: ids are permanent while config is not. A repo that ran Linear with team key `GH` (accumulating `gh-123-slug` specs) and later re-points to GitHub would mint a colliding `gh-123-slug`; and a GitHub-configured repo can still be handed an explicit native `GH-123` at link time. So: while `tracker.type` is `github`/`gitlab`, reserve the matching prefix in that repo and reject an explicit native identifier using it at link and create time; and **preflight the existing store** for a colliding canonical id or resolvable alias before minting, refusing with an actionable message. Native `GH` behavior is unchanged while the type stays `linear`/`jira`. Re-pointing `tracker.type` is a documented hazard, and the preflight is what makes it safe.

The grammar layer needs NO changes: `parse_any_id` (`:2584-2617`) already accepts `^[a-z][a-z0-9]{0,9}-…`, so `gh` and `gl` parse today, and `id_sort_key` / `is_spec_id` / `is_task_id` / `spec_id_from_task` all route through it. Only `fn` is globally reserved (`RESERVED_TRACKER_KEY`, `:2573`). The work is confined to the minting path in `cmd_spec_create` (`:14760-14790`).

Do **not** reuse `validate_tracker_identifier`'s `allow_reference` mode (`:2724-2801`) - it is link-time only and returns `("", n, display)` with an EMPTY key, the wrong shape for minting a resolvable id. Add a mint-side parse for `#123` and `<project>#456`. Use the project-scoped `iid` for GitLab, never the opaque global id.

**Validate downgrade needs a JSON contract, not just a retarget.** `cmd_validate:26363-26386` appends to `root_errors`. `validate --all --json` today exposes `root_errors`, per-spec `warnings`, and `total_warnings` but **no top-level root-warning collection** - verified. Moving the message into the existing warning count would print and count it while dropping its text from JSON, which is exactly the machine-diagnosability regression 3.2.1 fixed. Add a top-level **`root_warnings`** field, include it in `total_warnings`, and keep the text renderer, docs, and the spec's Quick commands consistent. Existing assertions in `test_validate_all_diagnostics.py:93-146` expect `root_errors` and must move.

**Resolver: verify before building.** `expand_bare_spec_id` (`:7498-7581`) already errors with "Spec id … is ambiguous. Matches: … Use the full slug to disambiguate." for the native-`fn` branch, tested at `test_expand_bare_spec_id.py:69,84`. Check it against the live `fn-122` pair first. If it already behaves correctly, R12 reduces to a regression test and you should say so rather than adding redundant code.

## Investigation targets

**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py:1069-1080` and `:1322`, `:1339` - tracker defaults and the strict-enum precedent
- `plugins/flow-next/scripts/flowctl.py:14760-14790` - both id-composition branches
- `plugins/flow-next/scripts/flowctl.py:2724-2801` - `validate_tracker_identifier` and why `allow_reference` is the wrong shape here
- `plugins/flow-next/scripts/flowctl.py:26363-26386` - the collision append site
- `plugins/flow-next/scripts/flowctl.py:7498-7581` - `expand_bare_spec_id`

**Optional** (reference as needed):
- `plugins/flow-next/scripts/flowctl.py:1358` - `_INIT_UNMATERIALIZED_BLOCKS`
- `plugins/flow-next/scripts/flowctl.py:9032-9060` - ad hoc `cmd_config_set` validation

## Key context

Same flowctl.py edit tax as task `.1`: dual copies, `SOURCE_SHA256` re-pin, and `flowctl-help.txt` + `HELP_SHA256` if argparse changed.

Depends on `.1` because both edit `flowctl.py` and should not be in flight simultaneously.


## Acceptance

- [ ] `tracker.specIds` is a strict string enum defaulting to `flow`, with **both contracts tested separately**: `config set tracker.specIds <invalid>` is **rejected** with a usage error, and an invalid value already on disk **fails closed** to `flow` on read. Only the literal `tracker` activates (R6).
- [ ] The unset-vs-`flow` distinction is preserved and tested, so setup can detect "never asked" (R9 dependency). The materialization decision is stated in the task evidence.
- [ ] Synthetic minting: `tracker.type=github` + issue `123` mints `gh-123-slug`; `tracker.type=gitlab` + `<project>#456` mints `gl-456-slug` using the project-scoped `iid` (R14).
- [ ] Synthesis is guarded by contextual reservation AND a preflight, not type-gating alone: while the type is `github`/`gitlab` the matching prefix is reserved and an explicit native identifier using it is rejected at link and create time; before minting, the store is preflighted for a colliding canonical id or resolvable alias and refuses with an actionable message (R14).
- [ ] Tests cover both history cases: a Linear/Jira repo natively keyed `GH` (no synthesis, unchanged behavior), and a **mixed historical store** where a `gh-123` spec predates a re-point to GitHub (R14).
- [ ] Minted ids resolve as bare aliases (`gh-123`, `gl-456`) the same way `wor-17` does, and no grammar-layer function was modified.
- [ ] A duplicate ordinal whose full ids are distinct is a **machine-readable warning**: a new top-level `root_warnings` field carries the text, `total_warnings` includes it, `total_errors` no longer counts it, and the text renderer and docs agree. A test covers the live `fn-122` pair in **both** renderers (R13).
- [ ] Bare `fn-N` ambiguity behavior verified against the live `fn-122` pair. If `expand_bare_spec_id` already satisfies R12, the task adds a regression test and says so explicitly rather than adding new resolver code (R12).
- [ ] Dual copies byte-identical; `SOURCE_SHA256` re-pinned in both bootstraps.
- [ ] Focused suite green: `cd plugins/flow-next/tests && python3 -m unittest test_tracker_config test_validate_all_diagnostics test_expand_bare_spec_id test_flowctl_surface test_startup_bootstrap -q`

## Done summary
Added `tracker.specIds` (strict `flow|tracker` enum), synthetic `gh-`/`gl-` key minting so GitHub and GitLab can use tracker-first, and moved duplicate-ordinal reporting from `root_errors` to a new machine-readable `root_warnings` field.

Implemented by grok-4.5 via the grok CLI bridge; reviewed in-host (opus-5). Verified behaviorally rather than from the summary:

- Config: `config set tracker.specIds bogus` is rejected with a usage error; the key is absent from `.flow/config.json` after init (unset-detectable, so setup can tell "never asked" from "answered flow") while the merged read returns `flow`. Grok chose NOT to materialize it at init and recorded the reason.
- Validate: `root_errors` is now empty on this repo and `root_warnings` carries the fn-122 collision text, with `total_warnings=1` and the text renderer showing it under Warnings. `total_errors` dropped 50 -> 49 accordingly. The new field was necessary: without it the message would have been counted but dropped from JSON.
- Resolver: grok verified before building. `flowctl show fn-122` already errored with the correct ambiguity message listing both candidates, so R12 landed as a regression test only and no redundant resolver code was added.
- Guards: the mixed-historical-store test is real — a Linear repo keyed `GH` mints `gh-123-old-linear`, then a re-point to GitHub attempting to mint issue 123 is refused with a message naming the colliding id. That is the exact case type-gating alone would have missed.

No argparse surface change, so `flowctl-help.txt` and `HELP_SHA256` correctly untouched.
## Evidence
- Commits: 1cc3c60f
- Tests: python3 scripts/run_tests_parallel.py (files=131 ran=2375 failures=0 errors=0), cd plugins/flow-next/tests && python3 -m unittest test_tracker_config test_validate_all_diagnostics test_expand_bare_spec_id test_flowctl_surface test_startup_bootstrap -q (75 tests OK), behavioral: config set tracker.specIds bogus -> rejected; key absent from .flow/config.json; merged read = flow, behavioral: validate --all --json root_errors=[] root_warnings=[fn-122 collision] total_warnings=1; text renderer shows it under Warnings, behavioral: flowctl show fn-122 -> ambiguity error listing both candidates (pre-existing, regression test only), dual-copy byte-identical + SOURCE_SHA256 matches; flowctl-help.txt unchanged
- PRs: