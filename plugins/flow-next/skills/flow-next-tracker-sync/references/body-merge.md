# Body reconciliation — agentic 3-way merge + format translation + scoped conflict (R6/R9)

The body-sync reconcile body behind the [../steps.md](../steps.md) Phase 3 `reconcile` /
`push` / `pull` hooks. This is the spec's **early proof point**: a two-way,
**agentic** 3-way merge against the stored merge base, with **format translation**
between flow's structured spec and the tracker's free-form issue, surfacing only
**genuine, section-scoped contradictions** for a human.

It operates ONLY on the normalized `issue` struct ([adapter-interface.md](adapter-interface.md)) —
never a Linear/GitHub/GitLab wire shape. The transport ([linear-ladder.md](linear-ladder.md))
is the firewall; this file is the merge. A transport bug stays in the rung file; a
merge bug stays here.

> **This is the host agent's judgment, not a deterministic engine.** Per CLAUDE.md
> "Architecture: agentic vs deterministic", the host agent IS the intelligence —
> the semantic 3-way merge (does this Linear edit *contradict* this flow edit, or
> just touch a different part of the same section?) is exactly what the agent is
> for. **Do NOT build a deterministic fallback merge engine** (the anti-pattern
> list literally names it). flowctl owns the deterministic parts — snapshot the
> base (`sync set-merge-base`), advance state (`sync set-last-synced`), emit the
> receipt (`sync receipt`), queue a conflict (`sync defer`). This file owns the
> merge, the translation, and the conflict judgment. The **deterministic
> pre-reduction** and the **structural gate** below are the only mechanical steps —
> and they exist to *narrow* what the agent judges, not to replace the judgment.

> **Live-verification status (this environment).** A full end-to-end exercise of the
> merge over a real Linear round-trip needs live credentials (a registered MCP
> server OR a `LINEAR_API_KEY` against a real workspace) — unavailable in the build
> environment. The **strictly-live step is deferred to the post-PR smoke-testing
> phase** the maintainer drives (same posture as the [linear-ladder.md](linear-ladder.md)
> round-trip spike). Everything else here — the pre-reduction, the format
> translation, the structural gate, the scoped-conflict judgment — is a complete,
> runnable procedure with worked fixtures and explicit oracles below, exercisable
> without a live tracker.

## The three inputs (real 3-way, never a 2-way guess)

The merge is **3-way** against the `lastSyncedAt` snapshot. Read all three from
flowctl + the transport:

| Input | Source | Form |
|---|---|---|
| **base** | `sync get-state <spec> --json` → `tracker.mergeBaseFlow` AND `tracker.mergeBaseTracker` | the body as it was at last sync — stored in BOTH forms (flow-structured + tracker-rendered) |
| **flow-side** | the current `.flow/specs/<id>.md` body | flow-structured (sections, R-IDs, source tags) |
| **tracker-side** | `fetchIssue(trackerId).body` (normalized `issue`) | free-form markdown |

Why both base forms: 3-way merge needs the ancestor in a form **comparable to each
side**. `mergeBaseFlow` is diffed against the live flow body; `mergeBaseTracker` is
diffed against the pulled issue body. fn-52.1 stores both (and their hashes) and
enforces the **paired-snapshot invariant** — `sync set-merge-base` requires BOTH
`--flow*` AND `--tracker*` together; never write one half alone (memory:
`paired-snapshot-setter-must-write-both`).

```bash
# Read the base (both forms + the echo-fence hashes):
STATE=$($FLOWCTL sync get-state "$SPEC_ID" --json)
# .tracker.mergeBaseFlow / .mergeBaseTracker / .baseHashFlow / .baseHashTracker
```

## Step 0.5 — Flow-owned fenced regions: the *tracker-body-for-merge* transform (fn-64, R10)

Some regions of the tracker body are **flow's, not the spec's** — flow writes them, flow owns them, and they must NEVER round-trip back into the spec or be re-litigated as tracker divergence. Today that is the GitHub dependency block on the fallback path:

```markdown
<!-- flow:deps -->
**Blocked by:** #12, #15, #23
<!-- /flow:deps -->
```

(written by `setIssueRelation` on the GitHub fenced fallback — [github.md](github.md) § Relation transport; the marker is its provenance boundary.)

