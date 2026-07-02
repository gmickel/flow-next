---
satisfies: [R3, R6, R7]
---

## Description

Class-3 non-eval dedupe: single Phase 0 for the two review skills (kills the double `review-backend` call), interview cascade + aux-section dedupe, audit Replace-flow dedupe + line-ref archaeology, prospect python-picker dedupe + stale scaffolding. CANONICAL FILES ONLY.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-impl-review/SKILL.md`, `plugins/flow-next/skills/flow-next-spec-completion-review/SKILL.md`, `plugins/flow-next/skills/flow-next-interview/SKILL.md`, `plugins/flow-next/skills/flow-next-plan/steps.md` (cascade cross-ref repoint only), `plugins/flow-next/skills/flow-next-audit/{workflow.md,phases.md}`, `plugins/flow-next/skills/flow-next-prospect/workflow.md`

## Approach

- **Dedupe rule (binding):** merge explanatory blocks to ONE site verbatim; KEEP short imperative rules repeated at action sites. Never paraphrase the surviving copy.
- impl-review: SKILL.md:29-40 (RP_ELIGIBLE) + :71+ (`review-backend` + ASK branches) duplicate workflow-common.md:9-91. SKILL.md keeps: intent, arg parsing, "Backend at a glance", critical rules; delegates the executable Phase 0 (eligibility probe + review-backend call + ASK handling) to workflow-common with an imperative pointer. Result: exactly one `flowctl review-backend` invocation per run. spec-completion-review: same fix against its workflow-common.md:13-51. NOTE fn-81 edited both SKILL.md files — re-locate blocks by content, not stale lines.
- interview: the template header comment (`plugins/flow-next/templates/spec.md:44-52`) describes only the 4-tier ORDER — it lacks the walker's load-bearing mechanics. FIRST move the full walker VERBATIM (case-insensitive-FS probe/HITS logic, both-exist warning preferring SPEC.md, `${CLAUDE_PLUGIN_ROOT:-…}` plugin-root fallback) into the single shared location (either expand the template header comment or a small shared reference linked one level deep), THEN replace the inline copy with a 2-3 line cross-link; repoint plan steps.md:268 to the same source. APFS/Windows behavior + plugin-root fallback preserved byte-for-byte. Aux-section block: SKILL.md:377 ≡ :394 (+ restatements :403,:428) → define once ("append the same auxiliary sections as the new-idea branch"), keeping any short imperative at each action site.
- audit: Replace/supersede/mark-stale flows — phases.md (`## Replace` :135 + outcome/calibration tables) is authoritative; workflow.md's duplicate step lists (~:303-349 region; relocate by content) become "execute per phases.md §Replace" delegation. Also strip flowctl.py line refs (phases.md:172, workflow.md:561 → constant names).
- prospect: python-picker at workflow.md:67,:503,:762 → define once near the preamble ("resolve $PY per Phase 0; re-declare per block if needed — vars die across tool calls"), phases reference it; drop the stale stdout snapshot dump + "lands later" prose (:357 region, :180, :203) — snapshot flows into the Phase 2 prompt directly.

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-impl-review/SKILL.md:20-110` + `workflow-common.md:1-95`
- `plugins/flow-next/skills/flow-next-spec-completion-review/SKILL.md:20-100` + `workflow-common.md:1-60`
- `plugins/flow-next/skills/flow-next-interview/SKILL.md:370-440,620-690`
- `plugins/flow-next/skills/flow-next-audit/phases.md:1-90,130-190,240-280` + `workflow.md:290-360,550-610`
- `plugins/flow-next/skills/flow-next-prospect/workflow.md:60-80,170-210,350-380,495-510,755-770`

## Key context

python-picker caution: the 3× repetition may be partially load-bearing (path-persistence — vars die across tool calls). If Phases 2/5 run in separate bash calls from Phase 0, $PY does NOT survive; keep a one-line re-resolve per block (`PY=$(resolve per Phase 0 block)` shape) rather than assuming a single definition carries. State this explicitly in the edited prose.

## Acceptance

- [ ] One `flowctl review-backend` call per impl-review / completion-review run (trace both flows); SKILL.md files keep intent + at-a-glance only
- [ ] Interview cascade single-sourced with the FULL walker mechanics preserved verbatim (case-insensitive FS, both-exist warning, plugin-root fallback); plan steps.md repointed; aux block defined once
- [ ] Audit Replace flows single-sourced in phases.md; no flowctl.py line refs
- [ ] Prospect picker defined once with explicit per-block re-resolve note; stale scaffolding gone
- [ ] Canonical-only diff; smoke green locally

## Done summary
Class-3 dedupe: impl-review + spec-completion-review now delegate executable Phase 0 to workflow-common.md (one flowctl review-backend call per run); interview template-discovery walker single-sourced verbatim in new references/spec-template-discovery.md with plan steps.md + docs/spec-template.md repointed and the auxiliary-sections rule defined once; audit Replace/supersede/mark-stale flows delegate to phases.md; prospect python-picker defined once in the Preamble with explicit per-block re-resolve notes; stale task-N scaffolding and all flowctl.py absolute line refs stripped from canonical skill markdown. Canonical-only (-135 net lines); mirror regen rides fn-82.5.
## Evidence
- Commits: 1d668d3586d7053873ef0556fb5fc97194f5dbaa
- Tests: bash plugins/flow-next/scripts/smoke_test.sh (from mktemp cwd) — 138/138 pass, /usr/bin/python3 -m unittest discover -s plugins/flow-next/tests — 1395 tests, same 4 pre-existing stale-mirror parity failures as pre-change baseline (mirror regen deferred to fn-82.5), RP impl-review SHIP (first pass, 0 findings; --base 3fcdd367)
- PRs: