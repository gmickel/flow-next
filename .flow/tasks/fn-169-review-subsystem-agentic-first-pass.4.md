---
satisfies: [R3, R4]
---
# fn-169-review-subsystem-agentic-first-pass.4 Payloads become identities; delete the truncation layer

## Description
Stop shipping the reviewer content it fetches anyway, and delete the machinery that existed only to make the payload fit.

**Size:** L
**Files:** `plugins/flow-next/scripts/flowctl.py` (`build_review_prompt` ~:9599, `_gather_review_diff` + `_gather_review_diff_capped`, the three cursor fitters, `_cursor_disk_read_header`, `build_convergence_ratchet_block`, `_render_structured_prior_finding`, `_build_impl_prompt_cursor`, the argv constants/markers ~:8484-8560), the impl/plan/completion prompt templates, `plugins/flow-next/tests/`, `.flow/bin/flowctl.py`

### Approach
- **Switch the scope signal from `--stat` to `--numstat` FIRST — this is the line that makes the whole model work.** Measured on the fn-168 diff: `git diff --stat` abbreviated **51 of 65 paths** (`.../pr-cognitive-aid/.write.lock`), so `<diff_summary>` today is a human-readable summary that cannot serve as a resolvable file set. It gets away with that only because the diff body ships alongside it. Remove the body and rely on `--stat` and the reviewer loses the file set. `git diff --numstat` on the same range: **65 exact paths, 0 abbreviated, 4,315 bytes** versus the body's **641,784** — 150x smaller and complete. Change it in `_gather_review_diff` and keep the label `<diff_summary>` (or rename to `<changed_files>` if clearer).
- Replace the five payload slots with identities: `<diff_content>` -> `<base-sha>..<head-sha>` (the reviewer runs `git diff` itself); `<spec>` -> `.flow/specs/<id>.md`; `<task_specs>` -> the task md paths. **Keep** `<diff_summary>` (bounded `--stat`, the cheap scope map that makes fetching targeted) and `<context_hints>` (bounded at 15, genuine starting points).
- Rewrite the rubric's "This review includes:" section accordingly — it currently declares the embedded diff "the authoritative 'what changed' signal" two lines before saying "You have full access to read files from the repository." Three near-identical copies exist (impl / standalone / plan); update all.
- **RETAIN a transport-only guard (plan-review r1, P1).** `CURSOR_ARGV_PROMPT_MAX` is doing double duty: content-fitting budget AND `run_cursor_exec`'s fail-closed boundary before it invokes positional argv. Cursor's Windows `CreateProcessW` limit does not disappear because we stopped embedding, and every caller of the shared runner — including the validator and deep-pass paths — depends on that explicit refusal. Rename it `CURSOR_ARGV_TRANSPORT_MAX`, document it as a transport boundary, and keep the fail-closed error. Deleting it would trade a controlled non-zero exit for a platform-dependent process-launch failure.
- **Delete fn-168's interim cursor sweep gate here** (`_FINDINGS_TRUNCATING_BACKENDS` and the `allow_aggregate` parameter). It could not go in `.3`: until the fitters are gone, a resume-FAILURE round on cursor still receives rendered prior items that the argv fitter can truncate. Once truncation is gone the gate has nothing to guard.
- **Delete** the content-fitting layer: `fit_cursor_prompt_to_budget`, `fit_cursor_diff_to_budget`, `fit_cursor_rereview_prompt_to_budget`, `_cursor_disk_read_header`, `_render_structured_prior_finding`, `_neutralize_prior_findings_text`, `_build_impl_prompt_cursor`, the ratchet's item rendering, the 50 KB diff cap for non-`export` paths, and the review-side argv constants/margins/markers (~594 lines of top-level defs plus 8 constants).
- **`export` keeps embedding** — no repo access, so the payload is its only channel. Keep the diff builder for that path only.
- **The artifact hash is unchanged**: `review-artifact` already reads the diff from `--diff-file`, so it keeps hashing spec+tasks+diff bytes and simply stops shipping them. Passing real `<base-sha>..<head-sha>` makes the reviewed range exact and replayable.
- Fix or delete `_gather_review_diff_capped`, whose docstring claims "50KB hard cap + truncation marker" while its body is a bare passthrough.
- `test_prompt_text_pinned` will fail — update hashes in the same commit with rationale (CLAUDE.md sanctions a deliberate prompt change). `optimization/reached-path` route evidence will shift; recompute from the live measurement.
- Propagation: `cp` flowctl.py, `./scripts/sync-codex.sh` TWICE (no second-run diff).
- **CORRECTION (found during implementation): do NOT delete `_render_structured_prior_finding` or `_neutralize_prior_findings_text`.** The approach above lists the ratchet's item rendering among the deletions, written before `.3` existed. `.3` made injection a LIVE fallback — it fires whenever resume fails, and unconditionally on cursor, copilot, and host. A reviewer's own prior findings are not a repo artifact: they live in the receipt, not in the tree, so "pass identities, not payloads" does not reach them and there is nothing for the reviewer to fetch. Deleting the renderer would make exactly the fallback path `.3` exists to protect a blind review. `_neutralize_prior_findings_text` is a delimiter-injection defense, unrelated to truncation. Both stay. What gets deleted is the machinery that made the payload *fit*, not the payload the reviewer cannot obtain any other way.
- **`export` never used this builder** (verified): `--review=export` is a skill route through `flow-next-export-context`, which composes its own artifact with `git diff --name-only`. No flowctl code path reaches `_gather_review_diff` for export — the registry `gather_diff` hooks belong to codex, copilot, and cursor only, all of which have repo access. So the "keep the diff builder for export" carve-out has no code to carve: the embedding layer serves only repo-capable backends and deletes cleanly.
- **The artifact hash must switch to the FULL diff, not the dispatched one.** `build_impl_review_artifact_blob` currently hashes the blob actually delivered in the prompt, recovered by `_dispatched_diff_from_prompt` — machinery that exists only because whole-prompt fitting could truncate it. With nothing embedded, the delivered blob is empty and the guard would stop seeing code changes between rounds. Gather the full diff for the IDENTITY only (never for a prompt) and hash that: strictly stronger than the fitted blob, and it retires `_dispatched_diff_from_prompt` with the truncation it was compensating for.

