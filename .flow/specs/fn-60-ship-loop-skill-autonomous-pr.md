## Conversation Evidence

> user: "add a second loop that does the resolving, waiting for comments, fixing bla bla and eventually merging and releasing?"
> user: "fully autonomous, its a sep skill right, so no risk, ppl dont have to run it. ci green, or fix ci, wait for automated reviewers, max time 30mins, then fix if valid etc, that in a loop until no new reviews come in"
> user: "whatever is defined in the actual project, the agent will pick this up automatically, so we would put something like follow this project's release instructions if they exist, otherwise just merge"
> user: "perhaps we add a new merge-pr skill for dealing with conflicts if necessary"

## Goal & Context
<!-- Source: 65% [user] / 25% [paraphrase] / 10% [inferred] -->

A cadence-driven (`/loop`-shaped) babysit loop — **opt-in and fully autonomous, a separate skill** so projects that don't run it carry zero risk. For each open PR the build-loop authored, it keeps CI green, waits for automated reviewers, resolves valid feedback, and once converged merges and (if the project defines a release process) releases. Where the build-loop is `/goal`-shaped (drains then stops), this is `/loop`-shaped — wakes on a cadence, acts on PRs, sleeps.

## Architecture & Data Models
<!-- Source: 60% [user] / 30% [paraphrase] / 10% [inferred] -->

Per cadence tick, for each open PR the loop authored:

1. **CI** — `gh pr checks`: red → diagnose + fix + push (report `FIXING_CI`); green → continue.
2. **Reviews** — wait for automated-reviewer threads within a ~30-minute patience window; none yet & PR younger than window → report `AWAITING_REVIEW` (next tick re-checks).
3. **Resolve** — new valid threads → `/flow-next:resolve-pr` (fix-verify-reply-resolve).
4. **Converge** — repeat 2–3 until a tick finds no new reviews.
5. **Merge** — CI green + an approving automated review + threads addressed → flip the build-loop's draft PR to ready (`gh pr ready` — pilot's PRs are born draft) and `gh pr merge`, autonomously; then `flowctl spec close` on the spec — land is the pipeline terminus, and closing prevents the build-loop from re-selecting a merged spec.
6. **Release** — discover + follow the project's own release instructions (RELEASING.md / docs / scripts) if present; otherwise stop at merge. A config toggle (e.g. `land.release`) can disable the release step independently of the rest of the loop.

`resolve-pr` gets a light autonomous touch: under `FLOW_AUTONOMOUS` it skips its needs-human bucket and reports `NEEDS_HUMAN` instead of blocking on a question.

## API Contracts
<!-- scope: technical -->

- **Invocation** `/flow-next:land`, opt-in. [user]
- **Per-PR verdict** `MERGED | RELEASED | FIXING_CI | AWAITING_REVIEW | RESOLVING | BLOCKED | NEEDS_HUMAN`. [paraphrase]
- **Tooling** — `gh pr checks` / `pr view` (review threads + decision) / `pr merge`; honors `FLOW_AUTONOMOUS`. [paraphrase]
- **Merge policy** — CI green + approving automated review + threads addressed (the gate the user specified). [user]

## Edge Cases & Constraints
<!-- scope: technical -->

