# fn-101 flowctl determinism audit - findings

Audit executed 2026-07-19 (6-auditor fleet sweep, fn-87 shape, plus inline profiling). Worker-handover surfaces (`anchor`, work-skill worker phases) excluded - owned by a parallel workstream. fn-83's plan-sync skip-gate decision honored (not re-litigated). Open questions resolved as: fleet sweep (not single pass), docs drift folded in, test debt folded in.

## 0. Headline numbers

- flowctl.py = 33,802 lines, 645 functions, 143 `cmd_` handlers, 47 top-level command groups. `main()` alone is 2,481 lines of argparse.
- Review subsystem = ~11.4k LOC (34% of the file), the single biggest family.
- Measured on this repo (100 specs / 403 tasks): `flowctl list --json` = **30.8s wall**, `flowctl status` = **32s**. Root cause profiled: `load_task_with_state` makes 2 uncached `git rev-parse` subprocesses per task (`get_repo_root` L188, `get_state_dir` L838) = 809 subprocess spawns per list. Verified linear: pre-setting `FLOW_STATE_DIR` (kills half the calls) halves wall time to 16.0s. Memoizing both = sub-second (~60x).
- Fixed startup cost ~0.4s per flowctl invocation (interpreter + recompile of the 33.8k-line script; scripts run by path get no bytecode cache). Hot skills make 10-20 invocations per run.
- Dead/vestigial code identified: ~2.7k LOC removable now, plus ~1.4k of pre-1.0 migration machinery eligible at 3.0, plus whole test files that ride along.
- Backend duplication: 9 near-clone review commands (codex/copilot/cursor x impl/plan/completion) = 2,314 LOC, plus ~700 more in supporting triplets; a registry-driven driver saves an estimated 1,800-2,100 LOC. `BACKEND_REGISTRY` (L4020) already exists half-built.

## 1. The kernel: what still earns deterministic Python

Bitter-lesson test applied to every surface: "would this still be needed if the host model were 10x smarter?" Only mechanisms survive, not intelligence substitutes.

**KERNEL (keep, forever-class):**

1. **State store** - spec/task CRUD, id allocation, dep graph, alias resolution, flock claims, atomic writes, schema `validate`. Two concurrent agents racing is physics, not intelligence. (~6-7k LOC, doctrine-clean per audit; zero judgment-leakage verdicts in the CRUD family.)
2. **Evidence layer** - receipts (review/gate/qa/sync/walkthrough), event tags, review-rounds cap counters, checkpoints. This is the product's differentiator: proof-of-work that does not depend on trusting narration. Writing must be deterministic; judging content need not be. (~1.5k)
3. **Backend transport** - subprocess exec of headless CLIs, fallback ladder, model cache, and the contracted `<verdict>` tag parse (a declared grammar, not prose comprehension). Needs to exist ONCE, not nine times. (~1k after dedup)
4. **Tracker-sync state plumbing** - hash-anchored merge bases, paired-snapshot invariant, id collision guards, defer queue, receipts. The 3-way body merge is already agent-side (body-merge.md explicitly forbids a deterministic merge engine) - this family is the doctrine's best example of the split done right. (~0.7k)
5. **Ralph enforcement** - hooks/sentinels/guard, ONLY while Ralph exists (see section 3).

**NOT KERNEL (judgment leakage - evict to skills/prompts):**