### Investigation targets
**Required:**
- `build_review_prompt` (~:9599) — the five payload slots and the three rubric variants (~:9108, ~:9299, ~:9409)
- `_gather_review_diff` — the 50 KB cap and marker; `_gather_review_diff_capped` (stale docstring)
- The cursor budget block ~:8484-8560 — constants, margins, markers, `CURSOR_ARGV_PROMPT_MAX = COPILOT_ARGV_PROMPT_MAX`
- `cmd_review_artifact_build` — confirm the hash path is untouched
- The `export` review route — the one branch that must keep embedding

**Optional:**
- 2.5.0 CHANGELOG / commit `a7297f9a` — fn-74 did this for file contents; mirror its shape

### Key context
- Measured: the fn-168 diff is 495 374 B against a 50 000 B cap, so reviewers saw ~10% and fetched the rest. The turn cost of fetching is ALREADY being paid; removing the payload deletes overhead rather than adding round-trips.
- codex takes the prompt on **stdin**, so it never had a size limit — embedding there was pure cost. Cursor's argv cap traces to Windows `CreateProcessW`, ~35x below this machine's `ARG_MAX`.
- Do not delete `<diff_summary>`: it is what keeps fetching targeted, and `.2`'s eval arm C exists to prove whether it is load-bearing.

## Acceptance
- [ ] `<diff_summary>` is generated with `--numstat` (or `--name-status`): every changed path appears in full, none abbreviated — verified on a >50-file diff
- [ ] `<diff_content>` / `<spec>` / `<task_specs>` replaced by a SHA range and paths for every non-`export` backend; `<diff_summary>` and `<context_hints>` retained
- [ ] All three rubric variants updated; no text still calls an embedded diff the authoritative signal
- [ ] The three cursor fitters, `_cursor_disk_read_header`, the ratchet item renderer, and the review-side argv constants/markers are GONE; grep finds them only in the `export` path and history
- [ ] The 50 KB diff cap no longer applies to any non-`export` review path; no remaining path silently shortens reviewer-visible evidence
- [ ] `export` still embeds; the artifact-unchanged hash still binds spec+tasks+diff bytes and its tests pass unchanged
- [ ] `_gather_review_diff_capped`'s docstring/body mismatch resolved
- [ ] Unresolvable range or missing spec/task path fails LOUDLY, never a silent empty review
- [ ] `test_prompt_text_pinned` green with same-commit hash updates + rationale; reached-path evidence recomputed
- [ ] Focused suites green; propagation done (cp + sync-codex twice, no second-run diff)