**The rule (load-bearing):** define a canonical **`trackerBodyForMerge(rawBody)`** transform that **strips the entire `<!-- flow:deps -->` … `<!-- /flow:deps -->` fenced region** (markers included), and apply it to the tracker body **before EVERY hash / merge-base / divergence comparison in this file** — specifically:

- the `baseHashTracker` content hash and the stored `mergeBaseTracker` snapshot (Step 5 writes the *stripped* tracker form, so the next reconcile compares like-with-like);
- the echo-fence check (Step 1 "Echo / no real change") and ALL of Step 1's pre-reduction comparisons;
- the `fetchIssue(trackerId).body` fed into Steps 2–4.

```bash
# Pseudo: everywhere this file reads issue.body for comparison/merge, read it through the transform.
TRACKER_BODY=$(trackerBodyForMerge "$RAW_ISSUE_BODY")   # <!-- flow:deps -->…<!-- /flow:deps --> stripped
```

**Reinject / preserve ONLY on a body-fallback issue-body write (GitHub-native-unavailable, or GitLab on a Free/personal namespace).** The fenced block is reattached (by `setIssueRelation`, which edits *only inside* its own markers — github.md / gitlab.md) when writing the issue body; the *merge* never sees it, never produces it, and never copies it into `.flow/specs/<id>.md`. Concretely:

- **Reconcile never folds flow's own block back into the spec.** Because the block is stripped before tracker→flow folding (Step 3 / Step 2), a `## ` section or stray `**Blocked by:**` line can never be invented into the spec from flow's own projection.
- **Render never overwrites it — but only because the WRITE preserves it.** `renderFlowToTracker` (flow→tracker) produces the spec body only; the dep block is a separate, additive `setIssueRelation` write that operates inside its markers. `renderFlowToTracker`'s output therefore does NOT contain the block, so a full-body `writeIssue` UPDATE path (GitHub's `gh issue edit --body-file -`, or GitLab's `PUT /issues/:iid` description write — github.md / gitlab.md § `writeIssue`) MUST read the current issue body and carry the existing `<!-- flow:deps -->` region forward before writing. Skip that carry-forward and a normal push self-deletes the block, and the very next `projectDepRelations` misreads the still-ledgered edge as a remote removal → false collision (queued, never recreated). The strip-on-read / retain-on-write seam is symmetric: the merge is blind to the block; the write keeps it. The dep projection, in turn, does not clobber the rendered spec body (it edits only inside its markers).

> **Why at the hash boundary, not just visually:** raw full-body hashing would see flow's just-written `<!-- flow:deps -->` block as a tracker-side change on the very next pull, flag a phantom divergence, and break echo-suppression. The strip MUST happen where the hash is computed — `trackerBodyForMerge` is the seam. (Linear native relations need no transform: relations are not in the body. The transform is body-fallback-specific — GitHub-native-unavailable, or GitLab on a Free/personal namespace — but lives here, transport-blind, as a body-merge rule.)

This generalizes the existing flow-internal-scaffolding exclusions (the `<!-- scope: … -->` HTML comments and the source-tag breakdown comment are likewise never surfaced as tracker text, Step 3) — `<!-- flow:deps -->` is the same idea on the tracker side: a flow-owned region the merge is blind to.

## Step 1 — Deterministic pre-reduction (kills false-conflict over-surfacing)

