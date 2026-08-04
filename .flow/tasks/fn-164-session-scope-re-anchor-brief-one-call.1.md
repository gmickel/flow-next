---
satisfies: [R1, R2, R3, R5]
---
# fn-164-session-scope-re-anchor-brief-one-call.1 flowctl brief: budgeted deterministic session verb + fixture suite

## Description
Implement `flowctl brief`: a pure-read, token-bounded, deterministic session-orientation verb with `--json` and `--full` forms, plus its full fixture test suite.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py` (new cmd_brief + parser registration near the anchor subcommand, ~:46992 subcommand list), `plugins/flow-next/tests/test_brief.py` (new)

### Approach
- Sections in fixed order: header (counts), open specs (id/title/status/ready/one-line goal; closed/done/superseded excluded), actionable tasks, recent completions (last 5 done: id + first `## Done summary` line via `get_task_section` + evidence flag), memory index (entry_id + title, active only), pointers.
- **Actionable-task derivation:** readiness = the canonical `cmd_ready` semantics (task-dep gates AND parent-spec dependency gates), reused/extracted over ONE global `TaskInventory` load — NOT `cmd_list` status alone. Claim state renders runtime `assignee`/`claimed_at`/`claim_note`. Closed-parent orphan tasks still appear.
- **Evidence predicate:** true iff done-evidence dict has any non-empty list among commits/tests/prs; default-empty dict and legacy no-dict tasks → false.
- Extraction rules (deterministic): goal = first non-empty non-heading non-comment line after `## Goal & Context`, 120-char cap; titles capped 80; summary lines capped 120 (ellipsis); memory one-liner = frontmatter title; completion order = task `updated_at` ascending, id-sort tie-break.
- **Budget:** selection computed ONCE on a canonical dataset, trimmed until BOTH renders (md + JSON) fit 8000 chars (measure the larger). Tiers in order: oldest completions → memory lines → spec goal lines → whole actionable-task rows (keep count line) → whole open-spec rows (keep count line). Tiers 4-5 + bounded scalars make the ceiling unconditional (O(1) floor). One `[truncated: ... — use --full]` marker per dropped tier; aggregate counts always survive. `--full` lifts on both forms; `--json` adds per-section `truncated` flags; identical retained ids/omissions across forms.
- **Tolerant collectors, not naive cmd_* capture** (`cmd_specs`/`cmd_list` raise on one malformed JSON; memory listing silently drops malformed entries): per-file spec loading; `TaskInventory.load(..., collect_load_errors=True)` or equivalent; memory scan retaining malformed paths. Unreadable items → `[unreadable: <path>]` lines at the END of their section — paths repo-relative and 120-char middle-ellipsis capped; these lines are canonical dataset items participating in truncation (tier 6: drop excess to an aggregate `[N unreadable files — use --full]` count). Header root paths capped at 120 too. Empty `.flow/` → "(none)" sections, exit 0. NO git invocations anywhere in brief.
- Tests: pinned populated fixture + pinned empty fixture; 20/50/30 budget fixture AND a pathological fixture whose mandatory rows alone exceed 8000 chars (long titles, 100+ rows); determinism (run twice, byte-identical); md/JSON parity (identical retained ids, both <= 8000); readiness fixture (blocked todo task NOT listed ready; spec-dep-gated task NOT ready); evidence fixtures (default-empty → false, populated → true); one corrupt file of each type (spec json, task json, memory entry) alongside readable siblings; many-corrupt-files/long-root-path fixture stays <= 8000 on both forms with the aggregate unreadable-count line; no-writes assertion (hash `.flow/` tree before/after all three forms).

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py:34260-34500` — anchor's capture pattern, section shape, parser registration
- `plugins/flow-next/scripts/flowctl.py:28563-28720` — cmd_specs/cmd_tasks/cmd_list + TaskInventory (note: no readiness calc here)
- `cmd_ready` implementation in flowctl.py — the readiness semantics to reuse/extract (task-dep + spec-dep gates)
- `plugins/flow-next/tests/test_anchor_bundle.py` — module-load fixture, TemporaryDirectory setup, determinism test shape

**Optional**:
- `plugins/flow-next/scripts/flowctl.py:8386-8500` — fit_cursor_*_to_budget char-budget + marker precedent
- `plugins/flow-next/scripts/flowctl.py:22262+` — cmd_memory_list fields

### Key context
- Do NOT touch task-scope anchor or its superset test — brief is a separate verb precisely so anchor's no-truncation contract stays intact.
- Drive tests through production CLI dispatch (memory: test-production-path-not-parallel-construction).
- fn-166 extracts flowctl.py ~:9300-11500 — no collision; rebase anchors if it lands first.

### Acceptance
- [ ] `flowctl brief` renders all six sections in pinned order; populated + empty fixtures pinned (R1)
- [ ] 20/50/30 fixture AND pathological mandatory-rows-overflow fixture both <= 8000 chars on both forms; deterministic markers; two runs byte-identical (R2)
- [ ] md/JSON parity: identical retained ids + omissions; `--full` lifts budget on both forms (R3)
- [ ] Readiness matches cmd_ready semantics (blocked/spec-gated tasks excluded from ready); claim fields rendered; orphan rule holds (R1)
- [ ] Evidence flag: default-empty dict → false, populated → true; legacy no-dict → false (R1)
- [ ] One corrupt spec/task/memory file each degrades to `[unreadable: ...]` in-section; siblings unaffected (R1)
- [ ] `.flow/` tree hash-identical before/after brief/--json/--full (R5)
- [ ] Unreadable file degrades to inline note; no git subprocess spawned (asserted or code-inspected)
- [ ] Focused suite green: `python3 -m unittest test_brief test_anchor_bundle -q`
## Acceptance
- One-call brief with pinned content/section order for populated and empty repos; fail-open on unparseable files (R1)
- 8000-char default budget holds on the 20/50/30 fixture; truncation deterministic and marked (R2)
- --json/--full parity (R3)
- No-writes assertion passes for all three forms (R5)
- Task-scope anchor and its superset test untouched
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