## Done summary
Review prompts now carry identities, and the layer that existed to make payloads fit is gone.

**The swap.** `<diff_content>` → `<diff_range>` (a `base..head` range plus the command to read it); `<spec>` / `<task_specs>` → repo-relative paths; `--stat` → `--numstat --no-renames -z`. `<changed_files>` and `<context_hints>` stay — they are what keeps fetching targeted. The reviewer runs in the checkout with a shell and reads what it needs at whatever depth each hunk warrants.

**Why the scope signal mattered most.** The whole model rests on `<changed_files>` being complete and resolvable, and git abbreviates in three independent ways — each found by running the real command, not by reasoning: `--stat` elides with an ellipsis (51 of 65 paths on the fn-168 diff; 28 of 43 on this spec's own), plain `--numstat` collapses renames into `{old => new}` so neither real path appears, and without `-z` any non-ASCII path is C-quoted (`"w\303\251ird na me.txt"`). All three are the same defect: a path the reviewer cannot open is evidence it will never read.

**What got deleted** (~695 lines): the three cursor fitters, `_cursor_disk_read_header`, the ratchet's per-item char budget, the legacy prose 8000-char cap, the 50 KB diff cap, eight argv content constants, the three reviewer-facing "truncated to fit" markers, both impl prompt builders (their only difference was fitting), `_dispatched_diff_from_prompt`, and fn-168's interim cursor sweep gate — the last retired by construction rather than gated, since every backend now renders every prior item.

**What deliberately survived.** `CURSOR_ARGV_PROMPT_MAX` → `CURSOR_ARGV_TRANSPORT_MAX`: it was doing double duty as content budget and as `run_cursor_exec`'s fail-closed boundary, and the Windows `CreateProcessW` limit does not disappear because we stopped embedding. It refuses loudly; it never trims. `_render_structured_prior_finding` also survived, against the task's original plan: a reviewer's own prior findings live in the receipt, not the tree, so there is nothing to fetch — they are the one payload with no identity, and `.3` made injection a live fallback that deleting the renderer would have blinded.

**Fail loudly, never quietly.** A failed `git` read raises `ReviewEvidenceError` with git's own stderr and aborts before a round is reserved; a genuinely empty range still returns empty, because failure and "nothing changed" must not collapse. The artifact identity is the complete diff at the frozen range, streamed under a 64 MiB ceiling that RAISES rather than truncating — a truncated identity collides with any diff sharing its prefix, which the unchanged-artifact guard reads as "nothing changed". Task enumeration comes from the canonical JSON, so a task with no readable markdown aborts instead of being invisible to both prompt and hash.

**Measured** (`optimization/reached-path/evidence/fn169/prompt-identity-delta.json`, this spec's own review range): impl-review prompt 70,243 → 11,824 bytes, −83.17%.

**Six review rounds, twelve findings, all real.** Two-phase dispatch was wired to only one of three handlers; `--numstat` abbreviated renames; `smoke_test.sh` was left on the removed signature; a failed git read was still silent; the helper was duplicated five times; the identity read had become unbounded; the eval payload landed after the rubric and changed recency; the host workflows contradicted their own new paragraph; the impl rubric stopped telling the reviewer to read the spec; docs overclaimed "all review kinds"; C-quoting; and the task glob. One finding was disputed and withdrawn — "identity targets are mutable mid-review" was classified `introduced`, but the plan/completion hashes read spec contents at dispatch exactly as they did before (`git show 511a23ee`), reviewers already read mutable current state, and the impl identity actually got *stronger* by becoming snapshot-addressed. Terminal round: SHIP, 0 findings, R3 and R4 met.
## Evidence
- Commits: d2c76a44, e06c076c, 755e5e1c, cc3b4e57, e8b7f8d1, 387bbd7a
- Tests: python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., bash plugins/flow-next/scripts/smoke_test.sh (135 pass; 1 pre-existing copilot re-review failure, identical on origin/main)
- PRs: https://github.com/gmickel/flow-next/pull/296