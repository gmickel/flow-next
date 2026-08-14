# fn-195-orchestration-by-intent-named-tiers-per Orchestration by intent: named tiers, per-harness reach, zero shipped model slugs

## Goal & Context
<!-- scope: business -->

Nobody understands our orchestration setup, including its author. To route work today a user meets a probe-and-pin ceremony, a role map keyed per bridged backend, a `backend:model:effort` grammar, per-host reasoning-tier tables, and model identifiers scattered through the docs — and then the identifiers go stale, because model ids change monthly and vary per account and per surface. Measured on current main: **179 concrete model-slug mentions across 64 files** in the plugin, doubled by the generated mirror. One model shipping means editing four surfaces; that has happened repeatedly.

The premise this spec changes: we were treating model routing as configuration to be enumerated and validated. It is better treated as **intent expressed to an orchestrator**. Every host flow-next supports already spawns its own subagents, already drives other CLIs, and already reads the project instruction file every turn. So flow-next should say *what kind of model* a job wants and *how this harness reaches one*, then let the orchestrator act — the same way a human operator gets correct routing today by writing two sentences of preference into their instruction file.

Who benefits: a user configures routing once, in their own file, in their own words, with model names they can verify against their own account — and stops paying for our enumerations going stale.

## Architecture & Data Models
<!-- scope: technical -->

**Two concepts replace the vocabulary.** A **tier** is what kind of model a job wants. **Reach** is how the active harness obtains one: the in-session model, an in-host subagent, shelling out to another CLI, or not available. Words like stamping, pinning, probe-verified, and role-map precedence leave the product; they described machinery this spec deletes.

**Four named tiers plus the default.** The names are user-facing English and become a stable interface, so they are chosen once and not churned:

