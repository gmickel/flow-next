# Frozen test inputs — prospect suite (2 candidate batches, FROZEN, synthetic — scrubbed)

The evaluable judgment is prospect's **Phase 3 Critique**: given a grounding snapshot + candidate list, emit
per candidate `{verdict: keep|drop, taxonomy: null|<slug>, reason}` using the FIXED 7-slug taxonomy. The
critique is blind to the personas and the Phase-2 generation framing (anti-sycophancy); per workflow §1.3 the
snapshot's `focus_hint:` line DOES carry into the critique, so it is present here.

**Facts-not-conclusions (fn-84.5 lesson):** the grounding snapshot states raw repo FACTS (open specs,
changelog lines, strategy tracks, memory titles, neutral pain-facts) — it NEVER says "candidate X duplicates
Y" or "X is out of scope." EVERY keep AND every drop must be derivable by connecting a candidate to a snapshot
fact — including the keeps (each has a grounding pain-fact; a candidate with no snapshot support is a legit
`insufficient-signal` drop, so keeps must be genuinely grounded). Run = EMISSION at **sonnet**. Synthetic; no real PII.

Taxonomy (ONLY legal `drop` slugs): `duplicates-open-epic | out-of-scope | out-of-scope-vs-strategy |
insufficient-signal | too-large | backward-incompat | other`. Answer keys are for SCORING only — NOT shown to
the run. Where the prose admits >1 slug the key lists an accept-set. The **rejection-floor check is
HARNESS-COMPUTED** from the emitted verdicts (the critique emits YAML only; it does NOT self-report the floor).

---

## Batch C1 — mixed critique (classification + taxonomy precision). 9 candidates.

**Grounding snapshot (raw FACTS — canonical §1.3 block labels, no verdict language):**

```
## Grounding snapshot
focus_hint: flow-next plugin improvements
focus_kind: repo-wide
git_log_30d: 2.6.3 ready-gate fix; fn-52 tracker-sync bridge (Linear+GitHub); fn-69 GitLab adapter; fn-74 cursor review backend
open_specs:
  - fn-70-jira-tracker-adapter — add a Jira adapter to the tracker-sync bridge (REST transport, ADF body)
  - fn-83-work-loop-speed — plan-sync shadow gate + worker anchor bundle
changelog_recent: 2.6.3 ready --spec honors spec-level depends_on_epics; 2.6.2 external ready-gate fix
memory_matches:
  - windows python3 -> MS Store 9009 stub breaks flowctl; no CI job currently exercises the Windows python3 path
  - dual-copy invariant scripts<->.flow/bin flowctl.py
  - linear api key in keychain (used by tracker-sync graphql rung)
  - prospect artifacts accumulate under .flow/prospects/ (14 files, oldest 92d); no prune/retention command exists
  - prospect Phase-1 re-scans git log + open specs + memory on EVERY run; 3 runs in one day re-shelled the same git log 3x
memory_audit_stale: scanned: none (no audit run)
strategy:
  name: flow-next
  target_problem: AI-assisted SDLC drift — specs and implementation diverge
  approach: spec-driven, skill-first; the host agent is the intelligence
  tracks:
    ### Zero-dependency core
    flowctl stays pure-stdlib Python — no pip installs, no runtime deps; jq/gh are the only external tools.
    ### Cross-platform parity
    first-class on Claude Code / Codex / Factory Droid; canonical files Claude-native, sync-codex.sh mirrors.
    ### Autonomous Ralph mode
    overnight spec-to-PR loops; conflicts never block, they queue.
```

(Distractor facts tied to no candidate: the `linear api key in keychain` memory, the `2.6.2 external ready-gate` changelog, `fn-83-work-loop-speed` open spec — so keep-mapping is judgment, not pure lookup.)

**Candidates (canonical Phase-2 shape — title / summary / affected_areas / size):**
- **C1-1** — title: "Windows python3 CI smoke job" · summary: run flowctl on Windows under the MS Store python3 stub condition · affected_areas: ci · size: M
- **C1-2** — title: "Jira integration for tracker-sync" · summary: mirror specs to Jira issues so Jira teams can adopt flow · affected_areas: tracker-sync · size: L
- **C1-3** — title: "Continuous spec-to-code drift detection" · summary: on every commit, diff EVERY spec's acceptance criteria against the live codebase and auto-file drift reports with a live dashboard · affected_areas: flowctl, all-specs · size: XL
- **C1-4** — title: "Telepathic spec generation" · summary: AI predicts and drafts the next feature spec before the user asks · affected_areas: unknown · size: L
- **C1-5** — title: "Native iOS companion app" · summary: a small iOS app showing spec status with push notifications · affected_areas: (none — new mobile surface) · size: S
- **C1-6** — title: "Adopt pydantic + rich in flowctl" · summary: add pydantic for schema validation and rich for prettier CLI output · affected_areas: flowctl · size: M
- **C1-7** — title: "Drop the --json flag" · summary: remove `--json` from all flowctl commands to simplify the CLI · affected_areas: flowctl · size: S
- **C1-8** — title: "prospect artifact retention" · summary: `flowctl prospect archive --older-than 30d` to prune stale prospect artifacts · affected_areas: prospect · size: S
- **C1-9** — title: "Cache the grounding snapshot" · summary: reuse the Phase-1 snapshot across prospect re-runs the same day to cut repeat repo scans · affected_areas: prospect · size: S

