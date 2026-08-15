---
name: flow-next-tracker-sync
description: Project a flow-next spec to a tracker issue (Linear, GitHub, GitLab, Jira) and reconcile two-way. Use when asked to sync to a tracker. NOT plan-sync.
user-invocable: false
allowed-tools: Read, Bash, Grep, Glob, Write, Edit
---

# flow-next-tracker-sync

The flow spec is the source of truth and quality layer. The tracker is a
co-editable projection. Tracker activity never starts agents or changes Flow
task state.

## Load the reached path

Read [steps.md](steps.md) for the operation sequence and
[references/adapter-interface.md](references/adapter-interface.md) for the
normalized contract. Load only references needed by the reached path:

- Body comparison or conflict:
  [references/body-merge.md](references/body-merge.md).
- Status projection: [references/status-sync.md](references/status-sync.md).
- Comment or question-valve content:
  [references/comments-sync.md](references/comments-sync.md).
- Hybrid identifiers: [references/identity.md](references/identity.md).
- Linear transport shape: [references/linear-ladder.md](references/linear-ladder.md),
  then only the reached MCP or GraphQL reference.
- GitHub, GitLab, or Jira transport shape: the matching provider reference only.

Never load an unselected provider merely because another reference links it.

## Deterministic boundary

`flowctl tracker` owns tracker transport, normalization, credentials, retries,
capability degradation, lifecycle ordering, receipts, and atomic local state.
The skill supplies only approved semantic inputs and reacts to the structured
result. Do not reconstruct provider requests in skill prose or shell.

Use the lifecycle facade for event-driven projection:

```bash
FLOWCTL="${CODEX_HOME:-$HOME/.codex}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
$FLOWCTL tracker sync "$SPEC_ID" --op "$OP" --event "$EVENT" \
  --flow-file "$FLOW_FILE" --body-file "$BODY_FILE" \
  --comments-file "$COMMENTS_FILE" --source-body-file "$SOURCE_BODY_FILE"
```

Pass only flags legal for the selected operation. [steps.md](steps.md) lists
the file contract. For discovery, create-first, link, unlink, status, relation,
attachment, and direct wire maintenance, use the matching `flowctl tracker`
verb. `flowctl tracker --help` is the executable source of truth.

Every command returns one JSON object on stdout. Success has `success: true`,
`data`, `degraded`, and `probe`. Failure has `success: false`, `class`, `error`,
`retryable`, and typed `details`. Branch on `class`, never provider text.

## Exactly five judgment surfaces

These are the only five surfaces intentionally retained in the host agent:

1. **MCP rung.** MCP tools exist only in the host tool environment, so flowctl
   cannot invoke them. The agent may perform the explicitly requested Linear
   MCP action, then hands the returned identity to `tracker persist-external`.
2. **Discovery ceremony.** Choosing a tracker, project or team, and enabling
   lifecycle events is an ambiguous one-time product decision. The agent
   surfaces detected choices and asks before persisting configuration.
3. **Body-merge conflict adjudication.** A three-way body conflict is semantic
   because equivalent prose, intent, and requirement meaning cannot be resolved
   from hashes or syntax alone. The agent adjudicates only conflicting sections,
   while flowctl owns snapshots and atomic persistence.
4. **Comment content synthesis.** Lifecycle comments communicate human context.
   The caller decides what the comment should say and supplies a stable
   occurrence identity as the first file line, `evidence=<token>`. Flowctl
   rejects missing/placeholder evidence, strips that line from visible content,
   and owns marker dedup, transport, and the receipt.
5. **Recovery routing from a structured error.** A typed conflict,
   `external_action_required`, or non-retryable capability result can require a
   user choice, an MCP continuation, a local correction, or a defer. The agent
   selects that next action from the structured envelope instead of parsing
   error prose.

No other tracker operation is agentic. In particular, request construction,
pagination, provider field mapping, status policy, relation projection,
comment dedup, credential selection, retry timing, and receipt writes remain
deterministic.

## Discovery ceremony

The bridge is off until the user confirms it. Surface available and unavailable
provider signals, the proposed project or team, and lifecycle defaults. Resolve
environment overrides before stored configuration. If the destination is
ambiguous, ask. If the user declines, write nothing.

After confirmation, use `flowctl config set` for the selected provider and
`flowctl tracker resolve` to persist `tracker.resolved`. Credentials remain in
the environment. Never copy credentials into config, a prompt, argv, receipt,
or error note.

Linear MCP is discovery/create only. All later shell-reachable operations use
the deterministic GraphQL route. If an MCP create returns only a display key,
`tracker persist-external` resolves and stores its durable identity.

## Operating rules

- One Flow spec maps to one tracker issue. Tasks remain Flow-local.
- Tracker-first creation uses the hybrid identifier rules in `identity.md`.
  Never rename an existing Flow-first spec.
- Callers retain their bridge-active and `perEvent` gates. An inactive bridge
  remains silent because the lifecycle facade is not invoked.
- Event-driven callers use `tracker sync`, not granular tracker verbs.
- Comment text and merged body text travel through mode `0600` temporary files,
  never argv. Delete temporary files after the call.
- The facade writes one aggregate receipt. Do not add a second receipt.
- A pull or reconcile may update Flow prose, but never Flow task status.
- Dependency projection is additive and provenance-led. Never delete or
  recreate a user-controlled relation without evidence that Flow owns it.
- `inactive` is a silent no-op for lifecycle callers.
- `rate_limited` is retried only when the envelope says `retryable: true`.
- `auth`, `unresolved`, `stale_id`, `conflict`, `capability`, and
  `external_action_required` follow the recovery table in `steps.md`.
- In Ralph or a forked lifecycle call, queue a decision that needs a person.
  Never attempt an interactive prompt from the fork.

## Boundaries

This skill is projection, not coordination. `/flow-next:tracker-sync` is
distinct from `/flow-next:sync`. Flow state remains authoritative. Provider
wire details live in deterministic Python; the Markdown references document
their shapes so reviewers can inspect the contract without copying executable
transport recipes into prompts.
