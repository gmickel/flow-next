# Review subsystem: agentic-first — pass identities, not payloads

## Goal & Context
<!-- scope: business -->

Reviews have accreted a prompt-assembly layer that ships the reviewer content it already fetches for itself. The layer is expensive, it silently truncates evidence, and it has been hiding three broken things in the resume path. Measured tonight, on this repo, with all four backends installed:

**The embedded diff is truncated at 50 KB — on every backend, not just cursor.** `_gather_review_diff` caps at 50 000 bytes and appends `... [diff truncated at 50KB]`. The fn-168 PR's own diff is **495 374 bytes**, so every reviewer on it — five impl-reviews, three plan-review rounds, and the completion review that reported "8/8 R-IDs met, no gaps" — **saw ~10% of the diff** and fetched the rest itself. We pay for the payload *and* the fetching.

**The reviewers were already reading from disk anyway.** Observed in this session's codex impl-review transcripts: `flowctl brief`, `rg -n …`, `git status --porcelain=v2 && git diff --stat`, `sed -n '11160,11610p' …`, `cmp`, `shasum`. The rubric even says *"You have full access to read files from the repository"* two lines after declaring the embedded diff "the authoritative 'what changed' signal".

**Three silent defects in the codex resume path** (`cmd = [codex, "exec", "resume", session_id, "-"]` — no flags):
1. **`sandbox: danger-full-access`** on every resumed review (measured from the CLI header). Fresh dispatches pass `--sandbox read-only`; resume passes nothing and inherits ambient `~/.codex/config.toml`. The impl-review skill's own rule: *"never widen the reviewer sandbox: reviewers are read-only by contract."* Every round 2+ in the fn-168 workstream ran with repo write access.
2. **`reasoning effort: medium`** on every resumed review — the `-c model_reasoning_effort` flag is not passed, so round 1 and round 2 of the same review are different-strength reviewers.
3. **`--skip-git-repo-check` missing**, so outside a git repo resume raises `CalledProcessError` and the handler silently falls through to a **fresh session** — `resolution_out["resumed"]` unset, exit 0, output shaped normally. Reproduced: a resumed re-review in a non-git cwd started a new `thread_id` and had no memory of its own prior findings.

Defect 3 is the load-bearing discovery: **the convergence ratchet has been compensating for an unverified resume.** fn-90 diagnosed the review runaway as *"every re-review ordered a FRESH blind review… two identical fresh cursor reviews overlapped on only ~50% of findings, making SHIP statistically near-unreachable"* and fixed it by injecting prior findings into the prompt. The mechanism that actually prevents blind re-review — session resume — was silently failing, so each subsequent spec saw re-reviews losing context and added *more* payload rather than checking the belt.

