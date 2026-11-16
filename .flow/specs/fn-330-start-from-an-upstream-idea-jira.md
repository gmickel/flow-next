# Start from an upstream idea (Jira Product Discovery first)

## Goal & Context

Some teams run product discovery in their tracker. Product management, services and sales enter requirements as ideas, product management scores and prioritises them, and an approved idea becomes a parent issue in the delivery project with child issues cut under it. Cutting the children by hand is slow, and hand-drawn dependencies between them end up cyclic.

flow-next already starts from a single tracker issue. This spec adds the step before that. The person points flow at an idea where ideas live, and flow reads it and routes it as it routes any other starting point. A clear idea goes to capture. An oversized or unclear one goes to chart first and then to capture. Capture's split proposal cuts it into independent specs, with the dependency cycle check that shipped in 9.7.0.

The result in the tracker is one parent issue for the idea, one child issue per spec under it, the dependencies between the children, and a delivery link from the parent back to the idea, so the person who owns the idea sees delivery progress on it.

Jira Product Discovery is the first idea source. Its ideas are ordinary Jira issues of type Idea in a discovery project, so the existing Jira transport reads them.

The feature is off until a team configures an idea source. A team that configures nothing gets no new behaviour, no extra requests and no extra skill text in any session.

<!-- Source: 65% user / 25% [paraphrase] / 10% [inferred] -->

## Architecture & Data Models

**Ownership.** The idea belongs to the people who run discovery. flow-next reads it and adds one delivery link to it, and writes nothing else there. The parent issue belongs to the tracker and has no spec. Each child issue belongs to one spec, as every linked issue does today. flow-next stores no idea state of its own. Which parent serves an idea is read from the idea's delivery links each time.

**Opt-in.** One config key under the Jira tracker settings lists the discovery projects, since a team can run several next to one delivery project. Absent or empty means the feature is off. With it set, an issue key in a listed project is an idea, which costs no request to decide.

**The path.**

1. The person gives attended flow an idea key or URL.
2. flow reads the idea's summary, description, comments and issue links through the existing Jira read.
3. flow routes on the idea's content with the route matrix it already uses. The idea's text and comments are source material for capture, next to anything the person says in the session.
4. Capture drafts the spec or proposes a split, the person chooses, and the cycle check runs on the proposed edges as today.
5. After the specs are saved, flow settles the parent. An idea that already has one delivery-linked parent-level issue in the delivery project uses it. Otherwise flow creates one, at the hierarchy level above the configured issue type, titled with the idea's summary and carrying a short summary and the idea's reference.
6. flow links the parent to the idea with the discovery product's delivery link type, when that link is not there yet.
7. Each spec records the parent, and its issue is created under it by the parent-on-creation capability this spec depends on. Dependencies are projected as today.

**Where the instructions live.** The steps above live in one reference file that an agent reads only on this path. The path is reached without adding words to any always-loaded skill file. When an idea source is configured and the issue read is an idea, flowctl's read output says so and names the reference to read.

**flowctl.** Three mechanical operations run through flowctl, because flowctl holds the credentials and each must be safe to repeat: the idea read with its links, the creation of a parent-level issue that has no spec, and the delivery link. Their code loads only when one of them runs.

<!-- Source: 35% user / 25% [paraphrase] / 40% [inferred] -->

## API Contracts

Config, one optional key, absent by default:

```json
"tracker": { "perTracker": { "ideaProjectKeys": ["IDEAS", "RESEARCH"] } }
```

The delivery link on Jira Cloud is an issue link of the discovery product's own link type. flowctl finds the type by listing the site's link types and taking the one whose name contains `Polaris` and whose two descriptions are `implements` and `is implemented by`. The parent issue is the inward issue and the idea is the outward issue, so the idea reads "is implemented by" the parent. A check on a Jira Cloud site on 2026-11-16 found the type named `Polaris work item link` and confirmed that direction. The type's id differs per site and its name has changed before, so flowctl never hard-codes either.

A link created this way appears in the idea's delivery view in Jira's own interface, with the parent's status and the progress bar. A person confirmed that on the same site on the same day. Over the REST API the idea's delivery progress and delivery status fields stay null, so flow-next never reads progress from them.

Reading an idea needs Browse on the discovery project, and linking needs Link issues. In that check the API token of the discovery project's own administrator could browse, comment and link, and held no right to create, edit or transition ideas. The design therefore needs nothing beyond read and link.

