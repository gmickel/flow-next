---
satisfies: [R1, R6]
---
# fn-169-review-subsystem-agentic-first-pass.1 Resume dispatch parity: sandbox, effort, git-check — and loud failure

## Description
Give the resume path the same guarantees as a fresh dispatch, and stop it failing silently. Independently shippable — this closes a live read-only-contract violation and is the spec's early proof point.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py` (`run_codex_exec` resume branch ~:4353; the copilot/cursor exec paths), `plugins/flow-next/tests/` (new resume-parity tests), `.flow/bin/flowctl.py` (propagation)

### Approach
- The resume argv is `cmd = [codex, "exec", "resume", session_id, "-"]` — no `--sandbox`, no `-c model_reasoning_effort`, no `--skip-git-repo-check`. Measured consequences on this machine: a resumed review reports `sandbox: danger-full-access` (inherited from ambient `~/.codex/config.toml`) and `reasoning effort: medium` instead of the configured value.
- Pass all three, mirroring the fresh `_dispatch` branch (~:4398). The resumed session's MODEL is fixed by the original dispatch and must NOT be re-pinned (PR #203 r2 already handles that via `resolution_out["resumed"]`) — only sandbox, effort and the repo-check flag are being restored.
- **Make failure loud.** Today `except subprocess.CalledProcessError: pass` falls through to a fresh session with `resolution_out["resumed"]` unset, exit 0, normal-looking output — so a blind re-review is indistinguishable from a resumed one. Set an explicit signal (e.g. `resolution_out["resume_failed"]` + the reason) and log to stderr. Do not change the fallback BEHAVIOUR in this task — unconditional injection still covers it; `.3` is what makes the signal load-bearing.
- Audit the copilot (`--session-id` / `--resume`, marker-tracked) and cursor (`--resume`, resume-only, `require_nonempty_sid`) paths for the same three defect classes and fix what applies. Cursor takes no effort flag by design.
- **Verify the unverified cases while you are here** (spec Open Questions): does resume survive (a) separate flowctl processes, and (b) a gap of minutes rather than seconds? Record the answers in the done summary — `.3` depends on them.
- Propagation: `cp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py`.

- **Land the strategic guardrails IN THIS TASK, before any review round of `.3`/`.4`.** This spec is mostly DELETION, and a reviewer with no stated constraint will argue deterministic machinery back in — that is exactly how fn-90 and fn-159 re-accreted what fn-74 removed. Two edits, both small:
  - `STRATEGY.md` — the principle: **pass identities, not payloads; the reviewer is an agent with a shell and a checkout.** Use `/flow-next:strategy`.
  - `CLAUDE.md`'s **"How to spot a mistake"** list — the planning-time trip-wires, which is the section agents actually read before designing: *embedding content the reviewer could fetch itself*; *writing a fitter/truncator for a prompt payload*; *adding a budget constant to a prompt path*. Three or more → convert to identities.
  Landing these here means every subsequent review round is reading the constraint rather than inventing against it. `.6` keeps the executable test, docs, CHANGELOG and the gate.

### Investigation targets
**Required:**
- `plugins/flow-next/scripts/flowctl.py` ~:4340-4420 — the resume branch and the fresh `_dispatch` it must match
- `run_copilot_exec` / `run_cursor_exec` — the sibling resume paths
- `BACKEND_REGISTRY` resume_modes: codex ~:40364, copilot ~:40384, cursor ~:40404

**Optional:**
- `plugins/flow-next/skills/flow-next-impl-review/SKILL.md` — the read-only reviewer contract this restores

### Key context
- **The three defects are ALREADY MEASURED** (spec § Already established): `danger-full-access`, `medium`, and the silent non-git fallthrough. Do NOT re-probe them to confirm — go straight to the fix and pin each with a regression test. The only NEW measurement in this task is resume across separate processes and after a multi-minute gap.
- The reviewer read-only contract is stated in the impl-review skill: "never widen the reviewer sandbox: reviewers are read-only by contract, so a sandbox-blocked reviewer means something asked it to mutate the workspace." Resumed reviews have been violating it.
- Every round 2+ review in the fn-168 workstream ran under `danger-full-access`. This is live, not theoretical.
- Do NOT make injection conditional here — that is `.3`, and it must not land before resume is trustworthy.

## Acceptance
- [ ] Resume passes `--sandbox`, the configured reasoning effort, and `--skip-git-repo-check`; a test asserts the resumed CLI header reports the intended sandbox and effort (regression target: `danger-full-access` / `medium`)
- [ ] The resumed session's model is still NOT re-pinned (the `resumed` resolution contract is preserved)
- [ ] Resume failure is SURFACED: an explicit signal plus a stderr line; a test forces failure (non-git cwd) and asserts the signal is set rather than a silent fresh session
- [ ] Fallback behaviour unchanged in this task — injection is still unconditional
- [ ] copilot and cursor resume paths audited for the same three defect classes; fixes applied where they apply, with the audit result stated in the done summary
- [ ] Resume verified across separate flowctl processes AND after a multi-minute gap; both results recorded in the done summary
- [ ] `STRATEGY.md` records the identities-not-payloads principle
- [ ] `CLAUDE.md`'s "How to spot a mistake" list gains the three planning-time trip-wires
- [ ] Focused suites green; propagation done (cp flowctl.py to .flow/bin)

