# Optional merge destination for flow

## Conversation Evidence

> user (research brief): "Flow composes existing primitives for each stage. It should optionally carry an item through PR convergence and merge by consuming land's behavior."
> user (research brief): "Land remains available independently for existing PRs, scheduled babysitting, and recovery. Do not duplicate its gates, CI repair, review resolution, merge logic or post-merge steps inside flow."
> user (research brief): "Explore an explicit destination such as \"stop at draft PR\" versus \"continue through merge\", independently of attended/autonomous mode. --until=merge is an example, not a decided interface."
> user (research brief): "Merge permission must not bypass review, QA, CI, branch protection, dependency gates or NEEDS_HUMAN."
> user (research brief): "Explicit spec/PR scope, including whether a host prompt already provides sufficient scoped behavior. Test with unrelated eligible PRs present before concluding that a new selector or scope mechanism is necessary."
> user (research brief): "Consent lifetime and revocation across retries, fresh sessions and resumes."
> user (research brief): "Waiting for CI/reviews, one-tick versus long-running behavior, disk-based recovery, and terminal/evidence contracts a factory can consume."
> user (research brief): "Post-merge scope: spec close, release-follow, tracker updates and recovery. Distinguish permission to merge from any additional external actions."
> user (research brief): "Backward compatibility for default flow behavior and existing verdict consumers. Keep fn-240 harness/model autorouting independent unless current evidence establishes a real dependency."
> user (scope clarification): "Well think about it this way or differently, like forget about merge foundry for a second, but essentially what you want is if you put flow next flow auto and then some kind of parameter you want it to be able to merge the spec right however we do that it doesn't really matter if we use the current land thing, that makes sense."
> user (scope clarification): "Perhaps we still keep land in there for manual stage usage. This fits with the other patterns, I think, right?"
> user (scope clarification): "It would have to be added to the, you know, next step thing if it's being manually called, like if there's already a PR and then you run flow again, it would then do that. Maybe, or it would ask if it should do that, probably more likely."
> user (consent clarification): "Yeah, I feel that asking is important here if they haven't run it with until merge because current behavior has always been until merge, right? And we haven't done anything like auto-merging so far in FlowNext."

> user (release grouping): "figure out everything that this would touch and we will do this edit ourselves directly first, then bake it into the minor release when we release 241 later"

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 90% [paraphrase], 10% [inferred] -->

A user should be able to give flow a spec and an explicit destination through merge. Flow then carries the item through the existing build stages, PR convergence, and landing without requiring the user to compose the build and landing loops themselves.

The 5.0.0 attended conductor and 5.1.0 unattended mode established the shared route. Their default boundary is before merge. Standalone land already has an opt-in merge license. This feature makes landing an optional stage consumed by flow while preserving that explicit consent boundary.

The key attended interaction is a user rerunning plain flow on a spec with an existing PR. Flow recognizes landing as the next step and asks whether to continue through merge unless the user has already explicitly authorized landing that item. The existence of a PR, completion of its tasks, or rerunning flow is never merge consent.

## Architecture & Data Models
<!-- scope: technical -->
<!-- Architecture & Data Models: 100% [paraphrase] -->

Flow owns route selection, continuation, and the human interaction. Land owns PR convergence, its gates and repair budgets, merge execution, and the post-merge tail. Flow invokes land and consumes its observed result rather than copying any of those steps.

Land remains available as a standalone stage for an existing PR, scheduled babysitting, and recovery. The driver-nesting prohibition gains a confined exception for flow invoking land as its landing stage. Ralph restrictions and recursive-driver prohibitions remain intact.

The selected spec and PR remain the route's scope across handoffs and retries. Explicit host context is the initial scope mechanism; the research probe successfully narrowed a land simulation with unrelated eligible PRs present. That simulation does not establish live or cross-host enforcement. A new selector or additional state machinery needs demonstrated necessity rather than being assumed by this feature.

## API Contracts
<!-- scope: technical -->

- Proposed spelling: `flow <spec> --until=merge` and `flow --auto <spec> --until=merge`. Destination and interaction mode are independent. The spelling is a proposal for this capture, not a previously settled interface. [inferred]
- Without a merge destination, unattended flow preserves its existing pre-merge terminal behavior. Attended flow adds landing to its existing-PR next-step guidance and obtains consent before invoking it. [paraphrase]
- Attended approval authorizes landing the current item; refusal leaves it unmerged. Approval is not requested again at every CI or review retry while that authorization remains active. [paraphrase]
- Existing terminal names and default verdict semantics remain compatible. Landing progress, an external wait, a human blocker, and a confirmed merge must be distinguishable in the returned evidence; no new factory protocol is prescribed. [paraphrase]

## Edge Cases & Constraints
<!-- scope: technical -->