Before the agent judges anything, reduce the trivial cases mechanically. This is
the only place a deterministic step precedes the merge — and it exists to ensure
the agent **only ever judges genuine both-sides-diverged content**, which is what
keeps the merge from over-surfacing false conflicts (the spec's named failure mode).

Per side, compare against the base **in that side's form**:

| Case | Condition | Action |
|---|---|---|
| **Echo / no real change** | tracker body hash == `baseHashTracker` (flow's own last push echoed back) | tracker side contributed nothing → treat as unchanged; `noop` if flow also unchanged |
| **Both byte-identical to base** | flow == `mergeBaseFlow` AND tracker == `mergeBaseTracker` | nothing to merge → `noop`, do NOT advance `lastSyncedAt` |
| **Only flow changed** | tracker == `mergeBaseTracker` (or echo), flow != `mergeBaseFlow` | fast-forward **flow → tracker**: render flow, `writeIssue`, snapshot. No conflict possible. |
| **Only tracker changed** | flow == `mergeBaseFlow`, tracker != `mergeBaseTracker` (and not an echo) | fast-forward **tracker → flow**: fold tracker free-text into flow sections, write spec, snapshot. No conflict possible. |
| **Both changed** | flow != `mergeBaseFlow` AND tracker != `mergeBaseTracker` (not an echo) | → **Step 2** (the agent's real job). |

The echo check uses the stored `baseHashTracker` content hash (fn-52.1's
`_content_hash`) — computed over the **`trackerBodyForMerge`-stripped** body (Step
0.5), so flow's own `<!-- flow:deps -->` block never registers as a tracker-side
change: a post-push pull whose stripped body hash matches what flow pushed is
flow's **own echo**, not a tracker-side edit — a `noop`, never a phantom conflict.
`lastSyncedAt` advances only on a real reconciliation (a fast-forward or a merge),
**never on an echo or a no-op pull**.

> Pre-reduction is mechanical *comparison* only (hash/byte equality). It does NOT
> attempt a text merge — the moment both sides diverged, the agent takes over. This
> is the CLAUDE.md split in miniature: equality is deterministic; meaning is agentic.

## Step 2 — Agentic 3-way merge (both sides diverged)

Only reached when **both** sides changed since base. The host agent reads
base / flow-side / tracker-side and produces the merged body. Per section
(`## Goal & Context`, `## Acceptance Criteria`, …) and per logical unit within it:

1. **Section / unit only one side touched** → take that side's version. (A PM
   clarified the Goal in Linear; a dev left the Acceptance untouched → keep the
   dev's Acceptance, take the PM's Goal.) **This is the headline R6 case: two
   non-conflicting two-sided edits both survive.**
2. **Both sides added different new content to the same section** (additive, not
   contradictory — e.g. flow added a new acceptance bullet, the tracker added a
   sentence of context to the same section) → **fold both in**, ordered sensibly.
3. **Both sides rewrote the same content to mean *different things*** (a genuine
   semantic contradiction the agent cannot confidently reconcile — e.g. flow
   narrowed the Goal to "OAuth only" while the tracker broadened it to "OAuth +
   SAML") → **scoped conflict** (Step 4). Do NOT silently pick a side; do NOT
   merge incompatible meanings into mush.

Judge by **meaning, not by line position.** A two-line diff that says the same
thing reworded is NOT a conflict; a one-word change that inverts the meaning IS.
This is precisely the judgment a deterministic line-merge gets wrong and the host
agent gets right — the reason the merge is agentic.

## Step 3 — Format translation (flow-structured ↔ tracker free-form) (R6)

The two sides are in different formats; the merge spans the translation. The agent
**translates** — it never byte-copies.

### flow → tracker (render structure into a readable issue)

- **Project the ENTIRE spec — every section, in full.** The render is a *format translation*, NOT a summary: never condense, truncate, abbreviate, or omit a section, an R-ID, or a paragraph. A reader of the issue must see the same content as the spec, just as clean free-form markdown. "Projection, not coordination" also means projection-in-full — a summarized issue is a data-loss bug, and the Step 3.5 structural gate ("no section silently dropped") fails it. The ONLY content intentionally not surfaced is the flow-internal scaffolding called out below (scope HTML comments, source-tag breakdown comment); everything else is rendered.
- Render the structured spec into clean free-form markdown a PM reads comfortably:
  keep the section headings as plain `##` headings, render acceptance criteria as a
  checklist, keep links/code spans intact.
- **R-IDs and source tags are flow-internal scaffolding.** Render them in a way that
  survives a round-trip without cluttering the issue — keep the `[R6]` suffix on a
  criterion (it is meaningful provenance the PM may reference) but do NOT surface
  the `<!-- scope: ... -->` HTML-comment annotations or the source-tag breakdown
  comment as visible issue text.
- **Idempotent for unchanged content** — rendering an unchanged flow body must
  produce a tracker body byte-identical to `mergeBaseTracker` (so flow→tracker→flow
  is no churn). If the tracker renderer canonicalizes markdown in a stable way
  (Linear normalizing list markers, collapsing blank lines), record that canonical
  form as the snapshot so the next reconcile compares like-with-like — see the
  [linear-ladder.md](linear-ladder.md) round-trip spike, whose whole job is to pin
  this canonical form *before* this merge runs on top of it.

### tracker → flow (fold free-text into the right flow sections)

- Fold a tracker-side free-text edit into the **correct flow section** by meaning —
  a PM rewriting the problem statement folds into `## Goal & Context`; a new
  acceptance line folds into `## Acceptance Criteria`.
- **NEVER invent R-IDs or source tags.** A PM literally typing `R17:` in Linear is
  **prose, not a promoted requirement** — fold it as prose under the right section;
  do not allocate a new R-ID, do not add a coverage-table row, do not stamp a
  `[user]`/`[paraphrase]`/`[inferred]` source tag. R-ID allocation and source
  tagging are flow-authoring acts (capture/interview/plan), not sync acts. The
  bridge **projects**; it does not author requirements.
- Tracker free text that matches no existing section folds into the nearest
  sensible section (or a `## Notes` section) — never dropped, never invented into a
  fake structured element.

## Step 3.5 — Structural verification gate (before ANY write-back) (R6)

A mechanical gate the merged body MUST pass **before** `writeIssue` or writing the
spec. This is the second (and last) deterministic step — it guards the agent's
output, it does not replace the merge:

- **No section silently dropped.** Every `##` section present in base, flow-side, OR
  tracker-side must be present in the merged output (unless a side *deliberately and
  unambiguously* deleted it — a deletion is itself a change the merge reasoned about
  in Step 2, not a silent drop).
- **Both sides' non-conflicting additions present.** Every additive change the
  pre-reduction / merge classified as "keep both" (Step 2 cases 1 and 2) appears in
  the output. A merge that quietly lost the dev's new acceptance bullet fails the
  gate.
- **No invented structure.** The merged flow body introduces no R-ID / source tag
  that did not exist in flow-side (Step 3's "never invent" rule, checked).

```bash
# The gate is a host-agent self-check (read the merged body, verify the three
# invariants above against base/flow/tracker). If it FAILS, do NOT write back —
# emit an errored receipt and re-merge or queue. ($EVENT = the lifecycle event tag
# from steps.md Phase 0; empty on manual runs, so the expansion omits the flag.)
$FLOWCTL sync receipt "$SPEC_ID" --status errored --transport "$TRANSPORT" ${EVENT:+--event "$EVENT"} \
  --note "structural gate failed: <which invariant> — write-back aborted, base unchanged"
```

A gate failure is treated like a transport failure: **no write-back, no state
advance, base unchanged** — never a partial/half-merged write.

## Step 4 — Scoped conflict (genuine contradiction only) (R9)

Reached ONLY from Step 2 case 3 — a genuine semantic contradiction. The conflict is
**scoped to the one section** that contradicts; the rest of the body merges cleanly
and is NOT re-litigated. **Never surface the whole body as a conflict; never
silently overwrite.**

### Interactive mode — confirm before write-back

Show the human the **merged body** (every cleanly-merged section already folded) with the single contradicting section flagged inline, and ask via `AskUserQuestion` (call `ToolSearch` with `select:AskUserQuestion` first if its schema isn't loaded):

- Options scoped to the one section: keep flow's framing · keep the tracker's ·
  accept a proposed merge of the two · edit by hand.
- On choice → apply to that section only → re-run the **structural gate** → write
  back (`writeIssue` + write the spec) → `sync set-merge-base` (BOTH halves) +
  `sync set-last-synced` → `sync receipt --status merged` (+ `--event` on a
  lifecycle run — steps.md Phase 0).

The confirmation shows the *whole merged body* (so the human sees the merge is
correct everywhere else) but the *decision* is scoped to the contradicting section.
That is the R9 guarantee: focused, not whole-body.

### Autonomous / Ralph mode — queue, never block (R9/R11)

Confident merges (Steps 1–3 with no Step 4 contradiction) proceed unattended. A
genuine contradiction — **including the `always-ask` tiebreak default** — does NOT
prompt and does NOT block: it **queues** to the deferred sink. "Ask the human"
resolves to "queue for the human" in autonomous mode (same policy, surface-dependent
delivery — mirrors fn-51's surface-aware ladder).

```bash
# Ralph (FLOW_RALPH=1 / REVIEW_RECEIPT_PATH set): queue the scoped conflict, write
# NO body, advance NO state, continue the batch.
$FLOWCTL sync defer "$SPEC_ID" \
  --summary "Goal section rewritten on both sides to mean different things (flow: OAuth-only; tracker: OAuth+SAML)" \
  --suggested "Human picks: keep flow's framing, the tracker's, or a merge of the two" \
  --reason "genuine-contradiction"
$FLOWCTL sync receipt "$SPEC_ID" --status diverged --transport "$TRANSPORT" ${EVENT:+--event "$EVENT"} \
  --note "scoped conflict queued (Goal section); base unchanged"
```

The conflict-tiebreak default (`flow-wins | tracker-wins | always-ask`, R1) governs
the rare unresolvable case: `flow-wins`/`tracker-wins` auto-resolve the scoped
section to that side (still a confident merge → proceed); `always-ask` queues in
Ralph (above) and prompts interactively.

## Step 5 — Write-back + snapshot + receipt (state advances ONLY on success) (R6)

State (`lastSyncedAt`, the merge base) is written **ONLY after a fully successful
reconcile + write-back**. This is the no-half-advance invariant:

```bash
# 1. write-back (transport + spec) — both must succeed:
#    writeIssue(merged)            [transport — linear-ladder.md]
#    write the merged flow body to .flow/specs/<id>.md
# 2. ONLY THEN advance state — snapshot BOTH forms together (paired invariant):
$FLOWCTL sync set-merge-base "$SPEC_ID" --flow-file /tmp/merged-flow.md --tracker-file /tmp/merged-tracker.md
$FLOWCTL sync set-last-synced "$SPEC_ID"
# 3. receipt records the merge for audit / rollback (--merges-file = the merge log):
$FLOWCTL sync receipt "$SPEC_ID" --status merged --transport "$TRANSPORT" ${EVENT:+--event "$EVENT"} --merges-file /tmp/merges.json \
  --note "3-way merge: 2 sections folded, 0 conflicts"
```

**Failure leaves prior state intact.** A failed/errored fetch or write (404,
transport error, structural-gate failure, partial batch) does NOT advance
`lastSyncedAt` and does NOT overwrite the merge base — it emits an `errored` (or
`queued`) receipt and leaves the base from the last good sync. Batch sync is
**item-level**: one spec's failure gets its own `errored` receipt + no state write,
and the run continues with the rest (the orchestration loop in [../steps.md](../steps.md)
catches per-item; this file's contract is "never advance state on a non-success").

### Merge-log record shape (`--merges-file`)

`sync receipt --merges-file` takes a JSON **list** of merge records (fn-52.1 stores
them verbatim on the receipt for audit/rollback). Each record documents one
reconcile for traceability — minimum useful shape:

```json
[
  {
    "spec": "fn-42-add-oauth",
    "trackerId": "uuid-...",
    "outcome": "merged",
    "sectionsFolded": ["Goal & Context", "Acceptance Criteria"],
    "conflicts": [],
    "baseHashFlowBefore": "…",
    "baseHashTrackerBefore": "…"
  }
]
```

The pre-`set-merge-base` hashes let a human roll back to the prior base if a merge
later proves wrong — the receipt is the audit trail (R12).

## First-sync / no-base bootstrap (no merge base yet) (R6)

When `sync get-state` shows no `mergeBaseFlow`/`mergeBaseTracker` (a first link),
there is no 3-way ancestor — so **never run Step 2** (it would over-surface the
whole body as a conflict). Bootstrap by origin:

- **Flow-first push, no base** → pure **projection / fast-forward**: render flow →
  tracker, `writeIssue`, then snapshot (`set-merge-base` from the rendered pair +
  `set-last-synced`). Never a conflict — there is nothing on the tracker side to
  contradict.
- **Tracker-first link** ("grab issue X and spec it") → **seed the base from the
  current issue body**, first pass is **pull-only** (fold the issue into the new
  spec's sections), then snapshot. The seeded base IS the issue, so the next
  reconcile has a real ancestor and the first sync never surfaces the whole issue as
  a conflict.

The link/unlink ceremony that calls these is in [../steps.md](../steps.md) Phase 2;
this file supplies the flow-form + tracker-form snapshots `set-merge-base` requires.

## Worked fixtures (runnable without a live tracker)

These are the merge engine's oracles — each is a base + two divergent sides + the
expected outcome, exercisable by the host agent reading them (no live Linear needed;
the live round-trip is the smoke phase). They double as the acceptance evidence for
R6/R9.

### Fixture A — non-conflicting two-sided edits both survive (R6 headline)

**Base** (`mergeBaseFlow`):

~~~markdown
## Goal & Context
Add login to the dashboard.

## Acceptance Criteria
- [ ] User can sign in with email + password [R1]
~~~

**Flow-side** (a dev added an acceptance criterion):

~~~markdown
## Goal & Context
Add login to the dashboard.

## Acceptance Criteria
- [ ] User can sign in with email + password [R1]
- [ ] Failed login shows an inline error [R2]
~~~

**Tracker-side** (a PM clarified the goal in Linear):

~~~markdown
## Goal & Context
Add login to the dashboard. Must support SSO via the corporate IdP for the launch cohort.

## Acceptance Criteria
- [ ] User can sign in with email + password
~~~

**Pre-reduction:** both sides diverged → Step 2. **Merge:** Goal touched only by
tracker → take the PM's clarification; Acceptance touched only by flow → keep the
dev's new `[R2]` bullet (and do NOT strip the `[R1]` `[Rn]` tags the tracker side
happened to drop — flow owns R-IDs). **Expected merged flow body:**

~~~markdown
## Goal & Context
Add login to the dashboard. Must support SSO via the corporate IdP for the launch cohort.

## Acceptance Criteria
- [ ] User can sign in with email + password [R1]
- [ ] Failed login shows an inline error [R2]
~~~

**Oracle:** both the PM's goal clarification AND the dev's `[R2]` criterion are
present; no conflict surfaced; structural gate passes (no section dropped, both
additions present). PASS iff both survive.

### Fixture B — format translation, no invented R-IDs (R6)

**Tracker-side** free text a PM typed in Linear (folds into flow on a tracker-first
pull):

~~~markdown
## Goal
Let users export their data.

R17: also we should rate-limit the export endpoint
~~~

**Expected fold into flow** — the `R17:` line is **prose**, not a promoted
requirement:

~~~markdown
## Goal & Context
Let users export their data.

## Notes
Also we should rate-limit the export endpoint. (PM note from the tracker — not yet a
tracked requirement; promote via interview/plan if it should become one.)
~~~

**Oracle:** the `R17:` prose folded under a real flow section; **no `[R17]` R-ID was
allocated, no coverage-table row added, no source tag stamped.** PASS iff the bridge
did not invent a requirement.

### Fixture C — genuine contradiction scoped to one section (R9)

**Base** Goal: `Support OAuth login.`
**Flow-side** Goal: `Support OAuth login only — SAML is explicitly out of scope.`
**Tracker-side** Goal: `Support OAuth and SAML login.`
(Both sides also added an *identical, non-conflicting* Acceptance bullet
`- [ ] Tokens expire after 24h`.)

**Pre-reduction:** both diverged → Step 2. **Merge:** Acceptance is identical on both
sides → no conflict, fold once. Goal rewritten on both sides to mean **different
things** (flow excludes SAML; tracker includes it) → Step 4 scoped conflict.

**Oracle (the R9 proof):**
- The conflict is surfaced **scoped to the `## Goal & Context` section only** — the
  Acceptance section merged cleanly and is NOT presented as a conflict.
- It is **NOT a whole-body diff**: the human (interactive) or the deferred-sink entry
  (Ralph) references only the Goal contradiction, with the rest already merged.
- No silent overwrite: neither Goal version is written until the human picks.

```bash
# Ralph proof for Fixture C — exactly ONE scoped conflict queued, no body written:
$FLOWCTL sync defer "$SPEC_ID" \
  --summary "Goal contradicts: flow excludes SAML, tracker includes it" \
  --suggested "Human picks OAuth-only vs OAuth+SAML" --reason "genuine-contradiction"
$FLOWCTL sync receipt "$SPEC_ID" --status diverged --transport none ${EVENT:+--event "$EVENT"} \
  --note "1 scoped conflict (Goal); Acceptance merged cleanly; base unchanged"
```

PASS iff the conflict names ONLY the Goal section and the Acceptance merge is not
re-litigated.

### Fixture D — echo-loop fence (push then pull is a no-op) (R6)

After a flow→tracker push, `baseHashTracker` holds the hash of exactly what flow
pushed. A pull immediately after returns that same body (the tracker echoing flow's
write).

**Oracle:** pulled tracker body hash == stored `baseHashTracker` → **echo** →
`noop`, NOT a phantom conflict; `lastSyncedAt` does NOT advance.

```bash
# Echo detection is a hash compare against the stored fence:
STATE=$($FLOWCTL sync get-state "$SPEC_ID" --json)   # → .tracker.baseHashTracker
# pulled_hash == baseHashTracker  ⇒  emit noop, do not reconcile, do not advance state:
$FLOWCTL sync receipt "$SPEC_ID" --status noop --transport "$TRANSPORT" ${EVENT:+--event "$EVENT"} \
  --note "post-push pull matched baseHashTracker — flow's own echo, no reconcile"
```

PASS iff the matching-hash pull is a `noop` and state is unchanged.

### Fixture E — flow-owned `<!-- flow:deps -->` block excluded from divergence (fn-64, R10)

The GitHub adapter's fenced dependency block is flow's own write. A pull that
returns it MUST NOT register as a tracker-side edit, and a reconcile MUST NOT fold
it into the spec. This is the `trackerBodyForMerge` transform (Step 0.5) under test.

**Base** (`mergeBaseTracker`, already a *stripped* snapshot — Step 5 stores the
stripped form):

~~~markdown
## Goal & Context
Add login to the dashboard.
~~~

**Tracker-side** (`fetchIssue.body` — raw, with flow's just-written dep block; NO
human edit):

~~~markdown
## Goal & Context
Add login to the dashboard.

<!-- flow:deps -->
**Blocked by:** #12, #15
<!-- /flow:deps -->
~~~

**Transform:** `trackerBodyForMerge(raw)` strips the `<!-- flow:deps -->` … `<!-- /flow:deps -->`
region (markers included) → the stripped body is byte-identical to
`mergeBaseTracker`.

**Oracle:** after the transform, tracker hash == `baseHashTracker` → **echo /
no-change** → `noop`; the `**Blocked by:**` line is NEVER folded into
`## Goal & Context` (or any spec section); `lastSyncedAt` does not advance. PASS iff
the dep block causes neither a phantom divergence nor a spec edit.

> **Companion negative case (R6 collision, owned in [../steps.md](../steps.md)
> § projectDepRelations):** an edge in the `depRelations` ledger AND still in
> `depends_on_epics` but MISSING from `listIssueRelations` (a tracker user removed
> flow's relation) is evaluated BEFORE any per-side rule → `sync defer` + a
> `queued` receipt, NEVER silently recreated. The collision check belongs to the
> relation hook, not this body merge; it is cross-referenced here because both are
> the same "flow-owned, never-clobber" posture applied to relations vs body.

## Boundaries

- **This is the merge, not the transport or the status/comment layer.** Transports
  (`fetchIssue`/`writeIssue`) live in [linear-ladder.md](linear-ladder.md) (fn-52.3)
  / the GitHub adapter (fn-52.7); status who-wins + comment append are fn-52.5. This
  file consumes the normalized `issue.body` and produces a merged body.
- **No deterministic fallback merge engine.** The pre-reduction and the structural
  gate are the only mechanical steps — equality and invariants, not a text merge.
  The merge itself is the host agent's judgment (CLAUDE.md agentic-vs-deterministic).
- **State advances only on a fully successful reconcile.** A failure (404, transport
  error, gate failure, partial batch) leaves the prior base intact + an `errored`
  receipt; batch sync is item-level.
- **Never invent R-IDs / source tags** on a tracker→flow fold — the bridge projects,
  it does not author requirements.
- **Codex mirror** (sync-codex.sh) is regenerated in fn-52.9 — keep this file
  Claude-native (`AskUserQuestion`); no Codex-specific edits here.