- **reviewer** — anything grading work someone else produced. The only tier carrying a family rule (a reviewer from the writer's own family is not an independent verdict).
- **implementer** — work handed to another harness. The load-bearing case: plan on the session model, implement somewhere cheaper or faster. Absent means the session model implements.
- **fast scout** — mechanical inventory scanning where the cheapest tier is the correct one.
- **thinking scout** — analysis that degrades badly on a fast tier.
- **unset** — planning, capture, interview, requirement analysis, every verdict, and the worker run on the session model. This is the existing never-delegate-judgment doctrine, restated as the default rather than as a special case.

**Preferences live in the consumer's instruction file, expressed as concrete models with optional effort.** We ship no model identifiers outside a single reference page and the review-backend grammar. The block is short, because the instruction file is loaded every turn; the reasoning behind the tiers lives in the on-demand usage guide.

**Resolution is prose at the dispatch site, not a resolver.** Wherever a skill spawns or shells out, one line states the order: an explicit argument wins, then the project's routing block, then the agent definition's own default, then the session model. No new verb, no validation pass, no staleness math.

**Agent definitions keep their model field as a floor.** They are what applies when nothing overrides, which keeps today's behavior on the primary host byte-identical and makes the routing block additive rather than load-bearing.

**Reach is documented once per harness, never inside skills.** One short page per supported harness states which reach mechanisms exist there, which do not, and what the degradation is when one is missing. A skill says "hand this to the implementer tier"; it never names a spawn tool or a CLI flag.

**Routing becomes observable.** Prose routing is best-effort by nature, so the receipt surfaces already carrying review provenance record what actually ran for a stage wherever the harness exposes it. Recording, never prescribing: an unrouted stage is a fact in the record, not a failure.

## API Contracts
<!-- scope: technical -->

- Tier names are exactly: `reviewer`, `implementer`, `fast scout`, `thinking scout`. A fifth name is a breaking change to a user-facing interface.
- A routing block entry is `<tier>: <model>` or `<tier>: <model> at <effort>`; an absent tier means the session model; an unparseable line is ignored with one advisory, never an error.
- The review backend keeps its existing `backend[:model[:effort]]` configuration and its receipts unchanged. This spec does not touch it.
- Deleted configuration keys are reported by name once when encountered, with the sentence that routing now lives in the instruction file. A stale key never blocks a run.

## Edge Cases & Constraints
<!-- scope: technical -->

- **A named model the harness cannot reach** (a slug from another vendor's CLI, a retired id, an id the account lacks): fall back to the session model, say so once, continue. No probing, no question, no failure. This is the case the deleted ceremony existed to prevent and it does not need preventing.
- **No routing block at all** is the common case and must be indistinguishable from today: agent defaults apply, session model otherwise.
- **A tier named for work the harness cannot delegate** (no subagent primitive, no second CLI): the work runs in session and the degradation is stated once.
- **The family rule is advice, not enforcement.** We cannot verify a model's family from a name a user invented. The reviewer tier documents the rule and the receipt records what ran; nothing fails closed on it.
- **Effort semantics stay the host's**: we pass it through and never translate between vendors' scales.
- **Instruction-file edits are the user's.** Setup proposes a commented block once; nothing rewrites a block a human has edited, and nothing infers availability into it.
- Standing criteria in `.flow/criteria.md` apply as written and are not restated here.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** The four tier names plus the unset default are defined in exactly one place, in user-facing English, and every dispatch site that routes work refers to a tier rather than a model. Errors: an unrecognized tier name is treated as unset with one advisory line.
- **R2:** Shipped prose contains no concrete model identifiers, with two declared exceptions: the single reference page that explains tier choices, and the review-backend configuration grammar. The count starts at 179 across 64 files; the end state is the two exceptions and nothing else. Errors: an identifier that cannot be removed without losing a load-bearing contract is listed as an exception with its reason, not left silently in place.
- **R3:** Each supported harness has one short page stating its reach mechanisms, what is unavailable there, and the degradation when a mechanism is missing. No skill names a spawn primitive, a CLI flag, or a vendor path. Errors: an undetectable harness resolves to the generic page and says so.
- **R4:** Every dispatch site states the resolution order as prose — explicit argument, then project routing block, then agent default, then session model. Errors: no error surface; the chain terminates at the session model by construction.
- **R5:** Setup proposes a routing block in the project instruction file with values commented out and tier guidance as comments, then closes by saying it wrote an example to edit. It never asserts which models are installed, and it never overwrites a human-edited block. Errors: an existing block is left untouched and reported.
- **R6:** The pinning ceremony and the per-backend role map are removed: no probe-verified pin requirement, no staleness stamp, no role-map validation on write. Deleted keys are reported by name once and never block. Errors: a config carrying deleted keys runs unchanged.
- **R7:** Where the harness exposes it, the stage receipt records the model that actually ran, so routing is checkable after the fact. Errors: unavailable provenance is recorded as unknown, never as the configured value.
- **R8:** Full suite, lint, mirror parity and the OS matrix are green; the docs sweep covers the reach pages, the usage guide, the setup flow, and the platform pages together. Errors: no error surface beyond the gate.

## Boundaries
<!-- scope: business -->

- **The review backend stays.** Its configuration, dispatch, receipts, round counting and provenance are untouched here; whether it collapses later is its own spec.
- **Packaged implementation delegation is not removed by this spec** — that is its own existing spec, and this one assumes it has landed, because the vocabulary changes when it does.
- No new flowctl verb, no new config schema, no validation pass over user prose.
- No model rankings, benchmark numbers, or speed claims in shipped text; tier guidance explains *kinds* of work, never scores.
- No enforcement of the family rule, and no availability detection of any kind.
- No changes to how subagents are defined beyond their model field remaining a default.

## Decision Context
<!-- scope: both -->

**Why intent beats configuration here.** Two independent signals. Our own platform documentation already records that config-based per-agent model application is unreliable on one major host and that steering by explicit invocation is preferable there. And a human operator gets correct routing today by writing preferences in prose, with no machinery at all — the orchestrator reads them and acts. Enumeration was solving a problem the orchestrator does not have, while creating one we pay for every vendor release.

**Why the user writes the slugs.** Model identifiers are a property of a machine and an account, not of a project or a framework. A consumer naming their own models in their own instruction file owns exactly one place, can verify it against their own CLI, and is never surprised by our list going stale. This is the same reasoning that rejected a setup-time availability snapshot: config that claims what is installed becomes config that lies.

**Why `implementer` is a tier and not an optional extra.** The most valuable split in practice is planning on a strong session model and implementing on a cheaper or faster one. That is the case users ask for, and it is the reason a tier vocabulary earns its place at all.

**Why agent defaults survive.** Stripping them would change behavior on the primary host and make the routing block mandatory. Keeping them as a floor makes this spec additive: absent a block, nothing changes.

**Rejected: a resolver verb.** Precedence is four words at the dispatch site. A verb would add a call, a schema, and a validation surface to a lookup a sentence already performs — and the existing role-map resolver is the machinery this spec is deleting.

**Rejected: shipping a capability or intelligence table.** It rots faster than slugs do, and ranking models in shipped prose violates the no-benchmark-claims rule. Tier guidance describes kinds of work instead.

## Parked unknowns

- Whether the `fast scout` / `thinking scout` split survives contact with users, or collapses into one `scout` tier. It is a real question about how many knobs people will set, and only usage answers it. What would resolve it: whether anyone sets the two tiers to different models once the block exists.