| # | Surface | Location | Why it fails the test |
|---|---|---|---|
| 1 | Triage LLM judge (flowctl shells `codex exec --model gpt-5-mini` on ambiguous diffs) | flowctl.py:26991-27138 (~245 LOC) | RECLASSIFIED KEEP (maintainer review 2026-07-19, initial eviction verdict retracted). "Is this diff worth review?" is a review-shaped verdict about code the pipeline just wrote (a skip writes `verdict: SHIP`); host self-issuing it is the self-blessing flow-next bans, and in autonomous loops skip-bias is the expensive failure mode. Cheap (mini @low), sandboxed read-only, 120s timeout, conservative fall-through to REVIEW on any failure, receipted, opt-out flags. Same sanctioned family as review-backend dispatch (fn-29.6 by design). Follow-up: document the carve-out in CLAUDE.md so future audits do not re-flag it (fn-107). |
| 2 | `memory add` overlap auto-routing: 0-4 token/tag overlap score, score>=3 silently UPDATES an existing entry instead of creating | flowctl.py:8522, 8571, 9077-9090 | Scoring math answering "is this the same learning?" and acting on it. Emit `matches`, let the calling skill decide update-vs-create. |
| 3 | Deep-pass pipeline: prose-regex finding parser + fingerprint confidence-promotion + Python recomputing the verdict (conf>=75 flips to NEEDS_WORK) | flowctl.py:22147-22359 | Threshold math substituting for reviewer/host judgment; "are these the same finding?" answered by line-bucket slugs. Fix direction: JSON-lines output contract from backends; host judges promotion interactively; autonomous mode keeps a thin schema check. |
| 4 | Validator prose parser mutating receipt verdicts | flowctl.py:21624, 21692 | Same pattern as #3. |
| 5 | Prose-tally parsers (`parse_suppressed_count`, `parse_classification_counts`, `parse_unaddressed_rids`) | flowctl.py:3734-3849 (~230 LOC) | Markdown-noise-tolerant regex over reviewer prose. Tighten the reviewer output contract to a JSON block; parsers shrink to json.loads + schema. |
| 6 | `scope suggest`: a CLI round-trip wrapping `fire = (1 <= n < 3)` on agent-supplied counts | flowctl.py:13401-13453 | The agent already did the judgment (counting signal categories); the leftover comparison does not earn a subprocess. Fold into capture skill contract. |
| 7 | ralph-guard `flowctl done` success sniffing (word-match "done/updated/completed" in response prose) | ralph-guard.py:733-740 | Text sniffing standing in for an exit-code/JSON signal; enormous false-positive surface, and it GATES the impl-receipt flow. |
| 8 | Review prompt builders: ~780 LOC of f-string prompts embedded in Python | flowctl.py:5133-5421, 5586-5804, 21354-21503, 24724-24877 | Not leakage per se (they feed headless CLIs), but the repo already proves the alternative: validator/deep-pass prompts live in skill .md templates with `load_*_template` + embedded fallback. Move them; prompts become prose the sync script and reviewers can see. |
| 9 | `prime classify` axis verdicts (greenfield vote tally, size thresholds) | flowctl.py:28727-28758 | KEEP-WITH-NOTE, not evicted: raw signals + evidence + confidence caps ride along, thresholds documented as tunable in the skill, low confidence routes to clarification, 189 eval tests pin it. Verdict-shaped but contract-consistent. Re-examine only if the skill starts overriding it routinely. |
| 10 | `memory migrate` legacy prose extraction (heading cascade + banner stoplist + fuzzy strip) | flowctl.py:10011-10095 | Contained: explicitly the deprecated mechanical-only fallback (fn-35), consent-gated, deprecation hint points to the agent-native skill. Leave until the migrate window closes; do not extend. |

**Gray zone, sanctioned:** `spec export-cognitive-aid`'s regex code-analysis helpers and security-filename stoplists (flowctl.py:15083-16038) are deterministic-signal-for-agent-rendering by explicit fn-42 design ("no LLM judgment in the export step"). Keep, but see the dead-flag removals below.

## 2. DEAD / VESTIGIAL surfaces (~2.7k LOC now, ~1.4k more at 3.0)

Zero fleet callers verified per item (skills/agents/hooks/templates greps, codex mirror excluded; docs mentions do not count). Risk note per item.