Each child spec's Goal & Context quotes the part of the idea it serves and gives the idea's key and URL. Its Decision Context names the sibling specs, the idea and the parent issue.

The close of the run prints the idea, the parent issue (created or reused), each child spec with its issue, and the dependency edges.

<!-- Source: 15% user / 15% [paraphrase] / 70% [inferred] -->

## Edge Cases & Constraints

- **An idea with no requirement text.** A fresh idea can hold only its template headings. flow tells the person the idea has no content to build from and asks, and never invents criteria from a title.
- **Several delivery-linked parents.** flow asks the person which one to use. A linked issue outside the delivery project, or below parent level, is not reused and is named in the close.
- **No delivery link type on the site.** flowctl checks for the type before it creates anything. Zero or several matches stop the run with what it found, and nothing is created.
- **The link fails after the parent exists.** The run reports the parent's key and the exact retry, and continues with the children. The link is the product owner's view of progress and no build step waits on it.
- **The person aborts at the split.** No tracker write has happened by then.
- **The same idea again.** A second run finds the delivery-linked parent and creates no second one. Capture's duplicate check covers the specs.
- **Wrong tracker.** The key set on a tracker other than Jira, or on Jira Data Center, is a capability error when the path is used. Jira Product Discovery exists on Jira Cloud only.
- **Unattended runs.** `flow --auto --from-issue` given an idea key behaves as in 9.12.0. The idea is not in the delivery project's ready lane, so the run stops before any write.
- **The idea is read-only apart from the link.** flow-next never edits an idea's text, fields or status and never comments on it.
- **A named idea is never linked as a spec's own issue.** Without this, the capture push would write the spec body into the idea.

<!-- Source: 10% user / 20% [paraphrase] / 70% [inferred] -->

## Acceptance Criteria

- **R1:** With the idea source configured, attended flow given an idea key or URL reads the idea's summary, description and comments and routes on that content with the existing route matrix: a clear idea to capture, an oversized or unclear one to chart and then capture. Errors: an idea the account cannot read stops with the transport error and writes nothing; an idea with no requirement text is put to the person as a question and no criterion is invented. [paraphrase]
- **R2:** Capture uses the idea's text and comments as source, and its split proposal, the person's choice and the cycle check on the proposed edges work as in 9.12.0. Each child spec quotes the part of the idea it serves and gives the idea's key and URL. Errors: a cycle in the proposed edges is shown as a path and settled before any spec is written, as today. [paraphrase]
- **R3:** After the specs are saved, the idea has exactly one parent issue in the delivery project: the delivery-linked parent-level issue it already had, or a new one at the hierarchy level above the configured issue type. Errors: several candidates are put to the person as a question; a second run on the same idea creates no second parent. [paraphrase]
- **R4:** The parent issue carries a delivery link to the idea, of the discovery product's own link type, so the idea reads "is implemented by" the parent. An existing link is left as it is. Errors: no matching link type, or several, stops the run before anything is created and names what was found; a failed link request is reported with the parent's key and the retry, and the children are still created. [paraphrase]
- **R5:** Each spec's issue is created as a child of the parent issue through the parent-on-creation capability, and the dependency edges between the children are projected as in 9.12.0. Errors: those of that capability and of dependency projection, unchanged. [paraphrase]
- **R6:** flow-next writes nothing to the idea except the delivery link, and never links a spec to the idea as the spec's own issue. No error surface. [inferred]
- **R7:** With no idea source configured, every flow, capture and tracker-sync run behaves as in 9.12.0 and makes no request it did not make before. `flow --auto` in every mode, including `--from-issue`, behaves as in 9.12.0 whether or not an idea source is configured. No error surface. [paraphrase]
- **R8:** The idea source configured on a tracker other than Jira Cloud is a capability error when the path is used, naming the limit. No error surface beyond that. [inferred]
- **R9:** The instructions for this path live in a reference file read only on this path. The pull request reports the size of every always-loaded skill file before and after (the flow, capture and tracker-sync skill entry files and the workflow and routing files they always read), in bytes and approximate tokens, and none grows. The reported numbers are the evidence. No test freezes a size (G1, G2). No error surface.
- **R10:** `flowctl ready` and `flowctl next` on a repository with no idea source configured import no module they did not import in 9.12.0, and their measured wall time before and after shows no regression beyond run-to-run noise. The code for the idea read, the parent creation and the delivery link loads only when one of those operations runs. The pull request reports the measurements. No error surface.
- **R11:** The existing tracker-sync tests pass with their assertions unchanged. No error surface. [paraphrase]

