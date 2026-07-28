# Handover: tracker-determinism batch (A done, B in PR, C next)

Paste this into a fresh agent in ~/work/flow-next. It carries the full state, ways of working, and next steps.

## Where we are

The tracker-determinism batch converts tracker-sync prose into the deterministic `flowctl_tracker/` Python package:

- **A = fn-139** (transport foundation): MERGED as PR #243, spec closed. No version bump (batched).
- **B = fn-140** (verb surface, capabilities, body fidelity): ALL 7 tasks done, completion review SHIP, **PR #246 open and ready-for-review** on branch `fn-140-tracker-determinism-b-verb-surface`. Two codex bot review waves already handled (7 threads total, all fixed + replied + resolved):
  - Wave 1 (a8524517): relate two-phase ledger intent (pending entry BEFORE provider mutation, finalize after; interrupted runs repair instead of queueing false collisions), Linear relation-probe pagination (drains both connections, truncated errors instead of reporting absence), GitHub label-readback degradation (non-list readback always yields status_labels_unverified).
  - Wave 2 (4aa57c02): status verb lost-update fix (applied/local-fold writes reload under config_lock, merge only status-owned fields), receipt now carries written.degraded, Jira remove-only assign identity guard (assignee_remove_skipped degradation on mismatch), facade comment dedup refuses to post after a truncated scan (TRANSPORT/dedup_truncated).
  - A wave-3 check was pending when this session stopped: **first action = check PR #246 for new bot comments and CI on head 4aa57c02** (CI was green on the prior head; the run on 4aa57c02 had not been confirmed).