| Surface | LOC | Risk of removal |
|---|---|---|
| `epic`/`epics` command aliases + `--epic*` flags + R31 dual-emit JSON keys (`specs`+`epics`, `spec`+`epic`, `epic_count`, `epic_blocked_by`, `legacy_reason`) threaded through every hot read payload | ~300 + payload bloat | Help text has promised "removed in 2.0" since 2.0; we are at 2.18. Out-of-repo consumers (flow-swarm reads `.flow/specs/` natively) should be checked for alias-key reads before dropping dual-emit. Obsoletes `alias_smoke.sh` + `test_read_compat.py`. |
| `rp windows / pick-window / ensure-workspace / builder` + `prep-chat` (superseded by atomic `rp setup-review` / `rp chat-send`) | ~195 + parsers | Docs already say "do not call individually". prep-chat has zero tests; removal free. |
| `memory discoverability-patch` (fn-30.6 relic; audit skill does this via Edit now) | ~357 | Zero callers, zero tests. |
| `task show-backend` (provenance display) + `codex/copilot/cursor check` probes (smoke-test-only) | ~460 | Human-debug value only; keep `check` if uninstall/troubleshooting docs direct users to it - verify first. |
| `task set-deps` (third copy of dep-add logic) | ~80 | Test fallout in test_tracker_id_resolution.py. |
| rp `setup-review` pick-window state file: writer with zero readers; docstring claims a ralph-guard verification that does not exist | ~5 + stale docstring | None. Also delete the ci_test.sh:716 cleanup line. |
| Empty config-alias machinery: `_CONFIG_KEY_ALIASES = {}` ("empty since 2.0.0") + two resolvers + a third inline duplicate in `cmd_config_get --raw`; also causes a triple config.json parse per read | ~110 + 19 no-op tests | Keep a one-line resolver seam if future renames are expected; delete the rest. |
| `sync clear-dep-relation`, `strategy list`, `repo-map show`, `repo-map since-ref`, `prospect list`, `prospect read`, `pilot-log summary`, `checkpoint delete`, `state-path` | ~870 | All API-symmetry or human-CLI surfaces. KEEP `pilot-log summary` if the fn-102 post-land measurement plan will consume it (it is the designed readout); decide there first. |
| ralph-guard debug log (unconditional `/tmp` append on EVERY hook fire, even with FLOW_RALPH unset - contradicts documented "zero overhead"), `RALPH_GUARD_VERSION` no-op constant, `ralph_e2e_test.sh` (unreferenced) | ~200 | Env-gate the log (`RALPH_GUARD_DEBUG=1`) rather than delete. |
| Always-empty `review_receipts` export field + dead `--section` export filter | ~60 | make-pr already documents the workaround; qa forbids the flag. |
| `migrate-rename` + `migrate-rollback` + banner hook (~1.39k) + `migrate-state` (~70) | ~1.46k | Textbook-quality code, but it migrates pre-1.0.0 (2026-05-09) layouts. Maintainer decision 2026-07-19: remove NOW (was initially basketed for 3.0), replaced by a short usage.md porting prose entry - an agent can do the rename-and-validate port from three sentences. Orphans test_migrate_rename.py (24 tests), test_banner.py (26), test_lockfile.py (12), legacy-epics clauses in capture/make-pr prose. Scoped into fn-105. |

## 3. Ralph separation

Ralph's actual footprint inside flowctl core is small: `ralph pause/resume/stop/status` sentinel commands (~90 LOC), `find_active_runs` progress.txt parsing in `status` (~90), RALPH_ITERATION receipt stamping duplicated 10x across review commands (~60). The heavy parts already live outside: ralph-guard.py (971) is its own file, the scaffold (ralph.sh 1361 + templates ~550) lives in the ralph-init skill, smoke/e2e = ~1.4k of shell.

So a code split buys only ~400 LOC of core shrink. The REAL cost Ralph imposes is the **extension tax**: every review-subsystem change must consider guard patterns, receipt-ordering gates, and ralph template parity. And the audit found the behavioral-enforcement half of the guard is already partially theater:

