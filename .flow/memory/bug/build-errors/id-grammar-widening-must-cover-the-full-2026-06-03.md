---
title: "Id-grammar widening must cover the FULL command surface, not just named commands"
date: "2026-06-03"
track: bug
category: build-errors
module: plugins/flow-next/scripts/flowctl.py
tags: [fn-52, tracker-sync, id-resolution, canonicalizer, enumeration, impl-review, case-rule, validator-separation]
problem_type: build-error
symptoms: "11 introduced impl-review findings over 3 rounds: tracker handles failed to resolve in next/tasks/validate/set-deps/spec-deps/task-setters/spec-setters; uppercase handle died at is_*_id gate; slugged identifier accepted; whitespace persisted"
root_cause: Canonicalizer wired only into the commands the spec bullet named; every other direct-path / fn-only-regex / pre-gate validation site was missed. Identifier validated with the resolver grammar (too loose) and stored raw (not stripped).
resolution_type: fix
related_to: [bug/build-errors/detectvalidate-must-require-specs-dir-2026-05-08, bug/build-errors/fn-44-review-cycle-lessons-2026-05-21]
---

## Problem
fn-52.10 widened flowctl's id grammar so a tracker key (WOR-17) resolves as a
flow handle. The first impl-review pass shipped the grammar + the headline
resolver (`expand_bare_spec_id`) + the obvious lifecycle commands, but rp review
surfaced 11 *introduced* gaps across 3 rounds — every one a command path that
still pathed directly to `.flow/{specs,tasks}/<id>.json` (or re-filtered through
an `fn-*` regex) WITHOUT routing the arg through the new canonicalizer.

## What Didn't Work
Wiring the canonicalizer into the commands the spec's acceptance bullet-list
named (show/cat/start/done/dep) and assuming that covered it. It did not:
`next`, `tasks` (unfiltered glob), `validate --all`, `task set-deps`,
`spec add-dep`/`rm-dep`, the task section setters (`set-description`/
`-acceptance`/`-spec`/`reset`/`set-backend`), and every spec/sync setter
(`set-plan`, `set-*-review-status`, `set-branch`, `set-title`, `close`,
`sync set-*`) each had their OWN direct-path or fn-only-regex site. Three more
gaps were validation, not wiring: uppercase handle (`WOR-17`) failed the
`is_spec_id`/`is_task_id` gate BEFORE the casefolding resolver ran; a
tracker-identifier validator built on `parse_any_id` accepted a slugged
`WOR-17-fix` (because parse_any_id also matches the canonical slug form); and a
quoted `"  WOR-17  "` validated on `.strip()` but persisted the raw whitespace.

## Solution
1. One central front-door per arg KIND, called BEFORE any IO:
   `resolve_spec_id_arg` (casefold→validate→expand) for every spec/sync setter;
   `resolve_task_arg` (+ `casefold_handle` at each command's gate) for every
   task command. flowctl.py.
2. Enumeration sites (`iter_spec_json_files`, `cmd_next`, `cmd_tasks`,
   `cmd_validate --all`, `cmd_list`): take EVERY `is_spec_id`/`is_task_id` stem;
   never re-filter `iter_spec_json_files` output through an `fn-*` regex (it
   already yields only valid stems). Keep native `fn-N` collision/allocation
   detection separate via `parse_id` (fn-only by contract).
3. A STRICT identifier validator (`parse_tracker_identifier`, regex
   `^[A-Za-z][A-Za-z0-9]{0,9}-[1-9][0-9]*$`) — NOT `parse_any_id`, which is the
   resolver grammar and accepts the slugged canonical form. It returns the
   stripped display form; callers persist THAT, never the raw input.

## Prevention
- When a feature widens an id grammar, the checklist is "every command that
  takes that id", not "the commands the acceptance bullet happens to name."
  grep for `glob(f"{...}.*.json")`, `/ TASKS_DIR / f"{id}`, `/ SPECS_JSON_DIR`,
  and `re.match(r"^fn-` to find every direct-path / fn-only site.
- A resolver grammar (accepts aliases + canonical + slugged) is the WRONG
  validator for a display identifier (must be the bare form only). Keep the two
  parsers separate.
- A validator that strips for its check must RETURN the cleaned value so callers
  persist the canonical form — validating one string and storing another is a
  latent data bug.
- Casefold/normalize an arg BEFORE the `is_*_id` gate, not only inside the
  resolver the gate guards — otherwise uppercase/alias input dies at the gate.
