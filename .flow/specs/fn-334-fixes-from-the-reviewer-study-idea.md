# Fixes from the reviewer study: idea intake, parent at creation, redaction

## Goal & Context

A reviewer-model study replayed recent flow-next reviews on newer models. The reviewers raised defects in three recently shipped features, and each candidate was then verified against `main` at 9.14.1 (`47878e0a5`), most by reproduction with fakes and the rest by reading the code. 22 are still present. This spec fixes them. The study is recorded in the maintainer's evaluation repository (`studies/reviewer-model-2026-11`).

The features are idea intake from Jira Product Discovery (9.13.0), creating a tracker issue under its parent (9.13.0), and tracker rejections that carry the tracker's reason (9.14.0). Teams using idea intake are the most exposed: a failed delivery link leads to a second parent epic on the rerun, an attended run given only an idea key cannot reach the idea instructions through flowctl, and a few write paths can still reach an idea. On the redaction side, a GitLab rejection can print a token glab read from a variable flowctl does not know about.

The users are teams that start work from discovery ideas, teams that name a parent when capturing, and every GitLab and Jira user whose tracker echoes text into an error.

<!-- Source: 30% user / 30% [paraphrase] / 40% [inferred] -->

## Architecture & Data Models

Everything here repairs existing behaviour. No new config key, no new command and no new state store.

**Idea intake.**

- **Finding the parent again.** flow-next keeps no local record of which parent serves an idea, by design. A parent the first run created but failed to link is therefore invisible to a rerun, which looks only at the idea's delivery links. The parent carries a marker that names its idea, written at creation, and the settle step looks for a parent-level issue with that marker in the delivery project before it creates one. The implementer chooses the marker (a label or an issue property, whichever one Jira query can find).
- **Reading an idea by key.** The idea pointer travels in flowctl's read output, but `tracker wire read` needs the issue's durable id, and nothing turns `IDEAS-7` into one. A Jira read by display key or URL alone returns the issue, its durable id and, for an idea, the pointer. The idea path stays reachable with no added always-loaded skill text.
- **The idea write refusal** applies to the key Jira returns for the issue as well as the key requested, so an issue moved into a discovery project is refused. It also runs before any request on every write path, including `wire unready`.
- **The spec-link refusal** matches project keys without regard to case, and `sync set-tracker-id` given only a durable id, with an idea source configured, refuses and asks for `--identifier`.
- **Idea text.** Colour-tag removal leaves code and `{noformat}` blocks untouched.

**The failure envelope** carries the error's subtype as an additive field, so the subtypes the idea reference and the flowctl reference document (`several_parents`, `delivery_link_type`, `parent_mismatch`) reach the caller. This applies to every tracker command.

**Parent at creation.**

- A numeric GitLab epic id counts as set only when the create response carries that epic. Otherwise the result says the parent was not set, without an extra request.
- A GitLab parent is accepted only as ASCII digits or an epic reference. Anything else is `invalid_input`.
- The create-first pending claim and its failure details carry the parent, so a retry with the same parent links the issue already created.

**Redaction and rejection reasons.**

- Every credential glab may have used is registered for redaction before provider text can reach a message: the `GITLAB_ACCESS_TOKEN` and `OAUTH_TOKEN` variables, glab's config under `GLAB_CONFIG_DIR`, and, when the host is not known, the stored token of every configured host. Registering an extra token is harmless.
- An attachment download that Jira or GitLab rejects carries the reason like every other rejection.
- A GitLab licence refusal stays `capability` when its marker appears only in glab's diagnostic.
- The token command checks its exit status before decoding, and output that is not UTF-8 becomes a cached authentication error that names the problem without echoing the bytes.

<!-- Source: 10% user / 30% [paraphrase] / 60% [inferred] -->

## API Contracts

The failure envelope gains one field, present whenever the error has a subtype:

```json
{"success": false, "class": "conflict", "subtype": "several_parents", "error": "...", "retryable": false, "details": {}}
```

A Jira read by key, for example `flowctl tracker wire read --locator '{"display":"IDEAS-7"}'`, returns the same shape as a read by durable id, with the durable id filled in.

## Edge Cases & Constraints

- **Marker search finds several.** A marker search that finds more than one parent-level issue for the idea returns the `several_parents` conflict with all candidates, as delivery links do today.
- **Moved issue.** A write whose requested key is ordinary but whose current key is an idea is refused with the same capability error, naming both keys.
- **Linked before opt-in.** A spec linked to an idea before the idea source was configured stays linked, and every write to it is refused, as today.
- **Envelope consumers.** Callers that parse the failure envelope keep working: the field is additive.
- **Over-registration.** A token registered for redaction but never used does nothing.
- **No new requests** for teams without an idea source configured, except where the list above says a refusal now happens earlier (fewer requests).

## Acceptance Criteria

- **R1:** When `tracker idea parent` created a parent whose delivery link then failed, a rerun on the same idea reuses that parent and creates no second one. No local state is written. Errors: several parent-level issues carrying the idea's marker come back as the `several_parents` conflict with every candidate. [paraphrase]
- **R2:** A Jira `tracker wire read` given only an issue key or URL returns the issue with its durable id, and for an idea it carries the same `idea` block a durable-id read carries. No always-loaded skill file changes. Errors: an unknown key or a key from another site returns the read's existing error. [paraphrase]
- **R3:** Every Jira write path refuses an issue whose current key, as Jira returns it, is in a configured discovery project, before any request. This includes body pushes, comments, labels, status, relations, the PR link and `wire unready`, where an idea is refused instead of returning success with no change. The docs' "before any request" sentence is then true. No error surface beyond the capability refusal. [paraphrase]
- **R4:** Linking a spec to an idea is refused whatever the case of the key, and `sync set-tracker-id` with only a durable id refuses and asks for `--identifier` when an idea source is configured. No error surface beyond those refusals. [paraphrase]
- **R5:** Every tracker command's failure envelope carries `subtype` when the error has one, so `several_parents`, `delivery_link_type` and `parent_mismatch` reach the caller as documented. No error surface. [paraphrase]
- **R6:** The idea-intake reference holds capture's later sync check and retry push as well as its first push until the children exist, writes the parent's key and URL into each spec's Decision Context once the parent is settled, states that a chart run projects its own issues when `tracker.charts` is on, and tells the agent what to do when the parent was created without its description (report it and write the summary onto the parent). No error surface. [paraphrase]
- **R7:** The idea read removes colour tags outside code and `{noformat}` blocks and leaves those blocks byte-for-byte unchanged. No error surface. [paraphrase]
- **R8:** A GitLab create with a numeric epic id reports the parent as set only when the response's epic is that epic; otherwise the result says the parent was not set, with no extra request. A parent that is neither ASCII digits nor an epic reference is `invalid_input`. No error surface beyond those. [paraphrase]
- **R9:** When create-first's final record write fails after the remote create succeeded, the pending claim and the failure details carry the parent, and a retry with the same parent links the issue already created. No error surface beyond the existing `parent_mismatch` for a different parent. [paraphrase]
- **R10:** The tracker-sync reference names `sync clear` where it says how to remove a parent, and capture's tracker reference records a named parent only when the tracker bridge is active. No error surface. [paraphrase]
- **R11:** Redaction covers `GITLAB_ACCESS_TOKEN`, `OAUTH_TOKEN`, glab's stored tokens under `GLAB_CONFIG_DIR`, and every configured host's stored token when the host glab used is not known. A rejection that echoes any of them prints `<redacted>`. No error surface. [paraphrase]
- **R12:** A Jira or GitLab attachment download that is rejected carries the tracker's reason like other rejections, and a GitLab licence refusal whose marker is only in glab's diagnostic stays `capability`. No error surface. [paraphrase]
- **R13:** A token command whose output is not UTF-8 fails as a cached authentication error naming the problem, without echoing its bytes, and the exit status is checked first. No error surface beyond that error. [paraphrase]
- **R16:** A Jira or GitLab rejection whose body is nested deeply enough to exhaust recursion while the reason is collected falls back to the bare `rejected (<status>)` message; no `RecursionError` escapes the classifier. The 9.14.0 audit fix guards only the decoding step, and a body nested about 1,200 levels under empty keys still crashes on `main` (reproduced 2026-11-18). No error surface beyond the bare message. [paraphrase]
- **R17:** `tracker idea read`, `idea parent` and `idea link` refuse a key that Jira now resolves to an issue outside the configured discovery projects (an idea moved into the delivery project), with the same capability error as the other idea refusals and before any write. No error surface beyond that refusal. [paraphrase]
- **R14:** The always-loaded skill files (the flow, capture and tracker-sync entry files and the workflow and routing files they always read) do not grow, except flow's routing file by the one phrase R15 adds; the pull request reports their sizes before and after (G1). No error surface.
- **R15:** An agent that reads an idea through its own tracker connection (an MCP server) still reaches the idea reference. Flow's routing file names "an idea from a configured discovery project" in its existing list of rarer starting states, and the conditionally read rarer-states file has a row routing that state to the idea reference. The always-loaded addition is that one phrase. No error surface. [paraphrase]