- Receipt-write ordering is enforced for Bash only; the Write tool bypasses it entirely (Stop-hook content validation is the actual backstop).
- hooks.json matches `Bash|Execute` (Droid) but the guard body drops anything not named `Bash` - the two files contradict each other; command checks are silently inert on Droid.
- `flowctl done` detection = word-sniffing response prose (section 1 #7).
- The one excellent piece is the fn-55 codex-delegation allowlist - a security control, not behavior babysitting.

That pattern IS the bitter lesson in miniature: hook-enforcement of agent behavior is a losing arms race that model improvement obsoletes, while the receipt/evidence layer (which does not care how smart the agent is) keeps working. STRATEGY.md already demoted Ralph to "the hardened harness for runs that outlast a session"; pilot+land is the default path and needs none of the guard machinery because the host session reads verdicts itself.

**Recommendation (decision for maintainer):**

- **Now (cheap):** dedupe the 10x iteration stamping into one helper; fix the guard's three real defects (done-sniffing -> structured signal, Droid Execute mismatch -> accept both or drop the claim, debug log -> env-gated); move `find_active_runs`'s progress parsing onto the existing `promise=COMPLETE` key=value contract instead of prose regex.
- **Boundary (this cycle):** declare Ralph feature-frozen (maintenance mode) in CLAUDE.md + ralph.md: new pipeline features (new backends, new receipt kinds) are NOT required to thread through guard patterns/templates unless Ralph-relevant. Cuts the extension tax immediately without breaking anyone.
- **3.0 option:** extract Ralph to its own installable module (guard + sentinel commands + templates as a `flow-ralph` add-on consuming flowctl as plumbing), or sunset it if host-native loop primitives (/loop + background agents on Claude Code; equivalents on Droid) cover the outlast-a-session case by then. Do not decide now; revisit with usage data.

## 4. Speed program (measured, ranked by wall-clock per pipeline run)

1. **Memoize `get_repo_root()` + `get_state_dir()`** (one `functools.lru_cache` each, env-override aware). list/status: 30s -> <1s at 400 tasks. Affects status/show/specs/tasks/list/ready/next/spec-close - and pilot/ralph run these every tick. The single highest-leverage change in the repo.
2. **Multi-key config read** (`flowctl config get land --json` returning the subtree, or `--keys a,b,c`). land Phase 0 = 7 sequential flowctl startups -> 1; plan = ~8 scattered reads -> 1-2; pilot = 3 -> 1.
3. **Write-path flags**: `spec create --branch` (kills the immediate set-branch follow-up), `task create --description-file/--acceptance-file` (kills 2N follow-up calls per plan, N typically 3-6).
4. **Review handlers self-write status**: `<backend> plan-review` knows the verdict; have it set `plan_review_status` (and reset review-rounds on SHIP) instead of 1-2 follow-up calls per round.
5. **Skill-prose round-trip diet**: make-pr Phase 0 has a validation-only `show >/dev/null` (output discarded) + 8 read-only fences collapsible to 2-3; pilot Phase 4 re-runs Phase 1's exact reads in a fresh shell (workflow.md:390-396 vs 142-149); plan-review duplicates its full per-backend block in SKILL.md AND workflow.md (3 backends x 2 copies - token load + drift risk); impl-review fragments arg parsing into 3 fences.
6. **Batch the export's git grep fan-out**: up to 40 sequential `git grep` per cognitive-aid export -> one `--or` invocation.
7. Minor: memoize `get_cursor_version`/`get_copilot_version` per process; prospect artifacts parsed 3x per item (fold to one read); `pilot-log append` O(n) tick derivation -> counter file; `cmd_tasks` double `get_flow_dir()`.
8. Startup (~0.4s/invocation) becomes tolerable once invocation COUNT drops per items 2-5; a zipapp/pyc distribution is possible later but is churn we do not need yet.

## 5. Extensibility program

1. **Backend registry driver**: extend `BACKEND_REGISTRY` (L4020, half-built) with `run_exec`/`resolve_spec`/`check_probe`/prompt-fit hooks; one `cmd_backend_review(backend, kind)` replaces the 9 clones (2,314 LOC -> ~500 of hooks keeping genuine variance: cursor argv budget, copilot session marker, codex sandbox). Adding backend #4 becomes a registry entry, not a 4th copy of everything. Start with the byte-identical git-diff gathering block (L24195/25216/25923/26403).
2. **Prompts to templates** (section 1 #8): review prompts move to skill .md templates with the existing loader+fallback pattern.
3. **Reviewer output contract**: JSON block instead of prose tallies (kills ~560 LOC of tolerant regex).
4. Near-clone field setters (`set-plan-review-status`/`set-completion-review-status`), triplicated dep-blocked loop (ready/ready-all/next), 8x error-emit boilerplate in scope commands, 3x dep-validation logic: extract helpers opportunistically when touching those files.
5. Single-file constraint: keep it (zero-dep curl-able distribution is load-bearing); IF the file keeps growing past this audit's cuts, an amalgamation build (package in-repo, concatenated artifact shipped) is the escape hatch - not now.

## 6. Docs drift (11 items, from the drift auditor)

flowctl.md: `setup-block` and `scope` groups entirely undocumented; `strategy` listed but sectionless; `pilot-log`/`review-rounds` sections missing from the Available Commands block; `spec skeleton`, `codex classify-result`, `codex rollback-plan`, `rp ensure-workspace` undocumented; `done` inline `--summary/--evidence` flags undocumented; File Structure tree stale (missing config.json/templates/artifacts/review-receipts; "memory (reserved)" is false). architecture.md layout omits bin/, usage.md, templates/, artifacts/, review-receipts/ and runtime dirs. ralph.md/flowctl.md: `state.json` claim is wrong (PAUSE/STOP sentinels + progress.txt); "zero overhead for non-Ralph users" contradicted by the unconditional debug log; guard-rules table omits the guard's biggest features.

## 7. Test debt riding along

Removals obsolete: `alias_smoke.sh` (whole file), `test_config_alias.py` (19 no-op-path tests), `test_read_compat.py`, set-deps cases in `test_tracker_id_resolution.py`, show-backend lines in `smoke_test.sh`, fire/no-fire scope-suggest cases in `test_r22_invariant.py`/`test_capture_biz_routing.py`. Coverage gaps found: `cmd_memory_migrate` extraction helpers untested; glossary/strategy have no dedicated test files. Keep-side anchors: test_r22_invariant (skeleton), test_spec_ready, test_export_traceability, test_pilot_backlog_substrate, test_prime_eval (189), test_backend_spec (140).

## 8. Follow-up specs (created as stubs alongside this audit)

1. flowctl hot-path perf: memoize repo-root/state-dir + misc caches + batched git grep (section 4: 1, 6, 7)
2. flowctl round-trip diet: multi-key config get, write-path flags, self-writing review handlers, skill-prose fence consolidation (section 4: 2-5)
3. dead-surface removal sweep + docs drift corrections (sections 2 + 6, INCLUDING pre-1.0 migrations + epic aliases per maintainer decision 2026-07-19; usage.md porting prose replaces the migration code)
4. review backend registry: dedupe the 9 clones, prompts to templates, JSON reviewer-output contract (section 5: 1-3; section 1: 3-5, 8)
5. judgment evictions: triage LLM judge, memory-add overlap auto-update, scope suggest (section 1: 1, 2, 6)
6. ralph boundary: guard defect fixes + iteration-stamp dedupe + feature-freeze declaration (section 3 "now" + "boundary")

Remaining 3.0-deferred item: only the Ralph extract-or-sunset decision (section 3). Migrations + aliases moved into fn-105 per maintainer decision 2026-07-19. Droid hook facts re-verified 2026-07-19 (Factory hooks reference): shell tool is still `Execute` (no `Bash`), file tools are `Edit`/`Create`/`ApplyPatch` (no `Write`) - the dual matcher stays needed and the guard body must honor it (fn-108). Hooks inventory confirmed: ralph-guard is the plugin's ONLY hook (all four events); flow-next has zero non-Ralph hooks.