## Done summary
Restored resume-dispatch parity with the fresh path, made resume failure visible, and landed the strategic guardrails early so later review rounds read them.

**The three defects, all measured before and after.** `codex exec resume` was invoked with none of the fresh dispatch's flags:
- **`sandbox: danger-full-access`** on every resumed review — inherited from ambient `~/.codex/config.toml` — against the impl-review skill's own rule that reviewers are read-only by contract. Now `read-only`.
- **`reasoning effort: medium`** instead of the configured value, so round 1 and round 2 of the same review were different-strength reviewers. Now tracks the pin (verified at `xhigh`).
- **`--skip-git-repo-check` missing**, so outside a git repo resume raised `CalledProcessError` and the handler silently fell through to a FRESH session — fn-90's runaway root cause, reachable with no signal at all.

**Not `--sandbox`.** `codex exec resume` has no such flag (verified against 0.146.1 `exec resume --help`); passing one makes resume exit non-zero. The first draft of this fix did exactly that and silently reintroduced the bug it was fixing — caught by the loud-failure signal the same change had just added, plus a live check. Sandbox therefore rides `-c sandbox_mode=`. The model is deliberately **not** re-pinned: a resumed session keeps its original.

**Resume failure is now loud** — `resolution_out["resume_failed"]` plus a reason plus a stderr warning. Fallthrough behaviour is unchanged; `.3` is what makes the signal load-bearing.

**Sibling audit: only codex was affected.** cursor and copilot build ONE flat argv where the session flag is just another entry, so nothing can be dropped — cursor's `--mode ask` (read-only) and `--model` both survive resume, pinned by `test_cursor_resume_drops_no_flags`. codex was the outlier because `exec resume` is a separate subcommand with its own flag set. **Observation, out of scope here:** copilot passes `--allow-all-tools` on *both* paths — same "reviewer exceeds the read-only contract" class, but not a resume-parity defect. Worth its own look.

**Both spec Open Questions resolved by measurement**, recorded durably at `optimization/reached-path/evidence/fn169/resume-parity-live.json`: resume works from a **separate process**, **more than ten minutes** after session creation, with recall intact and the header still reporting `read-only` / `xhigh`. `.3` can treat resume as the primary continuity mechanism.

**Guardrails landed here by design**, so every review round of `.3`/`.4` reads the constraint instead of inventing against it:
- `STRATEGY.md` — extended the existing **"The artifact is the contract"** principle rather than inventing a new one, because the rule already existed and the reviewer was simply exempt from it. Names identities-not-payloads, the fitter-is-a-symptom rule, and the fn-74 → fn-90 → fn-159 re-accretion history as the argument.
- `CLAUDE.md` **"How to spot a mistake"** — three planning-time trip-wires: embedding fetchable content; writing a prompt-payload fitter/truncator/budget; enumerating ways-to-do-it-wrong instead of placing the invariant where it is true by construction.

**Review rounds (3, all findings valid).** r1: tests called the real `require_codex`/`require_cursor` so they errored on any host without the CLIs (CI installs neither) — both now mocked, verified by hiding both binaries from `PATH` with the same interpreter. r1 also caught my argv test asserting against an **allowlist of codex's option surface** — the exact enumeration anti-pattern this diff added to CLAUDE.md, and already incomplete (it omitted `--config`); deleted in favour of asserting this implementation's invariant. r2: refused my live measurements because they lived only in the session transcript, not the repo — hence the committed artifact.

Implementation note: the code half of this task was first drafted by grok-4.5 via the cursor bridge. It produced the right shape but invented the `--sandbox` flag, and its hermetic tests passed against argv the CLI rejects. Live verification caught it; subsequent work was done directly.
## Evidence
- Commits: c9733dac, fac6e98e, fd494188
- Tests: python3 scripts/run_tests_parallel.py  (182 files, 4236 tests, 0 failures, 0 errors, 5 skipped), uvx ruff@0.16.0 check .  (All checks passed), portability: codex + cursor-agent hidden from PATH, same interpreter -> TestCodexResumeArgvParity 3/3 OK, live evidence: optimization/reached-path/evidence/fn169/resume-parity-live.json — resumed header sandbox=read-only effort=xhigh (was danger-full-access/medium), same session, recall intact, separate process, >10min after creation, sibling audit: test_cursor_resume_drops_no_flags — cursor resume drops no flags, flowctl codex impl-review fn-169-review-subsystem-agentic-first-pass.1  (r1 NEEDS_WORK 2xP1+1xP3; r2 NEEDS_WORK 1xP1 evidence-not-in-repo; r3 VERDICT=SHIP, receipt /tmp/impl-review-fn-169-1.json, gpt-5.6-sol)
- PRs: