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

### Approach

**Config leaf.** `tracker.*` defaults live in `get_default_tracker_config()` (`flowctl.py:1069-1080`). Strict-enum precedent: `pipeline.qa` (`:1322`) and `pilot.autonomy` (`:1339`) - only the literal positive value activates, never a coerced bool. There is no central enum registry, so write-time validation follows the ad hoc `cmd_config_set` pattern (`:9032+`, e.g. `review.backend` at `:9043`).

**Decide the materialization question deliberately.** R9 needs `tracker.specIds` to be *unset-detectable* so setup can tell "never asked" from "answered `flow`". A materialized default would make those indistinguishable and silently break the setup question. See `_INIT_UNMATERIALIZED_BLOCKS` (`:1358`). Whichever way you go, state it in the task evidence and cover it with a test.

**Synthetic keys.** The grammar layer needs NO changes: `parse_any_id` (`:2584-2617`) already accepts `^[a-z][a-z0-9]{0,9}-…`, so `gh` and `gl` parse today, and `id_sort_key` / `is_spec_id` / `is_task_id` / `spec_id_from_task` all route through it. Only `fn` is globally reserved (`RESERVED_TRACKER_KEY`, `:2573`). The work is confined to the minting path in `cmd_spec_create` (`:14760-14790`).

Do **not** reuse `validate_tracker_identifier`'s `allow_reference` mode (`:2724-2801`) - it is link-time only and returns `("", n, display)` with an EMPTY key, the wrong shape for minting a resolvable id. Add a mint-side parse for `#123` and `<project>#456`. Use the project-scoped `iid` for GitLab, never the opaque global id.

**Validate downgrade.** `cmd_validate:26363-26386` appends the collision message to `root_errors`. This is a retarget to warnings, not new logic: `ids` is built from unique file stems, so "full ids are distinct" is structurally guaranteed. Existing assertions in `test_validate_all_diagnostics.py:93-146` expect `root_errors` and must move.

**Resolver: verify before building.** `expand_bare_spec_id` (`:7498-7581`) already errors with "Spec id … is ambiguous. Matches: … Use the full slug to disambiguate." for the native-`fn` branch, tested at `test_expand_bare_spec_id.py:69,84`. Check it against the live `fn-122` pair first. If it already behaves correctly, R12 reduces to a regression test and you should say so rather than adding redundant code.

### Investigation targets

**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py:1069-1080` and `:1322`, `:1339` - tracker defaults and the strict-enum precedent
- `plugins/flow-next/scripts/flowctl.py:14760-14790` - both id-composition branches
- `plugins/flow-next/scripts/flowctl.py:2724-2801` - `validate_tracker_identifier` and why `allow_reference` is the wrong shape here
- `plugins/flow-next/scripts/flowctl.py:26363-26386` - the collision append site
- `plugins/flow-next/scripts/flowctl.py:7498-7581` - `expand_bare_spec_id`

**Optional** (reference as needed):
- `plugins/flow-next/scripts/flowctl.py:1358` - `_INIT_UNMATERIALIZED_BLOCKS`
- `plugins/flow-next/scripts/flowctl.py:9032-9060` - ad hoc `cmd_config_set` validation

### Key context

Same flowctl.py edit tax as task `.1`: dual copies, `SOURCE_SHA256` re-pin, and `flowctl-help.txt` + `HELP_SHA256` if argparse changed.

Depends on `.1` because both edit `flowctl.py` and should not be in flight simultaneously.

## Acceptance

- [ ] `tracker.specIds` exists as a strict string enum defaulting to `flow`; only the literal `tracker` activates it. A coerced bool, a typo, and a null all resolve to `flow` (R6).
- [ ] The unset-vs-`flow` distinction is preserved and tested, so setup can detect "never asked" (R9 dependency). The materialization decision is stated in the task evidence.
- [ ] Synthetic minting: `tracker.type=github` + issue `123` mints `gh-123-slug`; `tracker.type=gitlab` + `<project>#456` mints `gl-456-slug` using the project-scoped `iid` (R14).
- [ ] Synthesis is type-gated. A Linear or Jira repo whose native tracker key is literally `GH` mints from its own native key with no synthesis and no collision. Covered by a test (R14).
- [ ] Minted ids resolve as bare aliases (`gh-123`, `gl-456`) the same way `wor-17` does, and no grammar-layer function was modified.
- [ ] A duplicate ordinal whose full ids are distinct is reported as a **warning**, not a root error; `total_errors` no longer counts it. A test covers the live `fn-122` pair (R13).
- [ ] Bare `fn-N` ambiguity behavior verified against the live `fn-122` pair. If `expand_bare_spec_id` already satisfies R12, the task adds a regression test and says so explicitly rather than adding new resolver code (R12).
- [ ] Dual copies byte-identical; `SOURCE_SHA256` re-pinned in both bootstraps.
- [ ] Focused suite green: `cd plugins/flow-next/tests && python3 -m unittest test_tracker_config test_validate_all_diagnostics test_expand_bare_spec_id test_flowctl_surface test_startup_bootstrap -q`


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