- **C = fn-141** (spec exists in .flow, Quick commands already patched for the post-#245 ruff/prompt-pin gates): NOT started. Begin after B merges.
- **Batched release**: NO version bump until after C lands. Then one release covering A+B+C with full downstream walk (repo CHANGELOG -> flow-next.dev -> AI x SDLC guide -> Obsidian vault, per the private CLAUDE.md section).

## Rider that ships with PR #246

Commit bd196377 (out-of-spec, pipeline-blocking, documented in the PR body): "You ARE the reviewer - review directly" block added to impl-review, standalone-review, and completion-review prompt templates + their byte-identical FALLBACK constants; prompt-pin hashes refrozen in the same commit. Root cause: codex reviewer matched installed flow-next review skills in ~/.codex and spawned a nested codex that died in the sandbox -> no-verdict flaps. Flap-free since (10+ consecutive verdicts). plan-review deliberately NOT changed (write-once fn-130 B1 baseline, never flapped). A deferred chip (task_ea904b69) tracks a longer-term no-diff review-prompt eval + flap watch.

## Ways of working (proven over A + B, keep these)

**Implementation routing** (user-driven, per task):
- grok-4.5 via cursor bridge implements from a path-handoff brief: `cursor-agent -p --output-format text --force --model cursor-grok-4.5-high "$(cat brief.md)"` run in the background, output to a log. Brief format: READ FIRST (task md + spec + neighboring suites for fixture shapes), BUILD (numbered, concrete), HARD CONSTRAINTS (files it may touch, "Do NOT commit", "Do NOT edit task md files", no em dashes), VERIFY (focused suites + `uvx ruff@0.16.0 check plugins/flow-next/`).
- Host (you) reviews grok output BEFORE codex: known grok defect classes = production `assert` statements, vacuous durable-by-durable validation, silent pagination caps, ignored mutation success flags, task-md Done-summary edits (revert via git checkout), fixed multipart boundaries, credential-exfil URLs, double-probing.

**Review invocation** (codex backend, gpt-5.6-sol):
```
MAX_REVIEW_TRANSPORT_FAILURES=12 timeout 900 .flow/bin/flowctl codex impl-review <task-id> \
  --base $(git log --format=%h --grep "fn-140.N done" -n 1) \
  --sandbox workspace-write --receipt <scratchpad>/rev.json
```
Verdict via `grep '^VERDICT='`. The `--base` must be the task-scoped fork/prev-done commit (whole-branch diffs vs old main cause failures). Completion review: `flowctl codex completion-review <spec-id> --sandbox workspace-write --receipt ...`. Reviewer findings are usually right; when they cite canonical docs (status-sync.md etc.), the doc decides, not intuition.

**Propagation chain** (EVERY flowctl.py / flowctl_tracker change, before the gate):
1. `rsync -a --delete plugins/flow-next/scripts/flowctl_tracker/ .flow/bin/flowctl_tracker/`
2. flowctl.py changes: also cp to .flow/bin + regenerate the Python 3.14 help snapshot + HELP_SHA256 re-pin (new CLI subcommands change argparse help; asserted only on /opt/homebrew/bin/python3.14)
3. `python3 scripts/gen_tracker_manifest.py` (manifest replaced SOURCE_SHA256, covers flowctl.py itself)
4. `./scripts/sync-codex.sh` twice, only when skill files changed
Skipping any step fails test_tracker_distribution / test_startup_bootstrap.

**Full gate** (before any push): `python3 scripts/run_tests_parallel.py` (150 files, ~3000 tests) + `uvx ruff@0.16.0 check .` (pinned; CI matches). Focused suites per task: `cd plugins/flow-next/tests && python3 -m unittest test_tracker_<area> -q`.

**Bot-wave loop on PR #246** (repeat until quiet):
1. Poll: `gh api graphql` reviewThreads for `isResolved==false` (bot = chatgpt-codex-connector; triggers on ready-for-review and on each push, ~5-10 min after).
2. Triage per the wave discipline: fix P0/P1 + correctness/contract gaps; decline completeness-P2s with a reasoned reply + resolve. So far every finding was a genuine correctness gap.
3. Dispatch `pr-comment-resolver` subagents (parallel only on disjoint files; the relate package once needed serialization). Each gets: thread id, full finding text, file, repo contract constraints (never-raises boundary - TrackerError returns, no production asserts; no em dashes; do not commit; do not touch .flow/bin), required regression tests, focused-suite verify commands.
4. Host: propagate (chain above), full gate, ONE commit staging exactly the resolver files + .flow/bin mirrors + MANIFEST, push.
5. Reply + resolve via the bundled scripts (stdin, thread-id arg):
   `$SCRIPTS/reply-to-pr-thread THREAD_ID < reply.md && $SCRIPTS/resolve-pr-thread THREAD_ID`
   where SCRIPTS=~/.claude/plugins/cache/flow-next/flow-next/3.4.4/skills/flow-next-resolve-pr/scripts. Replies quote the finding, cite the fix commit + test names.

**Hard rules**: no em dashes in ANY artifact. Never delete uncommitted .flow/* without asking. flowctl done owns task-md Done sections. Batched releases (no bump.sh until after C). No `gh pr merge` from skills - merge is Gordon's call. Conventional Commits. Foreground sleeps blocked - use background tasks with notifications for watches.

## What is next, in order

1. **Wave-3 check on PR #246**: CI on head 4aa57c02 + any new bot threads. Handle per the loop above.
2. **Merge #246** when Gordon says go: `gh pr merge 246 --squash --match-head-commit <head-sha>`. Then close the spec if flowctl has not already (verify `flowctl show fn-140-...` spec status; `flowctl spec close` if needed) and commit flow state.
3. **Spec C = fn-141**: `flowctl show fn-141-<slug>` (tab-complete the id via `flowctl list`). Same pipeline as B: claim tasks, grok implements per brief, host review, codex impl-review per task to SHIP, completion review, make-pr draft, flip ready, babysit bot waves. Check whether recent B merges affect C's task specs before starting (same as was done when #244/#245 landed).
4. **After C lands**: batched release for A+B+C - read agent_docs/releasing.md, bump once, full downstream walk (repo -> flow-next.dev incl. BOTH nav sources -> AI x SDLC guide -> vault notes: Tracker Sync note is the main one, plus Release Timeline story beat).
5. **Then**: flow-swarm upstream tasks (see vault DIRECTIONNEW.md context; fn-118 parallel-dispatch and fn-132 opus-5 trace analysis are also parked backlog).

## Key design invariants (the reviewers test against these; do not regress)

- Locator {durable, display}: mutations address by durable; pre-mutation parent reads address by display and compare display->durable (catches moves).
- Never-raises boundary: every provider path returns TrackerError, no production asserts.
- Pagination drains with honest `truncated` flags; unproven absence is NEVER absence (relate probe, comment dedup).
- Structured `degraded` fields everywhere (never prose); the facade lifts nested result["write"]["degraded"].
- status: `--to` is a request, the fn-66 merge-evidence gate decides; lastSyncedAt advances ONLY on applied; open+closed PR evidence IS ambiguous (status-sync.md decides).
- sync-body: merge base equals the READBACK, both halves committed atomically under config_lock; flow:deps region excluded from divergence hashing.
- relate: two-phase pending/finalize ledger intent; additive-only; human-removed edges queue to .flow/review-deferred/tracker-relate.md, never recreated silently.
- Spec-file writes serialize under config_lock (relate _ledger_write, syncbody _commit_paired_base, status _persist_applied_state).
- Receipts: one per verb under .flow/sync-runs/; facade suppresses step receipts (write_receipt=False) and writes ONE aggregate with worst-of-steps status.
