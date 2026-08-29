# /flow-next:features maintain

Execute these phases in order. Each gates on the prior. Stop on a user-blocking error - never plow through with bad state.

Autonomy refusal and `MODE=maintain` are already resolved in [SKILL.md](SKILL.md). Feature file shape: [references/feature-entry-contract.md](references/feature-entry-contract.md). Doctor + proof: [references/doctor-and-proof.md](references/doctor-and-proof.md).

**Live driving consumes the drive skill by pointer.** Read [`plugins/flow-next/skills/flow-next-drive/SKILL.md`](../flow-next-drive/SKILL.md) (surface detection + universal flow + ladder) and the relevant rung reference under `plugins/flow-next/skills/flow-next-drive/references/`. **That prose stays there.** A copy of CDP / agent-browser / Computer-Use actuation detail written into this file has broken this. Execute the universal flow (`observe → snapshot fresh refs → act → verify → capture`) yourself. A transcript that "calls" flow-next-drive as if it were an API has broken this too.

Maintain is not a second QA pass and never replaces QA. Edit scope is `.flow/features/` plus harness scripts the map already names as launch, seed, or drive helpers. Never product code.

Run notes and live evidence land under `.flow/tmp/features-<run-id>/` (gitignored, same per-run tmp convention QA uses), referenced by path, never inlined. The `changed` PR carries `.flow/features/**` plus owned harness corrections. Run notes, scratch, and evidence stay out.

Assemble any structured output with `jq` or python. Never interpolate free-form prose into a heredoc JSON.

---

## Preamble

**CRITICAL: flowctl is BUNDLED - NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks in this file use `$FLOWCTL`:

```bash
set -e
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
RUN_DIR="$REPO_ROOT/.flow/tmp/features-$RUN_ID"
mkdir -p "$RUN_DIR"
```

**Entry gate (both checks, before any inspection):**

1. **On the default base.** Resolve the default branch (`gh repo view --json defaultBranchRef` or `git remote show origin`), fetch it, and require BOTH to match `origin/<default>`: the product code (`git diff --quiet origin/<default> -- . ':(exclude).flow/'` or an equivalent read) AND the owned map itself (`git diff --quiet origin/<default> -- .flow/features/`). Excluding only Flow runtime/bookkeeping keeps the audit honest - a branch-only map would otherwise be proven and certified as if it were the default branch's. A maintain pass proves routes against the code its PR will ship on; proof gathered on a diverged feature branch is proof of the wrong base. Diverged: end `BLOCKED` with the instruction to run maintain from the default branch (or a clean checkout of it). Never switch branches over the user's working state.
2. **Owned paths clean.** `git status --porcelain -- .flow/features/` (plus any harness paths the map owns) must be empty. Pre-existing uncommitted edits under owned paths cannot be told apart from this run's edits later, and the `BLOCKED` restore would discard them. Dirty: end `BLOCKED` asking the user to commit or stash first. This makes every later owned-path change attributable to this run by construction.

`jq` and a working Python (`python3`, `python`, or `py -3`) must be on PATH. `$FLOWCTL` is required for `memory search` / `memory add` on the `feature-map-drift` tag. Memory disabled or uninitialised: treat drift search and bug filing as empty, record that in the run notes, continue.

This file is self-sufficient. Do not assume SKILL.md already exported `$FLOWCTL`.

---

## Phase 1: Index hygiene

**Goal:** the index matches the feature files on disk, and drift memos from prior QA/maintain runs are in this pass's targets.

Read `.flow/features/README.md`. Glob `.flow/features/*.md`, excluding the index. Compare:

| Mismatch | Fix |
|----------|-----|
| File on disk, no index row | Add the row (Surface + sub-feature IDs from the file) |
| Index row, no file | Drop the row, or restore the file only if a live drive later proves it |
| Duplicate slug or path | Keep one; drop the extra |
| Dead path (row points at nothing) | Drop the row |

**Drift memos.** Consume the `feature-map-drift` tag:

```bash
DRIFT_RAW="$($FLOWCTL memory search "feature-map-drift" --json --limit 10 2>/dev/null || true)"
```

