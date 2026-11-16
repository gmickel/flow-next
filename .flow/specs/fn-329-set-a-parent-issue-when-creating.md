# Set a parent issue when creating tracker issues

## Goal & Context

Teams that keep a hierarchy in their tracker (a Jira epic with stories under it, a Linear parent issue, a GitLab epic) get a flat issue from flow-next today. The create call sends project, type, title and description, and nothing that places the issue under its parent. The workaround is to create the child by hand in the tracker under the right parent and then link the spec to it.

This spec lets a spec name its parent issue, so the issue flow-next creates is born under that parent. It covers the creation done for a single captured spec and for every child of a capture split. The tracker owns the parent from then on, and no later sync sends, changes or clears it.

The users are developers and product people who capture work that belongs to an existing piece of planned work, and who want the board to show it there without a second step.

Teams that name no parent see no change. No request gains a field and no extra request is made.

<!-- Source: 55% user / 30% [paraphrase] / 15% [inferred] -->

## Architecture & Data Models

**Ownership.** The parent relation is tracker state. flow-next holds one creation input per spec and nothing else. The spec's tracker block gains an optional `parent` field holding the parent's identifier as the tracker displays it. Absent means unmanaged, the rule the Linear Project fields already follow. Unlike those fields, `parent` is read at issue creation only. After the spec is linked, no code path reads it again.

**Where it is honoured.** Every path that creates an issue for a spec reads the field: the spec-keyed create, the create that the first push runs for an unlinked spec, the create-first path that makes the issue before the spec exists, and the payload flow-next hands to the agent when the Linear MCP route creates the issue. Chart projection keeps its own parent and child issues and is not touched.

**Per tracker.**

| Tracker | What the parent is | How it is sent | Added cost when a parent is set |
|---|---|---|---|
| Jira Cloud | An issue one hierarchy level above the created type, for example an epic above a story or task | `parent` in the create payload | One field |
| Jira Data Center and Server | Not supported in this spec | Refused before the create | None |
| Linear | A parent issue | `parentId` in the create input | One field |
| GitHub | Not supported in this spec | Refused before the create | None |
| GitLab | An epic (Premium and Ultimate tiers) | `epic_id` in the create payload | One field, plus one read when the epic is given as a reference that must be resolved to its id |

The Linear Project and Project Milestone fields keep their current behaviour. A Linear sub-issue created without a Project inherits its parent's Project on Linear's side.

**Capture.** When the person names a parent for the work ("under PROJ-12", "as sub-issues of ENG-40"), capture records it on each spec it writes, and a split gives every child the same parent unless the person says otherwise. A named parent is never linked as a spec's own issue. This guidance lives in the capture and tracker-sync references that load only when the tracker bridge is active.

<!-- Source: 30% user / 20% [paraphrase] / 50% [inferred] -->

## API Contracts

Spec JSON, tracker block, one optional field:

```json
"tracker": { "parent": "PROJ-12" }
```

The value is the parent's display identifier: a Jira key, a Linear identifier, a GitLab epic id or reference. flowctl records it through an option on the existing create and link commands, so nobody edits spec JSON by hand. The create-first command takes the same option, because no spec exists yet when it runs, and the value is written to the spec when it is minted.

The create result reports the parent it set.

A spec whose tracker block has no `parent` produces the same request bytes as 9.12.0 on every tracker.

<!-- Source: 10% user / 20% [paraphrase] / 70% [inferred] -->

## Edge Cases & Constraints