- ~30-minute patience window for the first automated review; convergence = no new threads since the last resolve. [user]
- Operates only on PRs the build-loop authored — discovered as open PRs whose head branch matches a flow spec's `branch_name` (make-pr bodies embed the spec id as a secondary signal); never arbitrary PRs. [inferred]
- CI-fix attempts are bounded per PR; on exhaustion the PR is durably marked (e.g. a `flow-next:needs-human` label — survives sessions, visible on GitHub), reported `NEEDS_HUMAN`, and skipped on later ticks. [inferred]
- The patience window anchors to the last push, not PR creation — a CI-fix push invalidates prior reviews and restarts the wait. [inferred]
- "Approving automated review" must be a detectable, per-project signal (a bot's APPROVE review or a configured reviewer's clean verdict) — reviewer bots differ in whether they file formal approvals. [inferred]
- If no approving automated review ever arrives and no reviewer is configured, it must **not** merge unreviewed — report `NEEDS_HUMAN`. [inferred]
- Merge conflicts: attempt rebase / resolve; if unresolvable, report `BLOCKED`. [user]
- `resolve-pr` is bounded at its existing 2 fix-verify cycles, then escalates → `NEEDS_HUMAN`. [paraphrase]
- Release is project-specific — no generic primitive; follow discovered instructions or stop. [user]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** A new opt-in skill `/flow-next:land` babysits the open PRs the build-loop authored, on a `/loop` cadence, fully autonomously. [user]
- **R2:** For a PR with red CI it diagnoses + fixes + pushes and reports `FIXING_CI`; with green CI it proceeds. [user]
- **R3:** It waits for automated-reviewer feedback within a ~30-minute patience window, reporting `AWAITING_REVIEW` until reviews arrive or the window elapses. [user]
- **R4:** New valid review threads are resolved via `/flow-next:resolve-pr`; it loops resolve → re-check until no new reviews arrive (convergence). [user]
- **R5:** `resolve-pr` runs autonomously under `FLOW_AUTONOMOUS` — its needs-human cases report `NEEDS_HUMAN` instead of blocking on a question. [paraphrase]
- **R6:** Once CI is green, threads are addressed, and an approving automated review lands, it merges via `gh pr merge` — autonomously. [user]
- **R7:** Merge conflicts are handled (rebase / resolve attempt) or reported `BLOCKED`. [user]
- **R8:** After merge it discovers and follows the project's own release instructions if present; otherwise it stops at merge. [user]
- **R9:** It is opt-in and isolated — a separate skill; projects that don't run it are unaffected, and it touches only PRs it authored (or a configured filter). [user]
- **R10:** Per-PR verdicts are `MERGED | RELEASED | FIXING_CI | AWAITING_REVIEW | RESOLVING | BLOCKED | NEEDS_HUMAN`. [paraphrase]
- **R11:** Docs + flow-next.dev updated — new skill page, both navbars, changelog, command reference, version bump; the auto-merge override is documented. [user]
- **R12:** Before merging, it flips the build-loop's draft PR to ready (`gh pr ready`) once the merge gate is satisfied. [inferred]
- **R13:** After a successful merge it closes the spec (`flowctl spec close`), so the build-loop never re-selects a merged spec. [inferred]
- **R14:** CI-fix attempts are bounded per PR; on exhaustion the PR is durably marked, reported `NEEDS_HUMAN`, and skipped on subsequent ticks. [inferred]

## Boundaries
<!-- scope: business -->

- Auto-merge here **intentionally overrides** the standing "no `gh pr merge` from skills" rule — confined to this one opt-in skill; the build-loop and every other skill keep the no-auto-merge rule. [user]
- **No generic release engine** — the loop follows the project's own release process or stops; it never invents versioning / publish steps. [user]
- It does **not** author PRs (the build-loop does) — it only babysits existing ones. [paraphrase]
- Choosing / authoring specs, planning, implementing — out of scope (build-loop). [paraphrase]
- Human PR review is not required (automated reviewers gate merge); but with no automated reviewer configured it must not merge unreviewed. [user]

## Decision Context
<!-- scope: both -->

`/loop` cadence vs `/goal`: babysitting waits on external events (CI, reviewers) over hours, so it's cadence-driven, not drain-to-completion — hence a separate skill from the build-loop. Fully autonomous + opt-in + isolated is the user's framing: a separate skill means no risk to non-users, and that isolation is what licenses the auto-merge override confined here. Release can't generalize — every project releases differently and flow-next has no generic release primitive — so "follow the project's instructions or stop" is the only honest contract. Depends on fn-59 for the PR-authoring convention it babysits. [strategy:Ralph autonomous mode]

## Strategy Alignment
<!-- STRATEGY.md populated 2026-05-16 -->

- Extends the **Ralph autonomous mode** track to the PR → merge → release tail, gated on CI + an approving automated review (quality-first). [strategy:Ralph autonomous mode]
- No conflict with *"Not working on: built-in CI runners"* — it reads the user's CI (`gh pr checks`) and fixes code; it provides no CI runner. [strategy]
- No conflict with *"Not working on: SaaS"* — merge / release via `gh` + the project's own scripts, all in-repo. [strategy]
- **Cross-platform parity** — sync-codex mirror for the Codex variant. [strategy:Cross-platform parity]

## Requirement coverage

| R-ID | Task |
|------|------|
| R1–R14 | TBD — populate via /flow-next:plan |
