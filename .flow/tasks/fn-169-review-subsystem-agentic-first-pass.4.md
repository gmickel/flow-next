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
- **Delete** the content-fitting layer: `fit_cursor_prompt_to_budget`, `fit_cursor_diff_to_budget`, `fit_cursor_rereview_prompt_to_budget`, `_cursor_disk_read_header`, `_render_structured_prior_finding`, `_neutralize_prior_findings_text`, `_build_impl_prompt_cursor`, the ratchet's item rendering, the 50 KB diff cap for non-`export` paths, and the review-side argv constants/margins/markers (~594 lines of top-level defs plus 8 constants).
- **`export` keeps embedding** — no repo access, so the payload is its only channel. Keep the diff builder for that path only.
- **The artifact hash is unchanged**: `review-artifact` already reads the diff from `--diff-file`, so it keeps hashing spec+tasks+diff bytes and simply stops shipping them. Passing real `<base-sha>..<head-sha>` makes the reviewed range exact and replayable.
- Fix or delete `_gather_review_diff_capped`, whose docstring claims "50KB hard cap + truncation marker" while its body is a bare passthrough.
- `test_prompt_text_pinned` will fail — update hashes in the same commit with rationale (CLAUDE.md sanctions a deliberate prompt change). `optimization/reached-path` route evidence will shift; recompute from the live measurement.
- Propagation: `cp` flowctl.py, `./scripts/sync-codex.sh` TWICE (no second-run diff).

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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
