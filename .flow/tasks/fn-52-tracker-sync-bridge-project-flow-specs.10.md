---
satisfies: [R16]
---

## Description

Tracker-key identity & id resolution — the deterministic flowctl id-format work that makes a tracker key a **first-class, resolvable flow handle**: `work wor-17`, `plan wor-17`, `show wor-17`, tasks `wor-17.M`. Implements the **hybrid** model (decided post-review): tracker-first specs are natively keyed by the tracker key; flow-first specs keep `fn-NN` and gain a resolvable tracker-key alias on push; **ids never change** (no rename-on-push — the disruptive path is explicitly ruled out).

**Canonical / alias model (consistent with the existing fn-NN convention):** flow's canonical spec id *includes the slug* (`fn-52-...-flow-specs`), and tasks are `<full-spec-id>.M`. Tracker-first mirrors this exactly: **canonical spec id = `wor-17-slug`**, tasks = **`wor-17-slug.M`**, branch = `wor-17-slug`. The bare forms `wor-17` and `wor-17.M` are **aliases that expand the same way `fn-52` / `fn-52.M` already do** via `expand_bare_spec_id` (bare → full-slug id). So `cmd_task_create`'s `task_id = f"{spec_id}.{N}"` stays correct (spec_id is the slug form); no special task-id construction.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`; tests `plugins/flow-next/tests/test_tracker_id_resolution.py`, `test_tracker_id_generator.py`

## Approach

- **Three grammars (define + test all three):** (a) **alias / bare handle** `^[a-z][a-z0-9]{0,9}-\d+$` (`wor-17`); (b) **canonical spec id** `^[a-z][a-z0-9]{0,9}-\d+-[a-z0-9-]+$` (`wor-17-fix-login`); (c) **task handle** `wor-17.M` (alias) or `wor-17-slug.M` (canonical). `fn-` is reserved for the native scheme **hard** — matched/resolved FIRST, and a tracker identifier whose lowercased key is `fn` (e.g. `FN-17`) is rejected at link/create time so it can never collide with the native scheme. The tracker grammars are tried only on an `fn-` miss.
- **Resolver — widen the SPEC path (candidate-set, NOT first-match short-circuit):** `is_spec_id`, `expand_bare_spec_id`. For a bare `wor-17`: the native `fn` path is reserved + tried first; then **gather ALL candidates from BOTH sources** — specs whose canonical id is `wor-17-*` (tracker-first) AND flow-first specs whose `tracker.identifier` matches (case-insensitive). Disambiguate the candidate set: 0 → not-found; exactly 1 → resolve; >1 with the **same `tracker.id` UUID** → same logical issue, dedupe to one canonical target; >1 with **differing/unknown UUIDs** → **ambiguous error** (never silently pick the canonical and hide an alias — that would be a data-loss footgun). The full-slug canonical (`wor-17-slug`) resolves directly by file lookup like any spec id.
- **Resolver — widen the TASK path (do NOT forget these):** `is_task_id`, `spec_id_from_task`, `scan_max_task_id`, task-path resolution/globs, and task-dep validation. **Task deps stay same-spec** (the existing `cmd_dep_add` invariant is unchanged) — aliasing only means `dep add wor-17.2 wor-17.1` canonicalizes to `wor-17-slug.2`/`.1` within the one spec; cross-spec relationships remain `spec add-dep wor-17 fn-53` (spec-level, which already allows distinct specs). Without these, `start` / `done` / `dep` break even when spec resolution works.
- **Enumeration vs allocation — split the two responsibilities (do NOT conflate):**
  - `iter_spec_json_files` widens to yield **all** spec JSONs (`fn-*` AND `wor-*`), across `.flow/specs/` (+ legacy `.flow/epics/`), so `list` / `specs` / `ready` / `validate` see tracker-key specs. Documented, stable sort for a mixed `fn-*` + `wor-*` set.
  - `scan_max_spec_id` (used by `cmd_spec_create` to allocate the next `fn-N`) stays **native-`fn`-only** — rename to `scan_max_native_fn_spec_id` for clarity. Tracker-key specs are visible to enumeration but **must NOT count toward `fn` allocation** (else a `wor-9999-foo` would push the next flow-first spec to `fn-10000`). Same split for `scan_max_task_id` if it informs `fn` task numbering.
- **Sort / parse helpers (the mixed-format `TypeError` trap):** `parse_id` (`flowctl.py:1745`) hard-matches `^fn-(\d+)…` and returns `(None, None)` for a `wor-*` id; the `spec_sort_key` / `task_sort_key` sites (`:11363`, `:11455`, `:11528`, `:11575`, …) build int tuples from it, so a mixed `fn-*` + `wor-*` list sorts `None` against `int` → `TypeError` / unstable order. Make `parse_id` (or a tracker-aware sort key) return a total-orderable key across both schemes (e.g. `(scheme_rank, key_str, number, task_num)`) and route every list/ready/specs sort path through it. Test a mixed set `fn-2`, `fn-10`, `wor-17-login`, `abc-3-foo` → no `TypeError`, documented stable order.
- **`spec set-title` no-rename for linked specs (`cmd_spec_set_title`, `flowctl.py:11869` — it renames the slug/id/files today):** for any spec that carries a tracker link (canonical `wor-*` id OR a stored `tracker.identifier`), `set-title` updates the title (and body H1) ONLY — it does NOT mutate the canonical id, branch, or filenames (renaming would desync the tracker linkage / branch / back-reference). Unlinked specs keep today's rename behavior. This makes the "ids never change" invariant hold against the one existing command that could break it.
- **Central canonicalizers (widening validators is NOT enough):** many commands path directly to `.flow/{specs,tasks}/<id>.json`, so an alias must canonicalize to the on-disk id BEFORE any file IO / dep compare / status write / receipt. Add `resolve_task_arg(flow_dir, task_id) → canonical` (and the spec equivalent in `expand_bare_spec_id`); every spec/task-taking command calls it first — **including read commands** (`show wor-17.1`, `cat wor-17.1`, `tasks`/`ready`/`validate`), not only the mutating `start`/`done`/`dep` paths. **Aliases are never persisted** — `dep add wor-17.2 wor-17.1` (same-spec) stores the canonical `wor-17-slug.2`/`.1` in `depends_on`, never the `wor-17.x` alias.
- **Case rule:** `tracker.identifier` stores the **display** form (`WOR-17`); the canonical id is derived from the **lowercase** key (`wor-17-slug`); alias resolution is **case-insensitive** (`WOR-17`, `wor-17` both resolve).
- **Generator — origin-branched, with a deterministic CLI surface:** extend `cmd_spec_create` so the link path (.2) can request a tracker-first id, e.g. `flowctl spec create --title "Fix login" --tracker-identifier WOR-17 --tracker-first --json` → canonical id `wor-17-fix-login`, `tracker.identifier=WOR-17`, branch `wor-17-fix-login`. Pin the JSON output shape in acceptance. A flow-authored spec (no `--tracker-first`) keeps the unchanged `fn-NN-slug` sequential generator; on later push it stores `tracker.identifier` as a resolvable alias — NEVER renamed.
- **No-rename invariant:** push / link must never mutate an existing spec/task id, branch, or dep edge. Assert it (rules out the rename-on-push breakage).
- **Collision / ambiguity (define across ALL candidate sources):** a local re-pull of the same issue dedups via the R4 tracker UUID — no second `wor-17`. The dangerous case is a tracker-first canonical `wor-17-slug` spec **and** a separate flow-first spec carrying `tracker.identifier=WOR-17`: gather both, then — same `tracker.id` UUID ⇒ dedupe to one target; distinct/unknown UUIDs ⇒ **ambiguous error**, never silently prefer the canonical. Two flow-first specs sharing an identifier ⇒ same ambiguous error. `fn-` is matched/resolved first; tested for each case.
- **Boundary:** one tracker team / workspace per repo, so a bare `wor-17` is unambiguous; cross-workspace same-key collision is out of scope (stated boundary, not handled).

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py` — `is_spec_id`, `expand_bare_spec_id`, `is_task_id`, `spec_id_from_task`, `scan_max_spec_id`, `scan_max_task_id`, `iter_spec_json_files` (the full validator/parser/enumeration surface to widen)
- `plugins/flow-next/scripts/flowctl.py:11059-11071` — `cmd_spec_create` (id generator + branch default + new `--tracker-first` / `--tracker-identifier` flags)
- the .1 `tracker.identifier` field + sidecar (the alias index source)
- `plugins/flow-next/tests/test_expand_bare_spec_id.py` — existing resolver test to extend