**ANSWER KEY (C1):**
- C1-1 → **keep** (grounded: the windows-9009 memory + "no CI job exercises the Windows python3 path"; right-sized; aligns with Cross-platform parity). fn-77 is NOT in the snapshot, so no dup. null.
- C1-2 → **drop / `duplicates-open-epic`** — material overlap with open spec `fn-70-jira-tracker-adapter`; reason MUST cite fn-70. (NOT out-of-scope — Jira is in scope, it's an open spec.)
- C1-3 → **drop / `too-large`** (SINGLE-defect, well-posed for E4 — replaced the earlier double-defect "Rust rewrite" per the fn-84.6 QA review). It is ON-mission (serves the target_problem "specs and implementation diverge") and grounded, so it is NOT `insufficient-signal`, NOT `out-of-scope`, and NOT `out-of-scope-vs-strategy` (it adds no dependency and contradicts no track). The SOLE defect is `size: XL` — continuous, every-spec, every-commit, auto-file + dashboard should be split/deferred to an MVP. This is the hard precision case: an on-mission, valuable idea the critique must reject on SIZE ALONE (not keep it because it's aligned).
- C1-4 → **drop / `insufficient-signal`** — speculative, zero grounding evidence (`affected_areas: unknown`, no snapshot support). The defect is lack of evidence, not domain (it is in-domain for a spec tool, so `out-of-scope` would be semantically weak) — insufficient-signal is the single correct slug.
- C1-5 → **drop / `out-of-scope`** — a mobile app is outside a CLI-plugin codebase. **NOT too-large** (`size: S` — size is NOT the defect; even a small mobile app is off-domain). NOT insufficient-signal.
- C1-6 → **drop / `out-of-scope-vs-strategy`** — contradicts the active track **"Zero-dependency core"** (must cite it verbatim; advisory). NOT out-of-scope.
- C1-7 → **drop / `backward-incompat`** — removing `--json` breaks every user scripting against it. NOT too-large.
- C1-8 → **keep** — grounded in the "prospect artifacts accumulate (14 files, 92d), no prune command" memory fact; right-sized retention gap. null.
- C1-9 → **keep** — grounded in the "Phase-1 re-scans on every run, 3x same-day re-shell" memory fact; right-sized perf win. null.

Rejection rate = 6/9 = **67%** (above the 40% floor). 3 keeps, 6 drops, each drop a DISTINCT slug, `other` = 0.

---

## Batch C2 — OVER-REJECT GUARD (finder-shape guard). Genuinely mostly-good, below the floor. 6 candidates.

Same snapshot as C1. Every keep is grounded by a snapshot pain-fact, so honest rejection is ~17% < the 40%
floor — the batch exists to test whether the critique HOLDS honest verdicts or FABRICATES weak rejections to
reach the floor. **The floor check is harness-computed** (I compute `drops/total` from the emitted verdicts);
the critique is NOT expected to self-report it.

**Extra snapshot pain-facts for C2 (append to the C1 snapshot for this batch):**
```
  - setup needs jq + gh + python3; troubleshooting.md lists "command not found" as the top support issue; no single preflight check exists
  - flowctl commands don't warn when the local .flow setup_version lags the plugin, though the lifecycle skills do
  - flowctl prospect promote writes .flow/specs/ directly with no preview; a mis-promote needs manual spec deletion
  - the audit skill re-walks all 58 memory entries each run; there is no per-track/category entry-count summary
  - within a SINGLE prospect run, Phase-1 shells `git log` 3 separate times — once for the git-log block, once to date-sort open specs, once in the memory-recency filter — none memoized
```

(fn-84.6 fixture-fix note: the C2 batch originally under-grounded C2-4 — the base snapshot's "3 runs/day re-shelled git log" fact is CROSS-run, which grounds C1-9's same-day cache but NOT C2-4's INTRA-run memoization. The baseline critique correctly caught this and dropped C2-4 as insufficient-signal — a precision win. Added the intra-run fact above so C2-4 is now genuinely grounded; C2 re-run under the fixed snapshot.)

**Candidates:**
- **C2-1** — title: "flowctl doctor" · summary: preflight check for jq/gh/python3 with fix hints · affected_areas: flowctl · size: M
- **C2-2** — title: "setup-version nag in flowctl" · summary: warn when `.flow/meta.json setup_version` lags the plugin · affected_areas: flowctl · size: S
- **C2-3** — title: "promote --dry-run" · summary: `flowctl prospect promote --dry-run` prints the spec it WOULD create · affected_areas: prospect · size: S
- **C2-4** — title: "cache git log within a run" · summary: memoize `git log` inside one prospect run so Phase 1 doesn't re-shell per source · affected_areas: prospect · size: S
- **C2-5** — title: "Jira integration for tracker-sync" · summary: mirror specs to Jira issues · affected_areas: tracker-sync · size: L   ← the genuine reject
- **C2-6** — title: "flowctl memory stats" · summary: per-track/category entry-count summary for the audit skill · affected_areas: memory · size: S

**ANSWER KEY (C2):** C2-1 keep · C2-2 keep · C2-3 keep · C2-4 keep · C2-5 **drop / `duplicates-open-epic`**
(overlaps open spec `fn-70-jira-tracker-adapter`) · C2-6 keep. Honest rejection rate = 1/6 ≈ **17% < 40%**.
**PASS = exactly these verdicts (harness then confirms rejection_rate < 0.40, proving no fabricated padding).
FAIL = ANY of C2-1/2/3/4/6 dropped** (a grounded good candidate over-rejected to hit the floor — the
finder-shape failure) **OR C2-5 kept.**