Tests drive the three flowctl operations through the fake executor, including the reuse of an existing parent, the missing link type and the repeated run, and pin the unchanged modes as contracts (G2). Docs updated in the same change: the tracker-sync reference (an idea-intake section and the config key), the config schema, the pipeline variations page, the skills reference, the teams guide (a discovery-to-delivery pattern), the flow, capture and tracker-sync skill references, the README, the changelog under Unreleased, and the matching pages on flow-next.dev. [inferred]

**Live check before release.** It needs a Jira Cloud site that has a discovery project and a software project with an epic-level issue type, reached the way tracker sync already reaches Jira: `JIRA_BASE_URL` and `JIRA_EMAIL`, with the token from `JIRA_API_TOKEN` or `tracker.perTracker.tokenCommand`. The account needs Browse and Link issues on the discovery project and create rights on the software project.

- Start from an idea with real requirement text and from one that is broad enough to split. Check the route each takes.
- Check that the first run creates one parent, links it to the idea and creates each child under it, and that a second run on the same idea reuses the parent.
- Check an idea that already has a delivery-linked parent made by hand in Jira's interface.
- A person opens the idea in Jira and confirms the parent shows in its delivery view.

The maintainer's test site, projects, fixtures and credential lookup are in the gitignored notes file `.flow/tmp/tracker-live-checks.md`. Fixture issues carry `[idea-intake live check]` in their titles. A contributor without that file uses their own site.

## Boundaries

- No idea source other than Jira Product Discovery. Linear initiatives and projects, GitHub issues or discussions labelled as ideas, and GitLab epics are later candidates. [paraphrase]
- No unattended idea intake. Starting from an idea is attended, and the person's invocation is the consent. [inferred]
- No reading of discovery insights, which the Jira REST API does not return, and no use of an idea's scoring fields (impact, effort, goals, roadmap). [inferred]
- No write to the idea beyond the delivery link: no status move, no comment, no field or text edit. [inferred]
- No status sync for the parent issue. It has no spec, and closing it stays with the team. [inferred]
- No delivery project on Jira Data Center reached from a Cloud discovery project through a connector app. [inferred]
- No view on the child issue of which repositories or components the implementation touched. [paraphrase]
- No tracker issues for flow tasks. Tasks stay flow-local, as today. [paraphrase]

## Decision Context

This spec and `fn-329-set-a-parent-issue-when-creating` were captured together from one request. That spec lets any created issue be born under a parent and stands on its own. This one depends on it for the child issues.

The parent issue is a tracker issue with no spec. The alternative was an umbrella spec for the idea with the children depending on it, the shape goal mode uses. It was rejected because the parent holds no work of its own, nobody would build or review that spec, and Jira already derives a parent's progress from its children. Reading the idea's delivery links to find the parent also removes the need for any local record of which parent serves which idea, which is what makes a second run safe.

An idea always gets a parent issue, including an idea that becomes a single spec. One rule matches the hierarchy these teams already use and keeps the delivery link pointing at one kind of issue.

Idea intake is attended. Capture never splits without the person choosing, and an unattended run would need both a consent act on the idea and a licence to split on its own. Neither exists today, and the people this serves want help while they cut the work, with the choice staying theirs.

The idea source is a config key, and detection is a comparison of the issue key's project. Detecting a discovery project by reading its type from the tracker would cost every tracker-issue start a request, including for teams that have no discovery project.

The three flowctl operations are plumbing with no judgment in them. They go through flowctl because the credentials and the Jira transport live there, and because each reads before it writes, which is what keeps a repeated run from creating a second parent or a second link.

The maintainer confirmed these choices on 2026-11-16: a parent issue with no spec, a parent for single-spec ideas too, attended intake only, and the routing pointer carried in flowctl's read output.

<!-- Source: 25% user / 15% [paraphrase] / 60% [inferred] -->

## Strategy Alignment

- Tracker determinism: reading an idea, creating the parent and writing the delivery link are mechanical and repeatable, so they live in the tracker package. Routing the idea, cutting it into specs and choosing among several candidate parents stay with the host agent and the person. [strategy:Tracker determinism]
- Spec-driven team patterns: the handover from discovery to delivery becomes one more documented pattern in the teams guide. [strategy:Spec-driven team patterns]