Each fix gets a test that fails on `main` and passes after it, reaching the behaviour through the real entry point (G2); the verification snippets are the starting point. Tests that pin the exact failure-envelope shape gain the `subtype` field and are listed in the pull request; no other existing assertion changes. Live checks before release: a key-only read of an idea and of an ordinary issue on the Jira test site, a rerun of `idea parent` after an induced link failure, and a numeric-epic create on the local GitLab instance. The test sites and credential lookups are in the gitignored notes file `.flow/tmp/tracker-live-checks.md`. Docs updated in the same change: the tracker-sync reference, the flowctl reference (envelope `subtype`, key-only read), the idea-intake reference and its codex copy, and the changelog under Unreleased.

## Boundaries

- No change to how a concurrent second intake of the same idea behaves. The spec promises safety for a sequential rerun only. [paraphrase]
- No GitLab epic resolution for a project that moved groups (a narrow case the review raised). [inferred]
- No change to the retry-key formula in the create-first reference. A key made without the parent already fails safely. [inferred]
- No change to unattended behaviour on an idea. Goal and backlog runs still stop, as 9.13.0 documents. [inferred]

## Decision Context

The marker on the parent keeps idea intake free of local state, which is what made a second run safe in the first place. The alternative, a local record of created parents, was rejected for 9.13.0 for that reason.

The idea path is reached two ways. R2 makes flowctl's own read work from a bare key: in the end-to-end run of 9.13.0, one fresh session tried a key-only read on its own and another found the reference by searching the plugin. R15 covers agents that read Jira through an MCP server and never see flowctl's output. The maintainer decided on 2026-11-18 to accept that cost, about seven words in the always-loaded routing file, in place of 9.13.0's zero-growth rule, because otherwise the feature silently does not happen for those teams.

The envelope's `subtype` is additive and applies to every tracker command because the documentation already promises those subtypes. Leaving them out of the output made the documented branches unreachable.

Findings the review raised that are not defects on `main`, and are left alone: a parented create-first keyed without its parent (fails closed), a race between two simultaneous intakes (outside the spec's sequential promise), and hardening notes about incomplete Jira metadata.

<!-- Source: 20% user / 20% [paraphrase] / 60% [inferred] -->

## Strategy Alignment

- Tracker determinism: every fix is mechanical plumbing in the tracker package or a sentence in the reference read on the idea path. Routing and judgement stay with the agent. [strategy:Tracker determinism]