- An unrelated eligible PR must not enter the route's landing actions. A missing, ambiguous, or closed-unmerged target does not authorize substitution or resurrection. [paraphrase]
- CI and review waits reuse land's cadence and patience behavior. Waiting is not a failed implementation attempt and does not consume pilot's no-advancement strikes. A tick performs one landing tick; a long-running invocation can wait and continue until the destination or an existing stop condition. [paraphrase]
- Retries and resumes re-read durable state and current permission. Revocation stops subsequent mutations; a completed merge is observed as completed, never retried. A historical transcript alone does not establish current merge authority. [paraphrase]
- The landing handoff must respect land's existing checkout and ownership constraints. Research found that its merge-verdict gate requires the base checkout and that a base branch already occupied by another worktree can prevent its tail checkout. Preserve these guards while making the normal flow-to-land handoff work. [paraphrase]
- Ordinary server-side branch catch-up stays within land. Conflicting hunks keep the existing escalation; an optional independently reviewed conflict-resolver handoff remains follow-up scope. [paraphrase]
- Merge success and tail completion are separate observations. Spec close, its persistence, release-follow, and tracker updates remain land-owned and honor their applicable authorization and configuration. A tail failure reports what already succeeded and what remains, without repeating the merge. [paraphrase]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** An explicit merge destination is available independently of attended or autonomous mode. A run can carry its selected spec from the existing build route through PR convergence to a confirmed merge. Errors: an absent or invalid destination never grants merge permission; the default unattended route retains its pre-merge stop. [paraphrase]
- **R2:** When plain attended flow encounters a spec with an existing PR, its next-step guidance offers continuation through merge and asks once before handing off to land unless landing that item is already explicitly authorized. Errors: declining or not answering causes no landing mutation; PR existence, readiness, and a repeated invocation are not consent. [paraphrase]
- **R3:** Flow consumes land's existing workflow, and standalone land remains usable independently. The composition exception is consistent across the route, tail, autonomy, and dispatch contracts. Errors: neither path bypasses review, QA, CI, branch protection, dependencies, repair limits, or `NEEDS_HUMAN`; flow duplicates none of land's convergence, merge, or tail logic. [paraphrase]
- **R4:** Long-running flow can continue across land ticks and CI/review waits; tick mode performs at most one landing tick. Errors: waiting does not consume pilot strikes, spin through repair attempts, or suppress an existing stop condition; the run reports enough observed evidence to distinguish progress, waiting, blockage, and merge completion. [paraphrase]
- **R5:** Landing actions stay bound to the selected spec/PR through retries and disk-based recovery, including when unrelated eligible PRs exist. Errors: ambiguous identity, lost authority, conflicting landing ownership, or an unusable landing workspace stops safely; an already merged PR resumes only its remaining authorized tail, and a closed-unmerged PR is not replaced automatically. [paraphrase]
- **R6:** Merge consent stays scoped to the item and is honored across retries while active; revocation stops subsequent mutations. The landing contract states how fresh-session resumes establish current consent and how spec close, release-follow, tracker updates, and recovery are authorized. Errors: merge permission alone does not silently grant additional external actions, and partial post-merge failure never becomes a second merge attempt. [paraphrase]
- **R7:** Existing default flow and standalone-land behavior and verdict consumers remain compatible, apart from the specified attended landing offer. Focused verification covers consent/decline, default versus merge destination, tick versus continuation, unrelated PRs, waits and existing gates, and recovery after merge. User-facing guidance explains the optional destination and manual next step. Errors: tests must expose accidental default merging, target substitution, gate bypass, and false completion claims; existing supported-host contracts remain intact. [inferred]

## Boundaries
<!-- scope: business -->

- No factory admission, aggregate scheduling, capacity or spend management, or cross-route coordination product in this feature. The feature is flow optionally carrying one item through landing. [paraphrase]
- No new driver and no copy of land's gates, CI repair, resolver, merge, or post-merge implementation inside flow. [paraphrase]
- No conflict-hunk resolver, stacked-PR support, or merge-queue integration as a prerequisite for continuation. [paraphrase]
- No dependency on fn-240 harness/model autorouting. [paraphrase]
- No prescribed task decomposition or new scope-selector, consent-store, or factory-receipt architecture. Keep the implementation as small as the observed behavior permits. [paraphrase]

## Decision Context
<!-- scope: both -->

- The governing product model is the existing conductor pattern. Flow chooses and runs the next stage; a user may invoke the same stage directly. Land is special in its merge authority, but still fits that composition. [paraphrase]
- The later scope clarification takes precedence over the earlier broad factory research. Ownership and recovery findings constrain a correct handoff; they do not justify turning this feature into an orchestration platform. [paraphrase]
- The explicit attended question preserves the established pre-merge boundary. The user's shorthand that flow previously ran "until merge" means up to the merge decision; the observed shipped behavior did not merge from flow. [paraphrase]
- The 5.1.0 long-horizon parity study still reported no draws during this research. The 191 focused tests and synthetic scope/worktree probes support the contract analysis, but do not prove a complete flow-to-merge run. Verify the new continuation behavior directly. [paraphrase]
- The change follows the strategy's composition principle: host judgment stays in skills and deterministic helpers remain thin. Standing criteria G1 and G2 apply. [strategy:Design principles]

## Delivery Handoff (2026-09-12)

- The capture approval removal is already merged in [PR #428](https://github.com/gmickel/flow-next/pull/428), commit `3716e52cd503995ce30d64f6e29899d7e40b1950`, on main. Interactive capture now saves the spec before its editor offer; substantive questions, plan/refine approval, and autofix's `--yes` gate remain. Build on this behavior. This is separate from R2's required consent before landing a PR. [paraphrase]
- That patch remains under Unreleased. Include it in the minor release that ships fn-241; do not cut a separate capture release or repeat the capture implementation. Its final verification was 4,886 local tests with zero failures, a SHIP implementation review, and 14 green PR checks before merge. These results cover the capture patch, not fn-241. [paraphrase]
- The combined release must finish the deferred downstream capture updates as well as fn-241's own documentation: the docs site's Capture skill page, first-30-minutes tutorial, and capture example in Writing Specs; the AI x SDLC guide's Flow-Next read-back paragraph; and the vault's Skills Catalog, Lifecycle and Handover Objects, Vocabulary and Concepts, and Messaging Library. Update release entries, the site version, and the vault index/log at that release, preserving historical entries. The repository's downstream-properties policy owns the publication and verification procedure. [paraphrase]
- The remaining design choices are explicit: the destination spelling is still proposed; the precise fresh-session consent lifetime and post-merge authorization contract must be settled under R6. Reuse the existing landing behavior and the recorded scope constraints when settling them. They do not require reopening factory orchestration or fn-240. [paraphrase]
