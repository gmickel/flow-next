---
title: "Path-handoff template id slots must use canonical ids, not aliases"
date: "2026-07-19"
track: bug
category: integration
module: plugins/flow-next/skills/flow-next-work/references/codex-delegation.md
tags: [fn-103, codex-delegation, path-handoff, alias-resolution, prose-contract, review-feedback]
problem_type: integration
symptoms: alias-filled template points delegate at nonexistent .flow/tasks/<alias>.md
root_cause: flowctl id namespace resolves aliases; the filesystem path namespace does not
resolution_type: fix
related_to: [bug/integration/byte-for-byte-spec-contract-branch-2026-07-01, bug/integration/rp-builder-file-slices-cause-false-2026-06-10, bug/integration/spec-named-config-keys-must-be-checked-2026-07-15, bug/integration/summary-sinks-for-repeatable-mixed-2026-07-19]
---

## Problem
fn-103.1 replaced the composed delegation brief with a fixed path-handoff template ("read `.flow/tasks/<task-id>.md` + `.flow/specs/<spec-id>.md`"). Codex impl-review flagged (Major/75): `/flow-next:work` accepts short aliases like `fn-103.1`; flowctl resolves them internally, but the literal alias path `.flow/tasks/fn-103.1.md` does not exist on disk - an alias-filled template hands the delegate two missing files and nothing errors until the run wastes itself.

## What Didn't Work
Treating the template's id slots as "whatever id the worker was invoked with". The id namespace (flowctl-resolvable) and the path namespace (literal files) diverge for aliases.

## Solution
Pin canonical-id resolution at both fill sites: the reference template section and worker.md step 2 now require `flowctl show <id> --json` -> `.id` / `.spec` for the two slots, never a short alias. Regression test `test_reference_template_slots_take_canonical_ids` asserts the contract in both files (commit e76025d5).

## Prevention
Whenever a prompt/template interpolates an id into a FILESYSTEM path, require the canonical id from the resolver (`flowctl show --json`), and add a prose-contract assertion so the requirement can't be swept out in a later rewrite. Also pin load-bearing sentences/blocks as whole normalized strings or exact contiguous blocks, not per-line fragments - fragment assertions tolerate reordering and drift.
