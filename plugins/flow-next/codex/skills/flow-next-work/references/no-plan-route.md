# No-plan route (gated reference)

> **Loaded only when Phase 1's zero-task fork fires** (spec-id entry, `tasks` array empty
> in `$FLOWCTL show <spec-id> --json`). Spec-file and idea-text starts never read this
> (they mint a single task unconditionally, direct-by-construction). A spec with any
> tasks (whatever their status) never reads this file.

## Pre-answer signals (flag / field / natural language)

SKILL.md's option parsing records `NO_PLAN=1` from `--no-plan` or natural-language
intent ("no plan", "skip planning", "work directly"). The spec's own `no_plan` field
(`no_plan: true` in the `$FLOWCTL show <spec-id> --json` already read at Phase 1 —
set at capture time or via `flowctl spec set-no-plan`) also sets `NO_PLAN=1`:
it is the same explicit human instruction, carried by the item instead of the
invocation. If `NO_PLAN=1`: skip the ask, go straight to Direct route. Contradictory
signals (flag or field says direct, prose says plan first) → ask instead of guessing.
On a later invocation, Phase 1 recognizes a sole `implicit_owner: true` task under
`no_plan: true` as this route's continuation. Intentional tasks stay authoritative.
A run that asked under a clean `NO_PLAN=1` has broken this.

Unless `NO_PLAN=1` is set with no contradicting signal: read [no-plan-ask.md](no-plan-ask.md)
and follow its autonomous refusal, ask and plan-first sections before the Direct route.

## Direct route: mint the implicit task

If the interactive ask in `no-plan-ask.md` ran, re-read `$FLOWCTL show <spec-id> --json`
and re-apply Phase 1's direct-route review gate before writing the route or minting; on a
clean `NO_PLAN=1` fast path Phase 1 already read `show` and applied that gate. A persisted
`needs_work` / `needs_human` or a request for design review made during the fork stops this
run with `NEEDS_HUMAN`; instruct separate `$flow-next-plan-review` for this spec before
re-invoking work. No backend or `--no-plan` choice bypasses that gate.

Refuse if the spec has no usable acceptance content (no acceptance criteria, no goal a
worker could act on): hand back to the user with a pointer to `$flow-next-plan` or
`$flow-next-refine` — never mint an empty task. Otherwise mint exactly ONE MINIMAL
task, no further confirmation. First persist the accepted route when `no_plan` is not
already `true` on the spec, including flag-only and interactive choices. Stop on a failed
write; never mint after one. This survives a crash before mint without fabricating a
plan-review verdict.

```bash
# Skip spec set-no-plan when Phase 1's show JSON already reported no_plan == true.
$FLOWCTL spec set-no-plan <spec-id> --json
$FLOWCTL task create --spec <spec-id> --title "Implement <spec title>" --satisfies "R1,R2,..." \
  --acceptance "Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly." \
  --require-empty-spec --json
```

`--require-empty-spec` on this recorded direct spec marks the task
`implicit_owner: true`. The marker distinguishes it from an intentional plan; it
is not a review verdict. Additional tasks make the ordinary planned route apply.

`--satisfies` lists ALL the spec's R-IDs (keeps the 3g single-task policy skip and the
make-pr coverage table correct); a spec with no R-IDs (goal-only) omits the flag
entirely — never pass it empty. The `--acceptance` line is a POINTER at the parent
spec, never copied criteria text — expanding the R-IDs into the task body is the
emulated-plan anti-pattern. Without it the task file carries a `TBD` placeholder and
the per-task impl review (whose contract is the task's acceptance) has nothing real to
judge, while the 3g skip then waives completion review. A goal-only spec words the
same pointer against the spec's goal instead of R-IDs. MINIMAL body — the task never emulates plan-full by
copying a plan into the body; the agent works from the spec, the task artifact exists
for the plumbing (receipts, evidence, review dispatch, done). No `Touches:` line — a
whole-spec task genuinely cannot name its paths.
Then continue with Phase 2 (branch choice) and the standard pipeline. A run that
minted a second task, or copied a plan into the body, has broken this.

If the `task create` above exits nonzero: read
[no-plan-ask.md § Concurrent mint](no-plan-ask.md#concurrent-mint) and stop as it says.

Only when the minted task goes to a worker, or before you dispatch any subagent while
implementing it: read [minted-task-dispatch.md](minted-task-dispatch.md).