Parse with `jq`. `has("error")` or empty → no memos, continue. Fold relevant hits into this pass's targets (feature slug, route, Surface they name). Titles, tags, named routes only. Never paste memory bodies into later prompts.

**Source-confirmed deletion.** Removing a feature the product deleted is a source-confirmed deletion. No live drive is required to prove an absence. Drop the feature file and its index row. Record the source fact in the run notes (the missing surface, the path that used to implement it). A deletion without that source fact is not confirmed - leave the file for the source wave.

Contract-broken files (missing `**Surface:**`, H2s out of order or missing) stay in the live-pass queue and are marked doc drift for Phase 5.

### Done when

- The entry gate passed: checkout matches the default base and owned paths were clean (or the run already ended `BLOCKED`).
- Index rows and feature files agree, or every remaining mismatch is queued as a this-pass edit.
- Drift memos were searched; relevant ones are on the target list.
- Source-confirmed deletions are recorded and not queued for a drive.

---

## Phase 2: Source wave

**Goal:** one read-only view of every remaining feature file, concurrently. Readers never drive, never edit.

Dispatch **one** `Task` with `subagent_type: Explore` **per feature file**, batched to the host's concurrent-subagent capacity: fill a batch in one turn, await it, dispatch the next - readers within a batch run concurrently, and a map larger than the cap costs extra batches, never a failure. A host with no concurrent dispatch at all degrades to reading the files inline on the main thread (read-only, same return shape) and reports `Sequential fallback: source wave ran inline`. Exceeding the cap is a batching concern, never `blocked-for-this-pass` - that mark is for a reader that errored. On hosts without Explore, use the host's generic read-only dispatch with Edit/Write disallowed. `Task` is also disallowed for the child (a nested writing subagent is an escape hatch).

Pass each reader an identity (the feature file path) plus the contract pointer. Do not embed the file body. Instruct:

> Use Read, Grep, Glob. Do not drive. Do not Edit, Write, or mutate git. Return only the payload below.

Return shape (exactly these keys):

```text
feature: <slug>
summary: <one-line user-visible behavior>
source_entry_points:
  - <where the user-facing surface lives in this checkout>
likely_drift: none | <one concrete claim>
live_recipe:
  entry: <user entry point from How to get to it>
  preconditions: <from Driving it>
  first_action: <one labeled bullet: user action, command, observable>
```

A reader that reports source entry points gone is source-confirmed deletion: drop the file, no drive, same rule as Phase 1.

A reader that errors or times out: mark that feature `blocked-for-this-pass`. Name it. The pass continues for the rest.

**Collapse:** every reader failed - dispatched or inline alike (a host with no dispatch runs the inline path above; that is a fallback, never a collapse). End `BLOCKED` (skip to Phase 6 teardown). Reason names the collapse.

The orchestrator (this skill, main thread) merges payloads. Readers do not write.

### Done when

- Every remaining feature file has a payload or a `blocked-for-this-pass` mark.
- No reader drove or edited.
- Collapse already terminated `BLOCKED`.

---

## Phase 3: Reconcile

**Goal:** a drive plan that covers every remaining feature with as few app states as practical, plus cited drift and any unmapped surfaces.

- Merge returned `live_recipe` values into as few app states as practical (same Surface, same signed-in user, same port/profile). Order writes ahead of reads of what they create.
- Spot-check **cited** drift only (`likely_drift` is not `none`). Never re-prove a reader's clean claim.
- Sweep recent churn for user-facing surfaces missing from the map (new routes, screens, CLI commands a user would name). **A concrete source path is required before calling one missing.** No path, no missing claim.
- Missing surfaces join the live-pass queue as candidates. They land only after a live drive. An undriven file does not enter the map.

`blocked-for-this-pass` features stay named and are not in the drive plan.

### Done when

- A drive plan exists: ordered app states, features per state, cited-drift list, missing-surface list (each with a source path) or explicit none.
- Clean claims from readers were not re-investigated.

---

## Phase 4: Live pass

**Goal:** every remaining feature is exercised once against an instance this run started. Required even when source looks clean.

Read [references/doctor-and-proof.md](references/doctor-and-proof.md) **before the first drive**, on each fresh session, and again after any failed drive. Skipping a required Doctor run has broken this.

