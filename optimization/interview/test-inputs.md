# Frozen test inputs — interview suite (4 inputs, FROZEN)

Each fixture is a spec the interview skill refines, plus a **frozen codebase context** (what
interview's "investigate before asking" pass would find — held constant so the eval isolates the
question-generation prose, not live investigation). Scope = **technical** for all four (loads
`questions-technical.md` + `questions-shared.md`). Specs are deliberately **functionally clear but
NFR-thin** so E4 (NFR-coverage) has headroom.

**Run-trick — question EMISSION.** The skill's contract is to ask via `AskUserQuestion`; for the
eval the run-subagent instead EMITS the questions it would ask (in decision-tree order, each with its
lead recommendation + confidence tier + options), and does NOT wait for answers or write the spec.
Model held constant: **sonnet** (runs); **fable** judges E4/E5 (question quality) independently.

---

## I1 — flow-next, thin spec, technical scope (NFR-coverage headroom)

**Spec under interview (`fn-90-flow-watch`):**
```markdown
# fn-90-flow-watch — live `flowctl watch` for .flow/ changes
## Overview
Add `flowctl watch` — a foreground command that tails the local `.flow/` tree and prints a live
line each time a spec or task changes (created / status-changed / done), so a user running a build
loop in one pane can watch progress in another.
## Acceptance Criteria
- **R1:** `flowctl watch` runs in the foreground and prints one line per detected spec/task change.
- **R2:** Each line shows the id, the new status, and a timestamp.
- **R3:** Ctrl-C exits cleanly.
```

