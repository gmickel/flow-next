# tracker-sync round-trip spikes — dev archive

De-risking spike harnesses for the tracker-sync adapters, moved out of the runtime
skill references (they are one-time transport probes for adapter development, not
material any sync run reads). Each pushes a canonical flow body to a real issue,
pulls it back, and diffs — plus the cross-tracker reconcile-parity check. Run one
when standing up or debugging an adapter transport. The Jira adapter never
carried a spike (no action needed).

**Not runtime material** — nothing in the skill tree links here for execution;
the adapter references carry a breadcrumb only.

## Contents

- [Linear — round-trip spike (per rung)](#linear--round-trip-spike)
- [GitHub — transport-blind proof / round-trip spike](#github--transport-blind-proof--round-trip-spike)
- [GitLab — transport-blind proof / round-trip spike](#gitlab--transport-blind-proof--round-trip-spike)

---

# Linear — round-trip spike

Source: `plugins/flow-next/skills/flow-next-tracker-sync/references/linear-ladder.md` (archived verbatim).

## Round-trip spike (acceptance #1 — run FIRST, before fn-52.4)

A de-risking spike that exercises the transport in isolation: **push a flow body
to a real Linear issue, then pull it back unchanged** — format translation only,
**no merge**. It surfaces transport bugs (OAuth, tool-name drift, GraphQL
auth/asymmetry, identifier-vs-UUID, complexity rate limits) BEFORE the .4 merge
engine is built on top.

> **Live-verification status (this environment).** A live Linear round-trip needs
> real credentials (a registered MCP server OR a `LINEAR_API_KEY` against a real
> workspace). Those are unavailable in the build environment, so the **live
> execution is deferred to the post-PR smoke-testing phase** the maintainer
> drives. The spike below is a complete, runnable procedure with an explicit
> success/fail oracle; the MCP tool names + GraphQL wire facts it depends on are
> verified and pinned (see linear-mcp.md / linear-graphql.md). Run it once per
> rung the target environment exposes.

### Spike procedure (per rung)

Fixture: a small canonical flow body the round-trip must preserve byte-for-byte
after a normalize→render cycle (headings, a checklist, a fenced block, a link —
the structures most likely to be mangled by a markdown round-trip):

~~~markdown
## Goal
Round-trip fixture for the Linear transport spike.

## Acceptance
- [ ] item one
- [x] item two (done)

## Notes
A fenced block:

```
exact text — must survive verbatim
```

A [link](https://example.com) and an inline `code` span.
~~~

Steps:

1. **Build the body** — write the fixture above to `/tmp/spike-flow-body.md`.
2. **Push (create)** via the active rung's `writeIssue` (no `id` ⇒ create):
   - MCP: `save_issue(team:<team>, title:"flow spike", description:<body>)`
   - GraphQL: `issueCreate(input:{teamId:<uuid>, title:"flow spike",
     description:<body>})`
   Capture the returned `{ id (UUID), identifier (WOR-N), url }`.
3. **Pull back** via `fetchIssue(id)` (use the **UUID**, not `WOR-N`):
   - MCP: `get_issue(id:<uuid>)` → `.description`
   - GraphQL: `query{ issue(id:<uuid>){ description } }`
   Write the returned body to `/tmp/spike-pulled-body.md`.
4. **Oracle (success/fail):**
   ```bash
   # Idempotent format translation ⇒ byte-identical round-trip.
   if diff -u /tmp/spike-flow-body.md /tmp/spike-pulled-body.md; then
     echo "SPIKE PASS — round-trip preserved the body"
   else
     echo "SPIKE FAIL — transport mangled the body; see diff above"
   fi
   ```
   A non-empty diff is a transport bug to fix in the rung file BEFORE fn-52.4 —
   e.g. Linear normalizing list markers, collapsing blank lines, or rewriting the
   fenced block. (If Linear's renderer canonicalizes markdown in a stable,
   loss-less way, record the exact canonical form as the fixture's expected
   output so .4 reconciles against *that*, not the raw input.)
5. **Repeat on the second rung** if the environment exposes both — the two pulled
   bodies must match each other (parity), not just their own inputs.
6. **Cleanup:** delete or archive the spike issue (MCP: `save_issue(id, state:
   "Canceled")` or the workspace's archive; GraphQL: `issueArchive(id)`).

The spike writes a receipt like any sync run:
`sync receipt <spec> --status noop --transport <rung> --note "round-trip spike: PASS|FAIL"`
(status `noop` because the spike performs no real reconciliation — it is a
transport probe, not a sync of a tracked spec; no `--event` either — the spike is
a manual diagnostic, never a lifecycle touchpoint).

---

# GitHub — transport-blind proof / round-trip spike

Source: `plugins/flow-next/skills/flow-next-tracker-sync/references/github.md` (archived verbatim).

## Transport-blind proof / round-trip spike (acceptance #3 — run FIRST)

The R13 guarantee: **the same reconcile path over `gh` fixtures yields merge
output identical to the Linear path.** Two checks:

### A. Round-trip spike (transport in isolation — no merge)

Push a flow body to a real GitHub issue, then pull it back — format translation
only. Surfaces transport bugs (auth, `--body-file` escaping, number-vs-node-id,
markdown round-trip) BEFORE relying on reconcile.

> **Live-verification status (this environment).** A live GitHub round-trip needs
> a real `GH_TOKEN` against a real repo with issue write access — unavailable in
> the build environment, so the **live execution is deferred to the post-PR
> smoke-testing phase** the maintainer drives. The spike below is a complete,
> runnable procedure with an explicit success/fail oracle; the `gh` flags + JSON
> fields it depends on are verified and pinned above (gh ≥ 2.x). Run it once.

Fixture (the same canonical flow body the Linear spike uses — headings, a
checklist, a fenced block, a link — the structures most likely to be mangled):

~~~markdown
## Goal
Round-trip fixture for the GitHub transport spike.

## Acceptance
- [ ] item one
- [x] item two (done)

## Notes
A fenced block:

```
exact text — must survive verbatim
```

A [link](https://example.com) and an inline `code` span.
~~~

Steps:

1. **Build the body** — write the fixture to `/tmp/spike-flow-body.md`.
2. **Push (create)** via `writeIssue` (no id ⇒ create), body via `--body-file -`:
   ```bash
   NUM=$(gh issue create -R "$REPO" --title "flow spike" \
           --body-file /tmp/spike-flow-body.md \
           | sed -E 's@.*/issues/([0-9]+).*@\1@')
   ```
3. **Pull back** via `fetchIssue(number)`:
   ```bash
   gh issue view "$NUM" -R "$REPO" --json body -q .body > /tmp/spike-pulled-body.md
   ```
4. **Oracle (success/fail):**
   ```bash
   if diff -u /tmp/spike-flow-body.md /tmp/spike-pulled-body.md; then
     echo "SPIKE PASS — round-trip preserved the body"
   else
     echo "SPIKE FAIL — gh transport mangled the body; see diff above"
   fi
   ```
   A non-empty diff is a transport bug to fix here BEFORE relying on reconcile —
   e.g. GitHub normalizing trailing whitespace or line endings. (If GitHub
   canonicalizes markdown in a stable, loss-less way, record that exact canonical
   form as the fixture's expected output so .4 reconciles against *that*.)
5. **Cleanup:** `gh issue close "$NUM" -R "$REPO" --reason "not planned"` (or
   delete via `gh issue delete "$NUM" -R "$REPO" --yes` where the token allows).

The spike writes a receipt like any sync run:
`sync receipt <spec> --status noop --transport gh --note "round-trip spike: PASS|FAIL"`
(status `noop` — a transport probe, not a sync of a tracked spec; no `--event`
either — the spike is a manual diagnostic, never a lifecycle touchpoint).

### B. Cross-tracker reconcile parity (the actual R13 check)

Feed the **same normalized fixtures** through reconcile twice — once with the
GitHub adapter's output structs, once with the Linear adapter's — and assert the
merge output is identical:

```bash
# Pseudo-procedure (reconcile is agentic — fn-52.4/.5 — and consumes structs):
#   1. Take a flow body + a base snapshot + a tracker-side edit.
#   2. Produce the normalized `issue`/`comment`/`status` structs TWICE:
#        - via the GitHub mapping tables above (open/closed+reason+status: label)
#        - via the Linear mapping (state{name type})
#      Construct both so they represent the SAME logical state (e.g. GitHub
#      OPEN+`status:in-progress` ≡ Linear `started`/`in-progress`).
#   3. Run the UNCHANGED reconcile core (body-merge.md / status-sync.md /
#      comments-sync.md) on each struct set against the same base.
#   4. Oracle: the two merge outputs are identical (same merged body, same
#      who-wins status, same comment dedup). Any difference is a mapping bug in
#      an adapter — NOT a reconcile change. Reconcile is never edited to make a
#      transport pass.
```

This is the load-bearing R13 assertion: identical reconcile output across Linear
and GitHub fixtures, with the reconcile core touched in neither task.

---

# GitLab — transport-blind proof / round-trip spike

Source: `plugins/flow-next/skills/flow-next-tracker-sync/references/gitlab.md` (archived verbatim).

## Transport-blind proof / round-trip spike — run FIRST

The R13 guarantee: **the same reconcile path over `glab` fixtures yields merge
output identical to the GitHub/Linear path.** Two checks:

### A. Round-trip spike (transport in isolation — no merge)

Push a flow body to a real GitLab issue, then pull it back — format translation
only. Surfaces transport bugs (auth, `description=@-` escaping, iid-vs-global-id,
project encoding, GFM round-trip) BEFORE relying on reconcile.

> **Live-verification status.** The endpoints/limits below were **smoke-tested live
> 2026-06-28** against gitlab.com (throwaway project `gmickel/fnsmoke`, permanently
> deleted after) — create/read/update/close, GFM body, labels (incl. a `flow:<id>`
> back-ref), `listOpenIssues` by label, notes, MR-link note, and the Premium-403
> relation degrade. A *fresh* round-trip needs a real `GITLAB_TOKEN` against a
> project with issue write access; the `glab`/REST flags + JSON fields it depends on
> are verified and pinned above. Run it once per environment.

Fixture (the same canonical flow body the GitHub/Linear spikes use — headings, a
checklist, a fenced block, a link — the structures most likely to be mangled):

~~~markdown
## Goal
Round-trip fixture for the GitLab transport spike.

## Acceptance
- [ ] item one
- [x] item two (done)

## Notes
A fenced block:

```
exact text — must survive verbatim
```

A [link](https://example.com) and an inline `code` span.
~~~

Steps:

1. **Build the body** — write the fixture to `/tmp/spike-flow-body.md`.
2. **Push (create)** via `writeIssue` (no id ⇒ create), body via stdin:
   ```bash
   IID=$(printf '%s' "$(cat /tmp/spike-flow-body.md)" | glab api --method POST \
           "projects/$ENC/issues" --raw-field "title=flow spike" --field "description=@-" \
           | jq -r '.iid')
   ```
3. **Pull back** via `fetchIssue(iid)`:
   ```bash
   glab api "projects/$ENC/issues/$IID" | jq -r '.description' > /tmp/spike-pulled-body.md
   ```
4. **Oracle (success/fail):**
   ```bash
   if diff -u /tmp/spike-flow-body.md /tmp/spike-pulled-body.md; then
     echo "SPIKE PASS — round-trip preserved the body"
   else
     echo "SPIKE FAIL — glab transport mangled the body; see diff above"
   fi
   ```
   A non-empty diff is a transport bug to fix here BEFORE relying on reconcile —
   e.g. GitLab normalizing trailing whitespace or line endings. (If GitLab
   canonicalizes GFM in a stable, loss-less way, record that exact canonical form as
   the fixture's expected output so reconcile reconciles against *that*.)
5. **Cleanup:** `glab api --method PUT "projects/$ENC/issues/$IID" --field
   "state_event=close"` (or delete via `glab api --method DELETE
   "projects/$ENC/issues/$IID"` where the token allows).

The spike writes a receipt like any sync run:
`sync receipt <spec> --status noop --transport glab --note "round-trip spike: PASS|FAIL"`
(status `noop` — a transport probe, not a sync of a tracked spec; no `--event` — the
spike is a manual diagnostic, never a lifecycle touchpoint).

### B. Cross-tracker reconcile parity (the actual R13 check)

Feed the **same normalized fixtures** through reconcile twice — once with the GitLab
adapter's output structs, once with the GitHub adapter's — and assert the merge
output is identical:

```bash
# Pseudo-procedure (reconcile is agentic — fn-52.4/.5 — and consumes structs):
#   1. Take a flow body + a base snapshot + a tracker-side edit.
#   2. Produce the normalized `issue`/`comment`/`status` structs TWICE:
#        - via the GitLab mapping tables above (opened/closed + status: label)
#        - via the GitHub mapping (open/closed + reason + status: label)
#      Construct both so they represent the SAME logical state (e.g. GitLab
#      opened+`status:in-progress` ≡ GitHub OPEN+`status:in-progress`).
#   3. Run the UNCHANGED reconcile core (body-merge.md / status-sync.md /
#      comments-sync.md) on each struct set against the same base.
#   4. Oracle: the two merge outputs are identical (same merged body, same
#      who-wins status, same comment dedup). Any difference is a mapping bug in an
#      adapter — NOT a reconcile change. Reconcile is never edited to make a
#      transport pass.
```

This is the load-bearing R13 assertion: identical reconcile output across GitLab and
GitHub fixtures, with the reconcile core touched in neither task.