Never drive an instance this run did not start. An orphaned port (a process this run did not start) ends `BLOCKED` with the reclaim instruction for the human. Never kill by process name. Two concurrent runs isolate by disposable profile/port; where the app cannot run twice, the owned-port check fails and this run ends `BLOCKED`. Never a shared drive.

A checkout that does not build or start as-is: end `BLOCKED` naming the precise breakage. No usable driver on this host: end `BLOCKED` naming the missing driver. (Seed uses `REFUSED` for these; maintain's outcome set is exactly clean/changed/blocked, so a pre-pass failure here is a named block.) Never write map edits against a broken base.

Start the instance this run will own. Doctor once for this session, then execute the drive plan:

1. **Doctor** (before first drive this session; after any failed drive; on a fresh session).
2. **Drive** via the flow-next-drive pointer above. Universal flow: observe → snapshot fresh refs → act → verify → capture.
3. **Proof** follows [references/doctor-and-proof.md](references/doctor-and-proof.md): capture the user action **and** the resulting state, not just the final screen; verify side effects beside what is visible; exercise the real user path, never a test-only endpoint.

Evidence lands at named paths under `$RUN_DIR`. Reference by path.

**`verified-unreachable`** only with both:

- the **concrete prerequisite** that was unmet
- the **route that was attempted**

Never record it as verified-via-another-path. An unstated prerequisite is itself drift: queue it for Phase 5 as map drift, not as a pass.

Wedged UI on a healthy process (Doctor cannot see it): reset to a known state or relaunch rather than hoping. Doctor again on the recovered instance before the next drive.

A harness fix from Phase 5 is re-driven live (this same Doctor + drive + proof loop) **before it ships**. Keep the instance up until that re-drive finishes.

**Final teardown after the last drive of this run**, including any Phase 5 re-drive. Cleanup removes instances and scratch this run started, **never evidence**. After teardown, verify each evidence file still exists at its named path. A cleanup that eats the proof fails the step.

### Done when

- Every feature that was in the drive plan has one live exercise with evidence at a named path, or is `verified-unreachable` with the pair above.
- Doctor ran at the required times. No drive used an instance this run did not start.
- Teardown is done once the last (re-)drive finished, or is deferred only while a Phase 5 re-drive is still queued.
- `BLOCKED` already terminated when Doctor, the checkout, or the driver forbade a drive.

---

## Phase 5: Triage

**Goal:** every live finding lands in exactly one bucket. Edits stay inside the map and the harness it owns.

| Bucket | When | Action |
|--------|------|--------|
| **Doc drift** | Wrong or missing user-POV description. The live app matches what a user would expect; the map does not. Unstated prerequisite. `verified-unreachable` whose map omitted the real precondition. | Fix the map (index and/or feature file) to match the proven live behavior. Four-H2 + `**Surface:**` contract still holds. Nothing undriven enters the map. |
| **Harness gap** | The app works. The harness the map owns cannot drive it. | Fix that owned harness script. Re-drive live (Phase 4 Doctor + drive + proof) before it ships. A harness fix that was not re-driven does not ship. |
| **Product bug** | App behavior is actually broken. | Report it. Never in the PR. Never edit product code to make a drive pass. |

**Reporting a product bug.** File to the bug memory track when memory is enabled. Write the body under `$RUN_DIR` first, then `memory add --track bug --body-file ... --json`. Overlap scoring stays on (never `--no-overlap-check`). Parse the JSON with `jq` or python. Memory disabled: record the finding in the run notes only. Either way the finding stays out of the `changed` diff.

**Edit scope.** `.flow/features/**` plus harness scripts the map already names as launch, seed, or drive helpers. Never product code. A path the map does not already own is out of scope.

Re-drive every harness fix before leaving this phase. Then teardown (Phase 4 rule) if the instance is still up.

### Done when

- Every live finding is in exactly one bucket.
- Map and harness edits exist only for doc drift and re-driven harness gaps.
- Product bugs are reported and listed for the reason line; none of them are in the staged diff.
- Every harness fix has a post-fix live proof at a named path, or it was not queued to ship.

---

## Phase 6: Ship or stop

**Goal:** exactly one outcome. No resume state. The terminal line is last.

Teardown first if the instance is still up (Phase 4 rule). Evidence stays at named paths under `$RUN_DIR`.

Pick exactly one. `blocked-for-this-pass` features prevent `CLEAN` (coverage was incomplete). They do not by themselves prevent `CHANGED` for the features that were proven - but the terminal `reason` of a `CHANGED` or `BLOCKED` run MUST name every `blocked-for-this-pass` feature slug. An outcome line that silently drops a blocked feature has broken this.

### CLEAN

Every feature was covered (live exercise, `verified-unreachable` with the required pair, or source-confirmed deletion). No map or owned-harness change. **No branch, no PR.**

`features=<n>` is the count of feature files remaining in the map.

### CHANGED

At least one proven map or owned-harness correction.

1. **Re-read every changed file.** A file not re-read does not ship.
2. Create a **fresh branch** `chore/features-maintain-<YYYY-MM-DD>-<run-id>` (the preamble's `$RUN_ID` suffix keeps a second same-day pass collision-free locally and on the remote) from `origin/<default>` (the entry gate already proved the checkout matches it, so the proofs gathered this run apply to exactly the code this PR ships on; the uncommitted map/harness edits ride the switch). If the switch conflicts with local state, end `BLOCKED` naming the conflict instead of shipping a mixed PR.
3. Stage **only** `.flow/features/**` plus the owned harness files that were re-driven. Never `$RUN_DIR`, never run notes, never scratch, never evidence. Never `git add -A`.
4. Commit, **push the branch with upstream tracking** (`git push -u origin <branch>` - `gh pr create` on an unpushed branch prompts, and a prompt in a non-interactive shell wedges the run), then open **one chore PR** directly:

```bash
gh pr create --title "chore(features): maintain pass" --body-file "$PR_BODY"
```

Write `$PR_BODY` to a file under `$RUN_DIR` (or a tempfile). Hand-written body matching the make-pr **structure**, these four sections in order:

- **Summary**
- **What changed**
- **Per-feature outcomes**
- **Evidence pointers** (paths under `$RUN_DIR`, referenced, not inlined)

`--body-file`, never a heredoc. Never invoke `/flow-next:make-pr` (it requires a spec behind the diff). **Never merge.** Never `gh pr merge`. Never `/flow-next:land`. The PR stays open for the human or land.

If the push or `gh pr create` fails: do not claim `CHANGED`. End `BLOCKED` naming the branch and which step did not land.

`features=<n>` is the count of feature files remaining in the map after corrections.

### BLOCKED

A named blocker stopped the pass: orphaned port, concurrent isolation failure, source-reader collapse, or a `gh pr create` failure after proven commits. Reason names what blocked.

**Terminal for this invocation.** The next run re-enters fresh from the committed map. No resume file, no checkpoint. Do not open a PR of unproven edits. Restore uncommitted map/harness edits to HEAD - the entry gate proved owned paths were clean at start, so everything dirty under them is this run's own work; pre-existing user edits were never admitted. Run notes remain under `$RUN_DIR` for the human; the next invocation ignores that directory.

`features=<n>` is the count of features fully covered before the block (`0` if none).

### Terminal line

Print as the **last line** of the run, nothing after it:

```text
FEATURES_VERDICT=<SEEDED|CLEAN|CHANGED|BLOCKED|REFUSED> features=<n> reason="<one line>"
```

Maintain emits exactly `CLEAN`, `CHANGED`, or `BLOCKED`. Not `SEEDED`, not `REFUSED` (those belong to seed and the SKILL.md autonomy fence). `reason` is one line, quoted.

### Done when

- Exactly one verdict. Last line is one `FEATURES_VERDICT=` line matching the grammar above.
- `CLEAN`: no branch, no PR.
- `CHANGED`: one open PR from a branch cut off the default base and pushed with upstream tracking; every shipped file was re-read; body has the four sections; notes, scratch, and evidence are not in the diff.
- `BLOCKED`: reason names the blocker; no resume file; next run starts from the committed map.
- Every `blocked-for-this-pass` feature slug appears in the terminal `reason` when the outcome is `CHANGED` or `BLOCKED`.