**This was already decided and shipped once.** fn-74 (flow-next 2.5.0) landed *"All review backends read files from disk — no prompt embedding"*, eval-validated on a planted-bug corpus (`QUALITY=PRESERVED`), and deleted `get_embedded_file_contents` plus the `FLOW_*_EMBED_MAX_BYTES` knobs. Its CHANGELOG explicitly notes cursor *"no longer trips its positional-argv limit on any non-trivial diff."* Then fn-90 (#202) re-added prior findings as prose, and fn-159 (#290) upgraded them to rendered structured items **and built a new fitter for them** (`fit_cursor_rereview_prompt_to_budget`). That fitter is what truncates correctness-bearing evidence, which produced the false-SHIP hole found on fn-168's PR #295: a cursor reviewer shown a subset of priors can truthfully answer `Prior findings: all fixed`, and the sweep applies it to the whole untruncated container.

fn-74 removed the code but left **no executable ratchet**, so the decision was re-litigable by accident. It was re-litigated twice.

## Already established — do NOT re-test or re-research

Everything below was measured on this repo on 2026-08-06 with all four backends installed. Treat it as settled input. Re-anchor on the code locations in each task's Investigation targets, but do **not** re-run these probes, re-derive these numbers, or re-litigate the design:

| Settled fact | Evidence |
|---|---|
| Embedded diff is capped at 50 KB on **every** backend | `_gather_review_diff(max_diff_bytes=50000)` |
| fn-168's own diff = 495 374 B → reviewers saw **~10%** | `git diff <merge-base>..HEAD \| wc -c` |
| Reviewers already read from disk while holding the diff | codex impl-review transcripts: `flowctl brief`, `rg -n`, `git diff --stat`, `sed -n`, `cmp`, `shasum` |
| codex delivers the prompt on **stdin** — no size limit ever | `cmd = [codex, "exec", ..., "-"]`, prompt via `input=` |
| cursor's 30 000 cap derives from Windows `CreateProcessW`; `ARG_MAX` here is 1 048 576 | `COPILOT_ARGV_PROMPT_MAX` comment; `getconf ARG_MAX` |
| Resume **works**: codex (same thread, `resumed=True`), copilot (same sid), cursor on `grok-4.5` (same sid). All three have tool access | direct smoke test via `run_*_exec` |
| cursor's DEFAULT model is quota-blocked on this account; use `grok-4.5` / `composer-2.5` | `ActionRequiredError: You've hit your usage limit` |
| Resumed codex runs `sandbox: danger-full-access` and `reasoning effort: medium` | resumed CLI header, parsed from stderr |
| Resume outside a git repo fails → **silent** fresh session (new `thread_id`, no recall, exit 0) | reproduced with `repo_root` set to a non-git dir |
| **The target design works**: resumed session + zero injection + "I addressed some, `<path>`, re-read and verify" → `Prior finding #1: fixed / #2: not-fixed / #3: fixed`, scored **exactly** by the production `_review_finding_prior_items` | direct smoke test |
| The minimal re-review prompt already exists in `build_rereview_preamble`; the ratchet is prepended to it | source |
| Only cursor passes `max_total_chars`, so only cursor truncates prior items | one call site, in `fit_cursor_rereview_prompt_to_budget` |
| ~594 lines of top-level defs + 8 constants are deletable | per-function line counts in Architecture below |
| fn-74 already shipped no-embed for file contents (eval-validated) and fn-90/#202 + fn-159/#290 re-added payloads | `a7297f9a`, 2.5.0 CHANGELOG, `4b30937d`, `ddcda163` |

**The only things that still need new measurement** are the three Open Questions at the foot of this spec — resume across separate processes, resume after a multi-minute gap, and copilot/cursor equivalents of the codex resume defects (all in `.1`) — plus the `.2` eval corpus, which is new instrumentation rather than a re-check of the above.

## Architecture & Data Models
<!-- scope: technical -->

**The principle: pass identities, not payloads.** The reviewer is an agent with a shell and a checkout. Give it a rubric, what to look at, and the reply grammar. It fetches.

### The minimal prompt already exists

No new prompt design is required. `build_rereview_preamble` already emits exactly the target shape — the ratchet is *prepended* to it:

```
## IMPORTANT: Re-review After Fixes
This is a RE-REVIEW. Code has been modified to address gaps since your last review.
**Updated files:** {files_list}
Re-read these files from the repository … do NOT rely on cached content.
```

RP's workflow carries the same principle in prose (*"Do NOT summarize fixes … Just request re-review. Any summary wastes tokens and duplicates what reviewer already sees"*), though its justification is RP-specific (auto-refresh, a caching workaround). CLI backends fetch **on demand**, so the explicit "re-read from disk" instruction is the correct form for them — and is what the smoke test exercised.

### Validated end to end (measured, not assumed)

Resumed codex session, **zero prior findings embedded**, prompt = *"I addressed some of your findings. Changed file: `<path>` — re-read it from disk and verify"* plus the grammar:

```
Prior finding #1: fixed
Prior finding #2: not-fixed
Prior finding #3: fixed

production parser -> [(1,'fixed'), (2,'not_fixed'), (3,'fixed')]   # exact
```

The reviewer recalled its own numbered findings, refetched, and hit the grammar cold. Scored through the real `_review_finding_prior_items`, not a mock.

### Backend matrix (measured tonight)

| backend | version | resume | tool access | prompt delivery |
|---|---|---|---|---|
| codex | 0.146.1 | works in a git repo (`resumed=True`, same thread) | yes | **stdin** — no size limit at all |
| copilot | 1.0.78 | works (same sid, recall confirmed) | yes (reported real HEAD) | stdin on Windows, argv on POSIX |
| cursor | 2026.08.04 | works (same sid) on `grok-4.5` | yes | **positional argv** — the only true cap |
| rp | 2.1.33 | same-chat, skill-level | Builder-driven | n/a |

Cursor's default model is quota-blocked on this account; `grok-4.5` / `composer-2.5` work. codex taking the prompt on **stdin** means the embedding buys codex nothing but cost — there was never a size failure to prevent there.

### Where the argv cap actually comes from

`CURSOR_ARGV_PROMPT_MAX = COPILOT_ARGV_PROMPT_MAX = 30000`, whose documented origin is *"Windows `CreateProcessW` caps the whole command line at 32768 UTF-16 chars. POSIX is much higher (macOS ~256KB, Linux ~2MB) but we use the same threshold uniformly."* `getconf ARG_MAX` here is 1 048 576. For copilot 30 000 is a **routing threshold** (Windows switches to stdin, which bypasses the cap entirely); cursor inherited the number with no second delivery mechanism, so a routing threshold became a content-truncation ceiling.

### Target shape

| today | becomes |
|---|---|
| `<diff_content>` (50 KB cap) | `<base-sha>..<head-sha>` — the reviewer runs `git diff` |
| `<spec>` (always embedded) | `.flow/specs/<id>.md` |
| `<task_specs>` | the task md paths |
| rendered prior findings + fitter | session resume; receipt path on fallback |
| `<diff_summary>` | **keep** — bounded `--stat`, the cheap scope map |
| `<context_hints>` | **keep** — bounded at 15, genuine starting points |

### Deletion surface (top-level defs, before tests)

`fit_cursor_prompt_to_budget` 68 · `fit_cursor_diff_to_budget` 38 · `fit_cursor_rereview_prompt_to_budget` 89 · `_cursor_disk_read_header` 31 · `build_convergence_ratchet_block` 127 · `_render_structured_prior_finding` 15 · `_neutralize_prior_findings_text` 10 · `_build_impl_prompt_cursor` 42 · the two diff gatherers 19 · the two prior-findings readers 33 · `build_rereview_preamble` 122 (minimal core survives) — **~594 lines**, plus 8 budget constants/markers and their tests.

## Edge Cases & Constraints

- **Host is the deliberate exception.** Host has no session by design (`session_id: null`, *"Every re-review is a fresh subagent — no context reuse, no fabricated resume ids"*), and `workflow-host.md` states the receipt's `review` field is REQUIRED because the ratchet reads it to inject priors into the next fresh subagent. Host keeps injection, tested as an exception so nobody "simplifies" it later.
- **`export` must keep embedding.** An external LLM in a browser has no repo. Keep the diff builder for that one path; it is the only honest embedder.
- **The artifact-unchanged hash is unaffected.** `review-artifact` already reads the diff from `--diff-file`; it keeps hashing spec+tasks+diff bytes and simply stops shipping them. The hash needs the content; the prompt does not. Passing real `<base-sha>..<head-sha>` makes the reviewed range exact and replayable, which *improves* auditability.
- **Resume failure must be loud.** Today it is silent (`resolution_out["resumed"]` unset, exit 0). Once injection is conditional on resume, a silent failure would mean a genuinely blind re-review — so failure has to surface and fall back to injection deliberately.
- **Resume is not universally reliable** and must not be assumed: session expiry, a different machine (`_review_stall_rule`'s own docstring warns a receipt "can be missing, stale, or on a different machine"), a CLI version change. Injection stays as the tested fallback path.
- **Not yet verified, and load-bearing if resume becomes primary:** (a) resume across *separate flowctl processes* (the smoke test made two calls in one Python process); (b) resume after a long gap / on a later day (tested back-to-back, seconds apart); (c) copilot/cursor equivalents of the three codex resume defects.
- **`_gather_review_diff_capped`'s docstring lies** — it claims "50KB hard cap + truncation marker" while its body is a bare passthrough; the cap moved into the callee and the docstring did not follow. Fix or delete with the rest.
- **Prompt text is hash-pinned.** `test_prompt_text_pinned` will fail on rubric edits; update hashes in the same commit with rationale, per CLAUDE.md.
- **`optimization/reached-path` route evidence shifts** when skill prose changes; recompute from the live measurement rather than leaving it stale.
- **Reviewers seeing 100% instead of 10% of the diff will surface more genuine findings.** That is correct behavior, and the volume is tunable via the impl-review prompt — an eval-later concern, explicitly not a blocker for this spec.

## Quick commands
```bash
# Focused suites
cd plugins/flow-next/tests && python3 -m unittest test_review_convergence_cap test_review_findings_parser test_review_findings_receipts test_prompt_text_pinned test_backend_spec -q
# Eval harness
cd optimization/review-prompt && REVEVAL_RUNS=3 python3 reveval.py
```

## Acceptance Criteria
<!-- scope: both -->

- **R1:** The codex resume dispatch passes the same guarantees as a fresh dispatch: `--sandbox <resolved>`, the configured reasoning effort, and `--skip-git-repo-check`. Verified by asserting the resumed CLI header reports the intended sandbox and effort (measured today: `danger-full-access` / `medium`). Errors: a resume that still fails must **surface** — set an explicit signal, log it, and fall back to injection deliberately; never silently start a fresh session. Copilot and cursor resume paths audited for the same three defect classes and fixed where present.
- **R2:** Prior-finding **injection happens only when the session did not resume.** Host always injects (no session by design). codex/copilot/cursor inject only on a surfaced resume failure. A resumed re-review contains no rendered prior items. Errors: resume-failure fallback is exercised by a test that forces failure and asserts injection returns; a resumed round with no injection still parses per-ordinal statuses through the production parser.
- **R3:** Payloads become identities. `<diff_content>` → `<base-sha>..<head-sha>`; `<spec>` → the spec path; `<task_specs>` → task paths. `<diff_summary>` and `<context_hints>` are retained. `export` keeps embedding; the artifact hash is unchanged and still binds spec+tasks+diff bytes. Errors: a reviewer given an unresolvable range fails loudly rather than reviewing an empty diff; an absent spec/task path is an error, not a silent omission.
- **R4:** The truncation layer is deleted — all three cursor fitters, `_cursor_disk_read_header`, the ratchet's item renderer, the 50 KB diff cap for non-`export` paths, and the review-side argv constants/markers. `grep` for the budget constants returns hits only in the `export` path and history. Errors: no remaining code path silently shortens reviewer-visible evidence.
- **R5 (eval-gated):** The eval harness gains a **git-fixture corpus with scope traps** — planted issues across several files, a decoy changed *before* base, a decoy changed *after* head, a bug in an unchanged region of a changed file, and a rename — plus metrics the current corpus cannot express: `verdict_delivered`, `range_correct` (read from the reviewer's own `command_execution` stream), turns-to-verdict, scope precision, and resumed re-review per-ordinal grammar compliance scored through the production parser. Baseline measured before the change, re-measured after, both recorded in `agent_docs/optimization-log.md`. **Pre-registered gate:** ship only if `verdict_delivered` = 100%, `range_correct` = 100%, scope precision = 1.0, correctness-class detection ≥ baseline, prior-ordinal compliance ≥ baseline, and prompt tokens down. Wall-clock is recorded, not gated. Any missed verdict or decoy finding blocks the ship regardless of token win.
- **R6 (the ratchet fn-74 omitted):** Three enforcement layers, because prose alone already failed twice. (a) `STRATEGY.md` records the principle — pass identities, not payloads; the reviewer is an agent with tools. (b) `CLAUDE.md`'s "How to spot a mistake" list gains the planning-time trip-wires: *embedding content the reviewer could fetch itself*, *writing a fitter/truncator for a prompt payload*, *adding a budget constant to a prompt path*. (c) An **executable test** asserts the built review prompt (non-`export`) contains no diff body, no spec body, and no rendered prior items. Errors: the test names the offending tag so a future regression is self-explaining.
- **R7:** Docs + CHANGELOG. `docs/orchestration.md`, `docs/flowctl.md`, `docs/review-findings.md`, and the three `workflow-host.md` files reflect fetch-not-embed and the host exception; the codex mirror is regenerated (`sync-codex.sh` twice, no second-run diff). CHANGELOG `## Unreleased`, outcome-first. **No release until this spec AND fn-168 have both landed** — the two entries ship together. No version bump inside the spec.

## Boundaries
<!-- scope: business -->

- **Host keeps prior-finding injection.** Not an oversight; it has no session. Tested as an exception.
- **`export` keeps embedding.** No repo access, so the payload is the only channel.
- Not a change to the artifact-unchanged guard, the round cap, reservation/refund, the findings container/lineage schema, the digest, or the stall rule — fn-168 owns those and they are unaffected.
- Not a rewrite of the review rubric content. The rubric is eval-optimized (fn-74); only the payload/pointer sections change.
- Not an attempt to reduce round *counts*. Expect less re-derivation but possibly more legitimate findings once reviewers see the whole diff at full effort. Round count is a measured outcome, never a promise.
- Not a change to `<diff_summary>` or `<context_hints>` — both are bounded and earn their place.
- Not tuning finding volume via the impl-review prompt; that is a follow-up eval.

## Strategy Alignment

Active tracks served:
- **Agentic-first architecture** — CLAUDE.md's rule is *"the host agent IS the intelligence"* and its symptom list already flags deterministic scaffolding that substitutes for agent capability. Review is the subsystem where flow-next still does not act like it: it hands an agent-with-a-shell a truncated copy of what the agent can read. This spec closes the last big gap and, via R6, makes the principle enforceable rather than advisory.
- **Ralph autonomous mode** — resume defects mean autonomous re-reviews run at the wrong sandbox, the wrong effort, and sometimes with no memory. Fixing them makes unattended review loops trustworthy.

## Decision Context

**Why identities rather than a better fitter.** The rendered-ordinal plumbing considered for PR #295 was machinery to prop up the payload model; it is ~the same effort as deleting the model and it would need unwinding afterwards. Under identities the false-SHIP class disappears rather than being managed: prior findings are the reviewer's own memory (or a receipt path), so nothing competes for argv space.

**Why the resume fix ships first and separately.** `danger-full-access` on every resumed review is live today and independent of the rest. It is also the cheapest change with the largest safety payoff, and it is a prerequisite for making injection conditional.

**Why speed is expected to improve, not regress.** The turn cost of fetching is already being paid — reviewers fetch today *because* the diff is truncated to 10%. Removing the payload deletes overhead from a path that fetches regardless. The only case that could add round-trips is a diff that fits entirely under 50 KB; fn-74's "~64 file-reads for a verdict on a 49-file diff" was recorded as a pass in the no-embed world, not a warning.

**Why an eval at all, given fn-74 already proved no-embed.** fn-74 proved it for file *contents*. The diff is the **scope** signal, and embedding was originally introduced to prevent a "114 turns / no verdict" failure — a scope-bounding failure. The existing corpus is a single file with no git history, so it structurally cannot fail that way and would pass while the real risk went unmeasured. Hence the fixture with decoys.

**Why three enforcement layers.** fn-74 made this exact decision, validated it, deleted the code, and wrote it in a CHANGELOG. It was reversed twice by specs that each had a good local reason. A CHANGELOG entry is not a constraint; a failing test is.

## Early proof point

Task `.1` (resume argv fix) is independently valuable and independently shippable: it closes a live read-only-contract violation and can be verified by asserting the resumed CLI header. If resume turns out to be unreliable across processes or after a gap (the unverified cases above), that is discovered here — before any work depends on resume being the primary continuity mechanism, and while injection is still unconditional.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1 | Resume argv parity + loud failure; copilot/cursor audited | .1 | — |
| R2 | Injection only when resume did not happen; host always | .3 | — |
| R3 | Payloads → identities; export + hash preserved | .4 | — |
| R4 | Truncation layer deleted | .4 | — |
| R5 | Eval fixture, metrics, baseline + post measurement, pre-registered gate | .2 (harness + baseline), .5 (re-measure + gate) | split so the baseline exists before the change |
| R6 | STRATEGY.md + CLAUDE.md symptoms + executable no-embed test | .6 | — |
| R7 | Docs + CHANGELOG + mirror + full gate | .6 | — |

## References

- `plugins/flow-next/scripts/flowctl.py` — `run_codex_exec` resume branch (~:4353, the three missing flags + the silent `CalledProcessError` fallthrough), fresh dispatch (~:4398), `_gather_review_diff` (50 KB cap + marker), `_gather_review_diff_capped` (stale docstring), `build_review_prompt` (~:9599, the five payload slots), `build_rereview_preamble` (~:11934, the minimal prompt already present), `build_convergence_ratchet_block`, `_render_structured_prior_finding`, `fit_cursor_prompt_to_budget` / `fit_cursor_diff_to_budget` / `fit_cursor_rereview_prompt_to_budget`, `CURSOR_ARGV_PROMPT_MAX` / `COPILOT_ARGV_PROMPT_MAX` (~:8491, the Windows-derived 30 000), `BACKEND_REGISTRY` resume_modes (codex ~:40364, copilot ~:40384, cursor ~:40404), the cursor dispatch that resumes *and* injects (~:40583)
- `plugins/flow-next/skills/flow-next-impl-review/workflow-host.md` — host's no-session contract (~:11, ~:165); `workflow-rp.md` — the do-not-summarize principle (~:636)
- History: `a7297f9a` / flow-next 2.5.0 CHANGELOG (fn-74 no-embed, eval-validated, knobs deleted) · `4b30937d` #202 (fn-90 ratchet) · `ddcda163` #290 (fn-159 structured prior items + the re-review fitter)
- Eval: `optimization/review-prompt/README.md` (method), `reveval.py` (runner/scorer), `orders.py` / `orders_clean.py` (corpus + over-flag), `agent_docs/optimizing-skills.md`, `agent_docs/optimization-log.md`
- Measurements (2026-08-06, this repo): fn-168 diff 495 374 B vs the 50 000 B cap → ~10% visible; resumed codex header `sandbox: danger-full-access`, `reasoning effort: medium`; resume outside a git repo → new `thread_id`, no recall; resumed re-review with zero injection → production parser exact match; `getconf ARG_MAX` = 1 048 576
- Coordination: fn-168 (PR #295 — its interim cursor sweep gate is deleted by this spec's R2/R4; **no release until both land**), fn-166 (flowctl module split — extracts this region; sequence after)

## Open Questions

- **Finding volume once reviewers see 100% of the diff.** Expected to rise. Tunable via the impl-review prompt (severity thresholds, blocking calibration) and deliberately deferred to a follow-up eval rather than pre-emptively damped here.
- **Does resume survive a long gap and separate processes?** Verified only back-to-back within one process. `.1` establishes it; if it does not hold, injection stays unconditional for the affected backend and R2 narrows to host-plus-that-backend.
- **Should `rp` converge on the same identity model?** RP's Builder-driven selection already avoids payload embedding by a different route. Left alone unless the eval shows a parity gap.