## Acceptance

- [ ] All three grammars defined + tested (alias `wor-17`, canonical `wor-17-slug`, task `wor-17.M` / `wor-17-slug.M`); `fn-` reserved + resolved first [R16]
- [ ] SPEC resolution via the shared canonicalizer (using the REAL command shapes — positional for show/cat, `--spec` for the rest): `flowctl show wor-17`, `flowctl cat wor-17`, `flowctl tasks --spec wor-17`, `flowctl ready --spec wor-17`, `flowctl validate --spec wor-17` all hit the right spec. (Slash-command resolution `/flow-next:plan wor-17` etc. is fn-52.6, not flowctl.) [R16]
- [ ] TASK resolution: `is_task_id`, `spec_id_from_task`, `scan_max_task_id`, task globbing handle `wor-17.M` / `wor-17-slug.M`; `flowctl start|done|dep wor-17.3` work. Task deps stay same-spec (`dep add wor-17.2 wor-17.1`); cross-spec uses `spec add-dep`; both reject/accept as today, just alias-aware [R16]
- [ ] Ambiguity (candidate-set): bare `wor-17` gathers candidates from canonical-prefix + `tracker.identifier` index; same UUID ⇒ dedupe; distinct/unknown UUIDs (incl. a `wor-17-slug` canonical + a flow-first alias, or two flow-first aliases) ⇒ ambiguous error, never silent canonical-preference [R16]
- [ ] Enumeration vs allocation split: `iter_spec_json_files` + `list`/`specs`/`ready`/`validate` see tracker-key JSONs (across `.flow/specs/` + legacy `.flow/epics/`); `scan_max_spec_id` (→ `scan_max_native_fn_spec_id`) counts **`fn-*` only**. Regression test: with `wor-9999-foo.json` present, the next flow-first create still allocates the next `fn-N` from `fn-*` only [R16]
- [ ] Central canonicalizer: `resolve_task_arg` (+ spec equivalent) canonicalizes an alias (`wor-17.1` → `wor-17-slug.1`) BEFORE file IO / dep compare / status write / receipt; every spec/task command calls it; `depends_on` persists canonical ids only (never the alias) [R16]
- [ ] Case rule: `tracker.identifier` stores display `WOR-17`; canonical id is lowercase `wor-17-slug`; alias resolution is case-insensitive [R16]
- [ ] Generator: `flowctl spec create --tracker-first --tracker-identifier WOR-17 --title …` yields canonical id `wor-17-slug` + tasks `wor-17-slug.M` (via the unchanged `task_id = spec_id.N`) + branch `wor-17-slug` + `tracker.identifier=WOR-17`; JSON output shape pinned. Flow-first create (no flag) unchanged `fn-NN-slug` [R16]
- [ ] Mixed-format sort: `parse_id` / sort keys total-order `fn-*` + `wor-*` (test set `fn-2`, `fn-10`, `wor-17-login`, `abc-3-foo` → no `TypeError`, documented stable order) [R16]
- [ ] No-rename invariant: push / link never mutates an existing id / branch / dep edge; `spec set-title` on a tracker-linked spec updates title only (no id/branch/file rename); unlinked specs keep today's rename behavior (regression tests for both) [R16]
- [ ] One-team-per-repo boundary stated; local re-pull of the same issue dedups (no duplicate `wor-17`) [R16]
- [ ] Pytest coverage (`test_tracker_id_resolution.py`, `test_tracker_id_generator.py`) green via the repo runner — covering spec + task + enumeration + mixed-format deps

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
