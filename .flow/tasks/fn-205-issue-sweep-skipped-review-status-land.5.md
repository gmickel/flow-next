---
satisfies: [R6]
---
# fn-205-issue-sweep-skipped-review-status-land.5 Closers print the host's invocable command form, with the mirror transform kept in step

## Description
Every closer that prints a copy-pasteable flow-next command must print a form the current host can actually invoke — flat `/flow-next-<name>` on OpenCode (R6). Sixteen literals across five files, and those five files are exactly the ones the Codex mirror rewrites with anchored substitutions, so the transform anchors move in the same change. Depends on the work-skill task: `phases.md` is shared.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-capture/workflow.md`, `plugins/flow-next/skills/flow-next-capture/references/rewrite-mode.md`, `plugins/flow-next/skills/flow-next-capture/references/split-proposal.md`, `plugins/flow-next/skills/flow-next-plan/references/next-steps-menu.md`, `plugins/flow-next/skills/flow-next-work/phases.md`, `scripts/sync-codex.sh`
**Touches:** [plugins/flow-next/skills/flow-next-capture/**, plugins/flow-next/skills/flow-next-plan/references/next-steps-menu.md, plugins/flow-next/skills/flow-next-work/phases.md, scripts/sync-codex.sh, plugins/flow-next/codex/**]

### Approach
- Closer surfaces and their literals: `capture/workflow.md:664-669` (base footer, 4), `capture/references/rewrite-mode.md:91-97` (5), `capture/references/split-proposal.md:79` (1), `plan/references/next-steps-menu.md:11,20-22` (4), `work/phases.md:576` (2).
- State the invariant, not a host matrix: one short clause per closer surface saying the printed command uses the form this host invokes, with OpenCode's flat spelling as the named case and the colon form as the canonical default when the host is indeterminate. Keep the canonical literals in colon form so the existing mirror transform still has something to rewrite. A per-host enumeration table in every closer is the rejected shape (spec Decision Context) — it races the next host and inflates every dispatch.
- Use the shipped signal only: the installer's ownership manifest at `${PLUGIN_ROOT}/.flow-next-opencode-manifest`, already the detection rung in `flow-next-setup/workflow.md:37-38,62`. Do not invent a probe, and do not add a flowctl command for this.
- The silent-failure risk is the mirror: `scripts/sync-codex.sh:389-427` rewrites an enumerated file list with anchored per-pattern seds, and the hard-fail guard at `:2171-2177` only greps the `Recommended next: /flow-next:` shape — one of sixteen literals. Any reworded literal whose anchor stops matching leaves the mirror on the colon form at exit 0. Update the anchors with the prose, and prefer extending the guard's coverage over trusting the reword. A guard failure is load-bearing: fix the content or extend the transform, never relax the guard.
- Watch the double-transform trap: the mirror inherits any host-conditional clause verbatim, so the clause must not tell Codex to branch on a host it is not. Codex's own form is `$flow-next-<name>` and stays the transform's job.
- If any edit lands in `phases.md` section 3c, the hardcoded `SECTION3C` heredoc in `sync-codex.sh` needs the same edit or the mirror goes silently stale at exit 0.
- This task is alone in its wave, so it owns its mirror diff: run `./scripts/sync-codex.sh` twice (idempotency) and commit the regenerated mirror. Validate against the installed OpenCode layout (flat `flow-next-<name>` command files), not just the repo tree.

### Investigation targets
**Required** (read before coding):
- `scripts/sync-codex.sh:389-427` — the enumerated file list and anchored invocation seds
- `scripts/sync-codex.sh:2168-2180` — the actionable-invocation hard-fail guard
- `plugins/flow-next/skills/flow-next-setup/workflow.md:30-75` — the host-detection rungs, the we-control-signal rule, and the canonical per-host spelling statement
- `plugins/flow-next/skills/flow-next-plan/references/next-steps-menu.md:1-25` — a full closer surface to model the clause on
- `plugins/flow-next/scripts/lib/opencode_generate.py:256-259,389-420` — how generated command names become flat

**Optional** (reference as needed):
- `plugins/flow-next/skills/flow-next-work-rolling/references/rolling-scheduler.md:268` — an existing portable-host clause to match in tone and length

### Acceptance
- [ ] Each of the five closer surfaces carries one host-form clause; no closer enumerates hosts as a table (R6, G1)
- [ ] On OpenCode the printed command is the flat `/flow-next-<name>` form; an indeterminate host prints the canonical colon form (R6)
- [ ] Detection uses only the existing ownership-manifest signal; no new probe, no new flowctl surface
- [ ] Every literal the mirror rewrote before is still rewritten after the reword — verified by inspecting the mirror, not by assuming the sed matched (R6)
- [ ] `scripts/sync-codex.sh` run twice with identical results, its guards green, mirror diff committed
- [ ] Validated at the installed OpenCode layout, not only the repo tree
- [ ] `cd plugins/flow-next/tests && python3 -m unittest test_install_opencode test_prompt_text_pinned -q` green

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