- **The tracker rejects the parent.** A parent that does not exist, sits at the wrong hierarchy level, belongs to a project the tracker does not allow, or that the account cannot see comes back as the tracker's own error. The create is one request on each supported tracker, so no issue exists afterwards.
- **GitHub.** flow-next projects a dependency on GitHub by making the blocked issue a sub-issue of its blocker, and a GitHub issue takes one parent. A named parent would push every dependency edge of that issue onto the manual queue, so a parent recorded on GitHub is refused. Dependency projection on GitHub behaves as in 9.12.0.
- **Later syncs.** Body, title, status, label, assignee, relation and pull-request-link writes carry no parent field on any tracker. A parent that a person sets, moves or removes in the tracker survives every sync operation. A check on a Jira Cloud site on 2026-11-16 created a story under an epic in one request, and a later summary and description update left the parent in place. The same day on a self-managed GitLab 19.5 instance with epics, an issue created with `epic_id` kept its epic through a title and description update and a label write.
- **Unlink.** `sync unlink` resets the spec's tracker block as today. It does not touch the tracker.
- **Bridge inactive.** With no tracker configured, capture records nothing and says in one line that no tracker is configured.

<!-- Source: 15% user / 25% [paraphrase] / 60% [inferred] -->

## Acceptance Criteria

- **R1:** On Jira Cloud, a spec with a parent recorded creates its issue as a child of that parent in the one create request, in team-managed and company-managed projects. Errors: a parent that is missing, at the wrong hierarchy level or not visible to the account returns Jira's error and creates no issue. [paraphrase]
- **R2:** On Linear, a spec with a parent recorded creates its issue as a sub-issue of that parent in the one create mutation, on the token route and in the payload handed to the MCP route. The Project and Project Milestone fields behave as in 9.12.0. Errors: an unknown parent returns Linear's mutation error and creates no issue. [paraphrase]
- **R3:** On GitHub, a parent recorded on a spec is refused before any create with a capability error that names the limit, and issue creation and dependency projection without a parent behave as in 9.12.0. No error surface beyond that refusal. [paraphrase]
- **R4:** On GitLab, a spec with a parent recorded creates its issue in the named epic in the one create request. Errors: a tier without epics, or an unknown epic, returns GitLab's error and creates no issue. [paraphrase]
- **R5:** A parent recorded for a tracker or deployment this spec does not cover (Jira Data Center and Server) is refused before any create with a capability error that names the limit. The parent is never dropped silently. No error surface beyond that refusal. [inferred]
- **R6:** The create-first path and the create that the first push runs for an unlinked spec both honour the recorded parent, and the minted spec carries it. Errors: a create-first retry after a partial failure links to the recorded issue and creates no duplicate, as today. [inferred]
- **R7:** With no parent recorded, every create request on every tracker is byte-identical to 9.12.0 and no request is added. A parent costs one field on Jira Cloud and Linear, and one field plus at most one read on GitLab. No error surface. [paraphrase]
- **R8:** No sync operation after creation (push, pull, reconcile, comment, status, labels, assignee, dependency relations, pull-request link) sends a parent field or removes a parent, on any tracker. A parent set or changed by a person in the tracker is still in place after each of those operations. No error surface. [paraphrase]
- **R9:** When the person names a parent, capture records it on the spec it writes, a split records it on every child, and the named parent is never linked as a spec's own issue. Errors: with the tracker bridge inactive capture records nothing and says so in one line. [paraphrase]
- **R10:** The pull request reports the size of every always-loaded skill file before and after (the flow, capture and tracker-sync skill entry files and the workflow files they always read), in bytes and approximate tokens, and none grows. The reported numbers are the evidence. No test freezes a size (G1, G2). No error surface.
- **R11:** `flowctl ready` and `flowctl next` on a repository with no parent recorded and no tracker configured import no module they did not import in 9.12.0, and their measured wall time before and after shows no regression beyond run-to-run noise. The pull request reports both measurements. No error surface.
- **R12:** The existing tracker-sync tests pass with their assertions unchanged. No error surface. [paraphrase]

Tests drive the create path of each adapter through the fake executor and assert the request each one sends with and without a parent, and that no later operation sends one (G2). Docs updated in the same change: the tracker-sync reference (the tracker block table and the per-tracker sections), the flowctl reference, the teams guide, the capture and tracker-sync skill references, the changelog under Unreleased, and the matching pages on flow-next.dev. [inferred]

