---
satisfies: [R6]
---
# fn-205-issue-sweep-skipped-review-status-land.5 Closers print the host's invocable command form, with the mirror transform kept in step

## Description
Every closer that prints a copy-pasteable flow-next command must print a form the current host can actually invoke — flat `/flow-next-<name>` on OpenCode (R6). The verified inventory (2026-08-27) is wider than first planned: the sixteen literals across the original five files (all Codex-rewritten today), PLUS six more closer surfaces whose literals the Codex transform never covered — meaning those are already wrong on Codex too, and this task closes both hosts at once. Transform anchors and guard coverage move in the same change. Depends on the work-skill task: `phases.md` is shared.

**Size:** L
**Files:** `plugins/flow-next/skills/flow-next-capture/workflow.md`, `plugins/flow-next/skills/flow-next-capture/references/rewrite-mode.md`, `plugins/flow-next/skills/flow-next-capture/references/split-proposal.md`, `plugins/flow-next/skills/flow-next-plan/references/next-steps-menu.md`, `plugins/flow-next/skills/flow-next-work/phases.md`, `plugins/flow-next/skills/flow-next-make-pr/create-and-finalize.md`, `plugins/flow-next/skills/flow-next-interview/SKILL.md`, `plugins/flow-next/skills/flow-next-interview/references/write-back.md`, `plugins/flow-next/skills/flow-next-prospect/workflow.md`, `plugins/flow-next/skills/flow-next-chart/references/briefing-and-reopen.md`, `plugins/flow-next/skills/flow-next-chart/references/chart-mode.md`, `plugins/flow-next/skills/flow-next-audit/SKILL.md`, `plugins/flow-next/skills/flow-next-audit/workflow.md`, `plugins/flow-next/skills/flow-next-guide/SKILL.md`, `scripts/sync-codex.sh`
**Touches:** [plugins/flow-next/skills/flow-next-capture/**, plugins/flow-next/skills/flow-next-plan/references/next-steps-menu.md, plugins/flow-next/skills/flow-next-work/phases.md, plugins/flow-next/skills/flow-next-make-pr/create-and-finalize.md, plugins/flow-next/skills/flow-next-interview/**, plugins/flow-next/skills/flow-next-prospect/workflow.md, plugins/flow-next/skills/flow-next-chart/references/**, plugins/flow-next/skills/flow-next-audit/**, plugins/flow-next/skills/flow-next-guide/SKILL.md, scripts/sync-codex.sh, plugins/flow-next/codex/**]

### Approach
- Closer surfaces and their literals, verified 2026-08-27. Already Codex-rewritten (anchors must move with any reword): `capture/workflow.md:664,667-669` (base footer, 4), `capture/references/rewrite-mode.md:91,94-97` (5), `capture/references/split-proposal.md:79` (1), `plan/references/next-steps-menu.md:11,20-22` (4), `work/phases.md:576` (2, via the one-off sed at `sync-codex.sh:538`). NOT Codex-covered today (already broken there; bring under the transform in this task): `make-pr/create-and-finalize.md:419-420,543,550-551` (success footer + stderr line, 5), `interview/SKILL.md:446-450` (suggest-next, 7) + `interview/references/write-back.md:154,165,217,244`, `prospect/workflow.md:764,810,825-826`, `chart/references/briefing-and-reopen.md:45` + `chart/references/chart-mode.md:78,162`, `audit/SKILL.md:81,121` + `audit/workflow.md:73,538`, `guide/SKILL.md:43-53` (routing-matrix route column — one clause covers the whole matrix). `rolling-scheduler.md:300` is already handled at `sync-codex.sh:439-440`; pilot/land command mentions are agent-internal dispatch, not closers — leave them.
- State the invariant, not a host matrix: one short clause per closer surface saying the printed command uses the form this host invokes, with OpenCode's flat spelling as the named case and the colon form as the canonical default when the host is indeterminate. Keep the canonical literals in colon form so the existing mirror transform still has something to rewrite. A per-host enumeration table in every closer is the rejected shape (spec Decision Context) — it races the next host and inflates every dispatch.
- Use the shipped signal only: the installer's ownership manifest at `${PLUGIN_ROOT}/.flow-next-opencode-manifest`, already the detection rung in `flow-next-setup/workflow.md:37-38,62`. Do not invent a probe, and do not add a flowctl command for this.
- The silent-failure risk is the mirror: `scripts/sync-codex.sh:389-427` rewrites an enumerated four-file list with 16 anchored per-pattern seds (`:401-405` file loop, `:408-423` patterns), `phases.md` gets its one-off at `:538`, and the hard-fail guard (block `:2169-2181`, grep at `:2174`) only checks the `Recommended next: /flow-next:` shape. Any reworded literal whose anchor stops matching leaves the mirror on the colon form at exit 0. Update the anchors with the prose, extend the transform to the newly covered files (a generic anchored pass over their `/flow-next:` invocation literals beats 20 new one-off seds — but keep it anchored, not blanket), and extend the guard as anchored per-file expected-output checks: for every file in the transform roster, assert its actionable literals appear in the mirror ONLY in rewritten form. Never a semantic whole-mirror grep for "copy-pasteable" — the mirror carries `/flow-next:` passive mentions across ~90 files that must stay untouched, and the sync script itself warns against blanket matching (review-confirmed). New files enter coverage by joining the roster; future closers are caught at review time by the conduct checklist, not by a guess-the-grammar grep. A guard failure is load-bearing: fix the content or extend the transform, never relax the guard.
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
- [ ] Every inventoried closer surface (the original five files plus make-pr, interview, prospect, chart, audit, guide) carries one host-form clause per file; no closer enumerates hosts as a table (R6, G1)
- [ ] On OpenCode the printed command is the flat `/flow-next-<name>` form; an indeterminate host prints the canonical colon form (R6)
- [ ] Detection uses only the existing ownership-manifest signal; no new probe, no new flowctl surface
- [ ] Every literal the mirror rewrote before is still rewritten after the reword, and the newly inventoried surfaces' invocation literals are now rewritten too — verified by inspecting the mirror, not by assuming the sed matched (R6)
- [ ] The sync guard covers every roster file with anchored expected-output checks (un-rewritten actionable literal in a roster file fails the sync); passive `/flow-next:` mentions elsewhere in the mirror remain untouched and unflagged
- [ ] `scripts/sync-codex.sh` run twice with identical results, its guards green, mirror diff committed
- [ ] Validated at the installed OpenCode layout, not only the repo tree
- [ ] `cd plugins/flow-next/tests && python3 -m unittest test_install_opencode test_prompt_text_pinned -q` green

## Acceptance
- [ ] TBD

## Done summary
Every inventoried closer surface (capture workflow/rewrite-mode/split-proposal, plan next-steps menu, work ship footer, make-pr success footer, interview SKILL + write-back, prospect, chart briefing/chart-mode, audit SKILL + workflow, guide routing matrix - 14 files) now carries one host-command-form clause: OpenCode installs (plugin root carries `.flow-next-opencode-manifest`, the existing setup detection signal - no new probe, no flowctl surface) print the flat `/flow-next-<name>` form; any other or indeterminate host prints the command exactly as spelled, which keeps the canonical colon literals for the mirror transform and keeps the clause double-transform-safe on Codex (R6). sync-codex.sh's actionable next-step transform roster widened 4 -> 13 files with anchored per-surface seds, and a new closer-roster hard-fail guard asserts every inventoried literal appears in the mirror only in rewritten `$flow-next-` form (fixed-string, per-file, tab-delimited roster; passive `/flow-next:` mentions unflagged; guard proven load-bearing - removing one sed pattern fails the sync rc=1). Mirror regenerated, sync run twice byte-idempotent; validated at the installed OpenCode layout (flat command stubs, manifest two levels above SKILL.md, clause present in installed skills).

baseline: green (handoff, verified at bcaf2ce5 by fn-205-issue-sweep-skipped-review-status-land.2)

stage: impl-review - skipped(policy: host-deferred + parallel-wave - conductor owns the gate after integration)

Deliberate exclusions (documented in the transform comment): prospect workflow.md's `**Next step:** /flow-next:interview` line documents what flowctl's `write_prospect_artifact` emits verbatim on every host - rewriting the doc would mis-describe the artifact; presentation is governed by the file's host-form clause. make-pr recovery-hint lines (:339,:386,:388) and chart-mode's shape-A `/flow-next:prospect` offer (:69) were not in the task's verified inventory - error-path hints, flagged as possible follow-up. guide + chart clause copies use plain hyphens (em-dash pins in test_guide_routing / test_chart_skill_contract); the other 11 files carry the em-dash form.

Implementation bridged to grok 4.6 via cursor-agent per explicit routing (1 chunk: the 14 clause insertions - usable on first attempt, zero repairs); sync-codex.sh transform/guard surgery and mirror regen taken by the host per the task's stated exception.

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 20c0e8be4f795d0a68e1a64d729c3ce036615fe9
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_install_opencode test_prompt_text_pinned -q, cd plugins/flow-next/tests && python3 -m unittest test_guide_routing test_skill_prose_diet test_chart_skill_contract test_chart_docs_inventory test_interview_scope_flag test_interview_source_tags test_make_pr_reached_path test_pr_cognitive_aid test_host_review_backend test_readback_ask_contract test_spec_id_routing_prose -q, python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh (run 2x, byte-idempotent via sorted sha256; closer-roster guard proven to bite: removing one sed pattern fails sync rc=1), bash scripts/install-opencode.sh --dest <tmp> (installed-layout validation: flat command stubs, manifest at config root, clause present in installed skills)
- PRs: