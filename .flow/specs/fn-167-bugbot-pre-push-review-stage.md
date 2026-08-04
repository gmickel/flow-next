# fn-167-bugbot-pre-push-review-stage Bugbot pre-push review stage

## Goal & Context
<!-- scope: business -->

Agent-driven build loops re-trigger PR review on every push. Measured on a real
16-repo portfolio over 30 days: 502 review submissions across 150 PRs, a mean of
**3.3 reviews per PR**, with individual PRs reaching 29, 20 and 18 review runs as
the land loop pushed fix commits. That multiplier is invisible under a per-seat
reviewer and brutal under a per-review-priced one.

Cursor Bugbot is per-review priced (roughly $1.00-1.50/run, usage-based since the
May 2026 change), and on **Individual** plans it "bills from included usage",
i.e. the same pool as agent and coding requests. So on the Individual tier every
Bugbot run is a direct tax on build capacity, and a flow-next land loop at the
measured cadence exhausts a Cursor Pro pool many times over. Users hit the wall
and turn Bugbot off, which is the rational response and also a lost review lane.

Bugbot ships a mechanism that fixes this, and nothing else in the field has an
equivalent. Running `/review-bugbot` from the agent stores the
[patch ID](https://git-scm.com/docs/git-patch-id) of the reviewed diff; when
Bugbot on the connected SCM later sees a diff with the same patch ID it **skips
the review** and comments that it already reviewed that diff.

flow-next's pipeline produces the dedup precondition for free. `work` loops until
SHIP, so the final review runs against the final diff, which is precisely the diff
`make-pr` pushes. Both systems are built around "review the diff you are about to
ship", so they line up without an adapter.

The value is a **relocation, not an addition**: the same review, moved from after
the PR to before it. Review count is unchanged, findings land inside the loop
where the worker can still act on them without a PR round-trip, and on a
per-review-priced reviewer the team stops paying twice for one diff.

Target user: flow-next users running the Cursor host who pay for Bugbot. For them
the recommended shape becomes Bugbot pre-push plus a second, different-family
reviewer on the PR (Codex), which is also what the cross-model review evidence
argues for -- models are measurably worse at reviewing their own output.

## Architecture & Data Models
<!-- scope: technical -->

A new **opt-in pilot stage**, `prepush-review`, positioned between `qa` and
`make-pr`:

```
plan -> plan-review -> work -> [qa] -> [prepush-review] -> make-pr
```

**Position is the whole feature.** The patch ID must survive to the SCM
untouched, so the stage has to be the last thing before the push. Any stage that
commits downstream of it silently breaks the dedup: the team pays twice and
nothing reports it. That is why this is not a backend of an existing review
skill:

- `impl-review` is the **inner loop** -- per-task, iterative, scoped by
  `BASE_COMMIT`/`TASK_ID`. The patch ID reviewed at task 3 is dead by task 7.
- `spec-completion-review` sits at the all-tasks-done juncture but **upstream of
  `qa`**, so it is correct only by accident of `qa` currently being advisory and
  non-committing.

**Single-purpose, not backend-split.** Bugbot is a product, not a model: it
brings its own review logic, its own rules system (`.cursor/BUGBOT.md`), and its
own findings format. flow-next authors no prompt, pins no model, and sets no
effort spec. The `impl-review` backend abstraction exists precisely because that
skill *is* generic -- flow-next writes the prompt and each backend is a different
model to run it through, which is what forces `model-pins.md`,
`model-routing-*.md`, the per-backend workflow files and per-backend receipt
mapping. None of that machinery buys anything here.

The generic capability is also already available: `impl-review` with `BASE_COMMIT`
absent falls back to main/master for a **full branch review**. "Whole-diff review
before push, any host, choice of model" is buildable today. The only genuinely new
thing is the patch-ID dedup, and that is Bugbot-only.

**Host scope.** Cursor host driver only. The `/review-bugbot` skill is reachable
when flow-next *is* the Cursor agent. It is not reachable through headless
`cursor-agent -p` (the existing `cursor` review backend transport) until Cursor
ships CLI support for the skill. Host-conditional capability is already modelled
in this repo in the opposite direction: the Cursor plugin manifest records that
Ralph autonomous mode "is available on other hosts; intentionally not registered
on Cursor".

**Gate.** `pipeline.prepushReview`, default **off**, same gate-reversed,
strict-scalar shape as fn-72's `pipeline.qa`. It reads from the tick's existing
root config snapshot, never a second `config get` call.

**Findings are advisory in v1.** They surface, they never block, mirroring the
`qa` precedent where `NEEDS_WORK` still advances to the draft PR.

## API Contracts
<!-- scope: technical -->

**Config**

- `pipeline.prepushReview` -- strict scalar string enum `on` | `off`. Default
  `off`. Any other value (`true`, `null`, a typo) leaves the stage off and pilot
  behaviour byte-for-byte unchanged. Set via
  `flowctl config set pipeline.prepushReview on`.

**Pilot**

- Stage enum gains `prepush-review`. `PILOT_VERDICT` stage values become
  `plan`, `plan-review`, `work`, `qa`, `prepush-review`, `make-pr`, `land`, `-`.
- Dispatched only when `pipeline.prepushReview == on` **and** the host is the
  Cursor driver. With either false, the stage is forbidden and the stage set is
  byte-for-byte unchanged.
- Autonomy-safe: advances on every outcome. `CLEAN` and `ADVISORY` advance;
  `BLOCKED` advances to `make-pr` and surfaces the reason. The stage never hard-
  blocks the loop and never asks a question.

**Receipt** (written to the existing review-receipts location)

```json
{
  "type": "prepush_review",
  "id": "<spec-id>",
  "reviewer": "bugbot",
  "verdict": "CLEAN|ADVISORY|BLOCKED",
  "patch_id": "<git patch-id>",
  "head_sha": "<sha at review time>",
  "findings": [{ "severity": "...", "path": "...", "line": 0, "summary": "..." }],
  "findings_visible_on_pr": true,
  "timestamp": "..."
}
```

`findings_visible_on_pr` records whether Bugbot surfaced the findings on the PR
itself. Task 1 determines the real value; `make-pr` only needs to carry findings
into the PR body when it is `false`.

**Invocation**

- Host-native skill call to `/review-bugbot`. Not a shell-out, not a
  `flowctl cursor` wrapper, not `cursor-agent -p`.
- Reviews the branch diff against the spec branch's base.

**HEAD assertion**

- Pilot's existing verify step asserts `git rev-parse HEAD` is unchanged between
  the `prepush-review` receipt's `head_sha` and `make-pr`'s push. A mismatch
  means the dedup will not fire; emit a warning into the make-pr output rather
  than failing the tick.

## Edge Cases & Constraints
<!-- scope: technical -->

- **Patch-ID invariant 1 (no commits before push).** Anything that commits
  between the stage and `make-pr`'s push (a lint fix, a changelog line, anything
  make-pr adds) changes the patch ID and silently kills the dedup. Enforced by
  the HEAD assertion above, which turns a diffuse "do not commit anywhere"
  constraint into a single checkable adjacency rule.
- **Patch-ID invariant 2 (clean tree at review time).** `/review-bugbot` reviews
  branch changes *including uncommitted* by default, which would produce a patch
  ID that never matches the committed diff that gets pushed. Under pilot this is
  already guaranteed: pilot refuses to run on a dirty working tree at tick start.
  The user-invoked path must not inherit that assumption -- check explicitly.
- **Non-Cursor host.** Clean skip, never an error, never a `NEEDS_HUMAN`.
- **Bugbot not installed, not authed, or rate-limited.** `BLOCKED` verdict plus a
  clean advance to `make-pr`. Never a hang, never an interactive prompt under
  autonomy.
- **Usage cost.** Every invocation consumes Cursor usage; on Individual plans
  from the pool shared with coding. The stage is off by default for that reason,
  and the docs must state it rather than burying it.
- **Churn non-goal (load-bearing).** No fix loop in v1. An unbounded fix loop on
  a per-review-priced reviewer rebuilds the exact 3.3x multiplier this feature
  exists to remove, inside flow-next. If a loop is ever added it is hard-bounded
  (land's bounded-fix-budget precedent), never loop-until-SHIP.
- **Findings visibility is unverified.** The docs say `/review-bugbot` reviews
  "stay in sync with Bugbot on your connected SCM", but whether the findings
  themselves render on the PR or stay in the local agent session is unknown.
  This is the single largest unknown and it decides whether `make-pr` changes at
  all. Task 1 exists to resolve it before any code is written.
- **Cursor version floor.** `/review` and `/review-bugbot` require Cursor 3.7+.
  Below that, treat as not-installed.
- **Draft-PR interaction (load-bearing for autonomous runs).** Bugbot's account
  setting "Review Draft PRs" is **off by default**, and `make-pr` **forces
  `--draft` under `mode:autonomous`** (`DRAFT_FORCE`; pilot's terminus is
  documented as "make-pr (draft)"). So on a default Bugbot account, the remote
  reviewer never fires on a pilot-generated PR at all. Two consequences: the
  dedup has nothing to dedup against on that path, and the **coverage** argument
  becomes the primary justification for the stage rather than the cost argument
  -- pre-push is the only way Bugbot ever sees autonomous output. The smoke test
  must therefore exercise both a non-draft PR (to observe the dedup) and a draft
  PR (to record the skip), and the docs must state the interaction.
- **Autofix is incompatible with the dedup.** Bugbot's "Commit to Existing
  Branch" autofix mode commits after the review, which changes the patch ID and
  breaks invariant 1 by design. The docs must say to leave Autofix off (or use
  "Create New Branch") when the stage is enabled. The stage never changes the
  setting on the user's behalf.
- **Bugbot enabled is not Bugbot running.** A repo can be toggled on in the
  Automations tab and still produce zero reviews (usage exhausted, "run only when
  mentioned", draft PRs, or Individual-tier "only PRs you author"). Detect the
  absence of a review rather than assuming enablement means coverage.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** A manual smoke test on a prepared repo records, with captured evidence,
  the observed behaviour of `/review-bugbot` followed by a PR carrying an
  identical diff: whether the remote review is skipped, what the skip comment
  says, whether findings render on the PR, and what CI check conclusion is
  posted. Errors: if the dedup does not fire on an identical diff, the spec's
  premise is void and tasks 2 and 3 do not start -- record the finding and stop.
- **R2:** `pipeline.prepushReview` defaults to `off`, and with it off pilot's
  dispatched stage set and `PILOT_VERDICT` output are byte-for-byte identical to
  the pre-change behaviour. Errors: any non-enum config value (`true`, `null`,
  typo) resolves to off, never to on and never to an error.
- **R3:** With the gate on and the Cursor host active, pilot dispatches
  `prepush-review` exactly once at the all-tasks-done juncture, after `qa` when
  `pipeline.qa == on`, and before `make-pr`. Errors: gate on but non-Cursor host
  -> clean skip, no error, no `NEEDS_HUMAN`.
- **R4:** The stage writes a `prepush_review` receipt carrying `verdict`,
  `patch_id`, `head_sha` and `findings`. Errors: Bugbot unavailable, unauthed, or
  rate-limited -> `BLOCKED` receipt with a reason, and the tick still advances to
  `make-pr`.
- **R5:** `make-pr` asserts `HEAD` is unchanged since the receipt's `head_sha`
  and warns in its output when it is not. Errors: mismatch produces a warning,
  never a failed tick and never a blocked push.
- **R6:** Findings reach the human reviewing the draft PR -- either natively via
  Bugbot's SCM sync, or, when R1 shows they do not surface, carried into the PR
  body by `make-pr` alongside the existing cognitive-aid sections. Errors: zero
  findings produces no PR-body section rather than an empty one.
- **R7:** The stage never blocks the loop and never asks a question under
  autonomy. Errors: no error surface beyond R4.
- **R8:** No fix loop ships in this spec, and the churn non-goal is recorded in
  both the spec and the user-facing docs. Errors: no error surface.
- **R9:** Documentation covers the stage, the config flag, the Cursor-host-only
  constraint, the usage-cost implication, the draft-PR interaction, the Autofix
  incompatibility, and the recommended pairing (Bugbot pre-push plus a
  different-family reviewer on the PR). The full downstream property chain is
  walked, not just repo docs. Errors: no error surface.
- **R10:** The draft-PR interaction is characterised with evidence: what Bugbot
  does on a pilot-forced draft PR with "Review Draft PRs" off, and whether the
  dedup still applies when that draft is later marked ready-for-review. Errors:
  if a draft PR never triggers a remote review at all, record that pre-push is
  the sole coverage path for autonomous runs and reflect it in R9's docs.

## Boundaries
<!-- scope: business -->

Explicitly out of scope:

- **Any fix loop.** v1 is advisory only. A bounded loop is a separate, later
  decision.
- **Backend-split machinery.** No `--review=` passthrough, no model pinning, no
  effort specs, no per-backend workflow files, no prompt authoring. If a generic
  pre-push review is ever wanted, `impl-review` without `BASE_COMMIT` already
  does full-branch review.
- **Replacing existing review passes.** `impl-review` (per-task quality) and
  `spec-completion-review` (spec conformance against R-IDs and AC) both stay.
  Bugbot has never read the spec and cannot answer the conformance question.
- **Non-Cursor hosts.** Not a portability gap to close in this spec.
- **Merge and land.** Pilot's terminus stays the draft PR; merge stays
  human-gated.
- **Other reviewers.** No Greptile, CodeRabbit, or Copilot integration here.
- **Changing Bugbot configuration on the user's behalf.** The docs may recommend
  "run only once" and Incremental Review; the stage never writes them.

## Decision Context
<!-- scope: both -->

### Motivation
<!-- scope: business -->

Review economics, not review quality, are what break agent-driven loops. A team
running flow-next generates PRs faster than any per-review pricing model
anticipates, and the loop's own fix commits multiply the bill by roughly 3x
before anyone notices. The observable outcome is users disabling their reviewer,
which costs them the review lane entirely.

This is also a flow-next product concern rather than only a user concern: the
land loop's unit economics differ by orders of magnitude depending on which
reviewer a user has installed, and nothing in the docs says so today. Shipping
the stage is a chance to state the rule -- **the land loop is only economical
under a reviewer with either a separate quota or flat per-seat pricing** -- and
to give Cursor users the one configuration where a per-review reviewer stops
being punitive.

### Implementation Tradeoffs
<!-- scope: technical -->

**Stage over backend.** The first design routed Bugbot through `impl-review` as
another backend. That is wrong twice: impl-review is task-scoped and loops, which
destroys the patch ID, and the backend abstraction drags in prompt authoring and
model pinning that a self-contained product integration does not need. A
single-purpose stage is both smaller and correct.

**After `qa`, not before.** `qa` is advisory and does not commit today, so both
orders work at present. Placing the stage last makes it correct regardless of
what `qa` becomes, and avoids paying for a review of a diff that `qa` findings
then invalidate.

**Advisory before looping.** Shipping the fix loop first would be the natural
instinct and would recreate the churn problem inside flow-next. Advisory v1
proves the mechanism at one review per spec, which is also the cheapest possible
way to validate the dedup in production.

**Smoke test before implementation.** The findings-visibility question decides
whether `make-pr` changes at all, and the dedup premise is unverified in a real
PR. Both are cheap to answer manually and expensive to get wrong in code, so
task 1 is a human-run experiment with a hard stop-the-spec outcome.