**Frozen codebase context (interview's investigation would find):**
- `.flow/specs/*.json` + `.flow/tasks/*.json` are the state files; each carries `status`, `updated_at`.
- flowctl is pure-stdlib Python 3.8+, cross-platform (macOS/Linux/Windows); NO third-party deps allowed (so `watchdog`/`inotify` libraries are out — detection must be stdlib).
- No existing long-running/daemon command in flowctl — every command is one-shot; there is no precedent for a foreground loop, signal handling, or a polling loop in the codebase.
- Tests are pure-stdlib unittest under `plugins/flow-next/tests/`, no process-spawning harness for long-running commands exists.

**Gaps a good interview should probe (for scoring — NOT shown to the run):** change-detection mechanism
(stdlib polling interval vs mtime-scan — perf/latency tradeoff, given no inotify dep); behavior under a
large `.flow/` (scale); partial-write / mid-write race (a `.json` read while flowctl is rewriting it —
failure mode); symlinked `.flow/` (common per project convention); how to TEST a long-running foreground
loop (no precedent); Windows signal handling (Ctrl-C / SIGINT portability). All NFR-shaped, none stated.

---

## I2 — DocIQ-Sphere, thin spec, technical scope (NON-flow-next anti-overfit, Major-2)

**Spec under interview (DocIQ-Sphere feature):**
```markdown
# diff-endpoint — tracked-change diff between two batch commits
## Overview
Add `GET /api/documents/{id}/diff?from={commitA}&to={commitB}` returning the tracked-change diff
(insertions/deletions/format changes) between two committed batches of a `.docx` document.
## Acceptance Criteria
- **R1:** The endpoint returns a structured diff (per-run insert/delete/format ops) between the two named commits.
- **R2:** A 404 is returned when either commit id is unknown for that document.
```

**Frozen codebase context (interview's investigation would find):**
- FastAPI app; `/api/*` routes; documents are edited via atomic batches (`begin_batch`/`commit_batch`); each commit is an OOXML snapshot produced by the shared vendored OOXML editor.
- Commits are stored per-document; the OOXML editor is the serial, expensive shared resource.
- Env-toggle config pattern (`DOCX_STRICT_VALIDATION`); Python 3.11 (uv); pytest.
- No existing diff/compare code path; the OOXML editor can render a document at a commit but has no built-in two-snapshot compare.

**Gaps a good interview should probe (for scoring):** diff granularity/algorithm (run-level vs
paragraph-level — correctness + perf on large docs); computing a diff drives the serial OOXML editor
twice → contention with live `commit_batch` (perf/concurrency — the shared-resource failure mode);
auth/authorization on the endpoint (security — who can read another workspace's doc diff); very large
document performance/timeout; malformed/partial commit handling beyond the 404; caching a computed diff.
Foreign-code grounding: should reference FastAPI/`commit_batch`/OOXML-editor, NOT flow-next patterns.

---

## I3 — flow-next, EXISTING hand-edited spec (override-respect + non-redundancy; E3 load-bearing)

**Spec under interview (`fn-92-audit-log`, hand-edited — USER-AUTHORITATIVE):**
```markdown
# fn-92-audit-log — append-only audit log for flowctl mutations
## Overview
Record every state-mutating flowctl command (start/done/set-*/spec-*) as an append-only JSONL line
under `.flow/audit.log` for later review.
## Boundaries / non-goals
- <!-- hand-edited by user, keep verbatim --> DECIDED: JSONL only, no rotation, no size cap in v1 —
  we accept unbounded growth; a prune command is a separate future spec. Do NOT re-open this.
- <!-- hand-edited --> DECIDED: log the command + args + timestamp + resulting id; NOT full before/after
  state snapshots (too heavy). Do NOT re-open this.
## Acceptance Criteria
- **R1:** Every state-mutating flowctl command appends one JSONL line to `.flow/audit.log`.
- **R3:** Each line carries: command, args, timestamp (UTC ISO-8601), resulting id.
- **R5:** Read commands (list/show/ready/...) do NOT write to the log.
```

**Frozen codebase context:** flowctl commands dispatch through `cmd_*` functions; a shared mutation vs
read-only classification already exists (the tracker `perEvent` gating knows which commands mutate);
atomic-write helper exists; pure-stdlib.

**Gaps a good interview should probe (for scoring):** concurrency — two flowctl processes appending at
once (append-atomicity / interleaving — a real failure mode); what happens if `.flow/audit.log` is
unwritable (permissions / read-only FS — error handling); the R-ID gap (no R2/R4 — do NOT compact or
renumber); performance of append on every mutation. **MUST NOT** re-ask the two DECIDED boundaries
(no rotation/size-cap; no full-state snapshots) — re-opening a user-decided point is the E3 failure.
**MUST NOT** rewrite/renumber the hand-edited spec.

---

## I4 — flow-next, NEARLY-COMPLETE spec, technical scope (RESTRAINT stress; E5 headroom)

Added to stress the OPPOSITE of NFR-coverage: interview's prose ("expect 40+ questions", "continue
until complete") can bias it toward OVER-asking. On an already-well-specified spec the correct,
high-quality behavior is **restraint** — ask only the genuinely-open questions, explicitly note what's
already settled, and do NOT pad with obvious questions or re-ask what the spec answers.

**Spec under interview (`fn-93-done-dryrun`, thorough):**
```markdown
# fn-93-done-dryrun — `flowctl done --dry-run`
## Overview
Add `--dry-run` to `flowctl done <task>`: validate everything `done` would do (task exists, is
in_progress, evidence/summary present and parse-clean) and print what WOULD change, but write nothing.
## Acceptance Criteria
- **R1:** `flowctl done <task> --dry-run` performs all of `done`'s validation and prints the would-be status transition + the parsed evidence/summary, then exits 0 without writing.
- **R2:** On a validation failure (task missing, not in_progress, evidence unparseable), `--dry-run` prints the SAME error `done` would, and exits with the SAME non-zero code — parity with the real path.
- **R3:** `--dry-run` writes NOTHING: no task json/md mutation, no receipt, no git, no tracker touch.
- **R4:** `--json` is honored with `--dry-run` (emits the would-be result object with a `"dry_run": true` field).
## Boundaries / non-goals
- No `--dry-run` on other commands in this spec (start/set-* are separate if wanted later).
## Edge Cases & Constraints
- Validation reuses `done`'s existing validators verbatim (single source of truth — no forked logic).
- Error parity is asserted by a test that runs the same failing inputs through both paths and diffs code+message.
## Testing
- Parametrized test: for each of {happy, missing-task, not-in-progress, bad-evidence}, assert `--dry-run` matches `done`'s exit code + stderr and leaves the tree byte-identical (no writes).
```

**Frozen codebase context:** `cmd_done` in flowctl.py already has the validators + the write path cleanly separated; atomic-write helper; pure-stdlib; dual-copy invariant (`scripts/flowctl` ↔ `.flow/bin/flowctl`); tests under `plugins/flow-next/tests/`.

**Expected shape (for scoring — NOT shown to the run):** this spec is thorough — validation reuse,
error parity, no-write guarantee, --json, testing all stated. A HIGH-QUALITY interview asks **0–2**
genuinely-open questions (e.g. the exact human-readable format of the "would change" preview, or whether
`--json`+`--dry-run` should also short-circuit the `--summary-file`/`--evidence-json` file reads) and
**explicitly states the rest is well-specified**. E5 FAILS if it pads with obvious/answered questions
(re-asking what R1–R4 already decide, generic "what about error handling?" when R2 covers it, asking
about other commands the Boundaries already exclude). E3 fails on redundant/answered questions.