**Live checks before release.** Each tracker is reached the way tracker sync already reaches it, so the checks need no new setup.

- **Jira Cloud:** `JIRA_BASE_URL` and `JIRA_EMAIL`, with the token from `JIRA_API_TOKEN` or `tracker.perTracker.tokenCommand`. Needs a software project with an epic. Check that a story is created under the epic in one request, and that the parent is still there after a body push and a status transition.
- **Linear:** `LINEAR_API_KEY`, or the token command. Check that an issue is created as a sub-issue of a named parent, that the parent is still there after a body push and a state change, and that a spec carrying both a parent and the Project fields gets both.
- **GitLab:** an existing `glab auth login` session for the host, or `GITLAB_TOKEN`. Needs a group with epics (Premium or Ultimate). Check that an issue is created in the named epic in one request, and that the epic is still there after a description push and a label write.
- **GitHub and Jira Data Center:** check the refusal, which needs no live site.

The maintainer's test sites, projects, fixtures and credential lookups are in the gitignored notes file `.flow/tmp/tracker-live-checks.md`. Fixture issues carry `[parent-link live check]` or `[idea-intake live check]` in their titles. A contributor without that file uses their own instances.

## Boundaries

- No parent support on Jira Data Center and Server in this spec. Their REST API still places a story in an epic through the Epic Link custom field. [inferred]
- No GitLab parent other than an epic. Task-under-issue hierarchy goes through the work items GraphQL API, which the GitLab adapter does not use. [inferred]
- No parent on GitHub in this spec, and no change to how GitHub dependencies are projected. GitHub gets its parent in later work that also moves its dependencies to GitHub's native blocked-by relation, so an issue can keep both. [paraphrase]
- No reconcile of the parent after creation, and no config default that puts every spec of a repository under one parent. [inferred]
- No tracker issues for flow tasks. Tasks stay flow-local, as today. [paraphrase]
- No creation of parents here. Creating a parent issue from an upstream idea belongs to the idea-intake spec that depends on this one. [paraphrase]
- No view on the issue of which repositories or components the implementation touched. [paraphrase]

## Decision Context

This spec and `fn-330-start-from-an-upstream-idea-jira` were captured together from one request. This one stands on its own and ships first. That one creates a parent issue from an upstream idea and depends on this one for the child issues.

The field follows the Linear Project precedent: a per-spec value in the tracker block, absent means unmanaged, and an absent value changes no request. That precedent reconciles the Project on every push. The parent is sent at creation only, because the requirement is that later syncs never overwrite a parent set in the tracker, and a value flow-next never sends again cannot overwrite anything.

A repository-wide default parent in config was rejected. A parent is a property of one piece of work, and a default would put unrelated specs under one epic.

GitHub is left out. It is the one tracker where a parent collides with existing behaviour: dependencies are projected there as sub-issues, an issue takes one parent, and a child under a named parent would lose its dependency edges to a manual queue. Shipping that combination is worse than refusing the parent. GitHub's native blocked-by relation removes the collision, and moving dependency projection to it changes behaviour for every existing GitHub user, so it is its own piece of work.

Jira Data Center and GitHub are refused instead of dropped, the rule the Linear-only Project fields already follow on other trackers. A silent drop would leave a story outside its epic with nothing telling the person.

The maintainer confirmed these choices on 2026-11-16: no GitHub parent in this spec, a refusal on Jira Data Center, and GitLab's one field plus at most one read as an acceptable cost.

<!-- Source: 30% user / 20% [paraphrase] / 50% [inferred] -->

## Strategy Alignment

- Tracker determinism: the parent is a mechanical create-time field with no judgment in it, so it lives in the tracker package. Which parent a piece of work belongs under stays with the person and the host agent. [strategy:Tracker determinism]
