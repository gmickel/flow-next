---
name: flow-next-chart
description: Decision-map discovery for one oversized/unclear idea before capture. Triggers on /flow-next:chart with an unshaped idea, chart id, decision pin, --status, or stored tracker URL. Prompt-first adaptive loop - ground, chart a frontier, resolve one D-ID per invocation, brief for capture.
user-invocable: false
allowed-tools: AskUserQuestion, Read, Bash, Grep, Glob, Write, Edit, Task
---

# Chart - decision-map discovery (pre-capture)

**Read [workflow.md](workflow.md) for routing and the mode dispatch table.** It routes to exactly one mode reference per invocation (chart / work / briefing-reopen / re-entry); status mode and the safety recap stay inline there. Native prompts, adaptive traces, and the full flag tables: [references/examples.md](references/examples.md).

Takes **one unshaped idea that is too big for a single capture session and wrapped in unknowns**, and finds the route by resolving **one decision at a time** until the effort can be captured as one or more specs. Unit of work is a **decision** (D-ID), not a build task. Chart never writes a spec and never sets `ready`; output is a briefing handed to `/flow-next:capture`.

**Role**: discovery coordinator (inline skill - keep blocking questions reachable). Host agent owns grounding, interpretation, frontier judgment, evidence-route dispatch, prototype presentation, attended consent, re-charting, and the terminal verdict. flowctl owns atomic create/claim/resolve/scope/briefing/store mutations.

## Preamble

**CRITICAL: flowctl is BUNDLED - NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks (here and in `workflow.md`) use `$FLOWCTL`:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

**Inline skill (no `context: fork`)** - keeps `AskUserQuestion` available for read-back consent and attended routes. Subagents cannot call blocking question tools. For read-only scouts use `Task` with `subagent_type: Explore` (or the host's generic read-only dispatch with Edit/Write disallowed when Explore is unavailable). On portable hosts without `AskUserQuestion`, fall back to a plain-text numbered prompt with a final `Other - type your own answer` option. (sync-codex.sh rewrites AskUserQuestion to a plain-text numbered prompt in the Codex mirror.)

## Prompt-first contract

Natural language is the primary control surface. Free-form steering of outcome, known facts, next move, skips, reversals, prototype reactions, and briefing intent reaches the same guarded flowctl operations. Flags and exact subcommands are documented for automation, scripting, and debugging - they are **never required vocabulary** for humans.

On every invocation:

1. Infer the intended **mode** and operation from `$ARGUMENTS` + conversation.
2. Ask a blocking question **only** when two interpretations would materially change the chart, cost, or consent boundary.
3. Read back any state-changing interpretation before persisting.
4. Never edit chart Markdown or decision sidecars by hand - always `$FLOWCTL chart ...`.

## Modes (disambiguate by argument)

| Invocation shape | Mode | Behavior |
|---|---|---|
| free-form idea / "chart out ..." | **chart** | Bounded Grounding Snapshot -> name Outcome + visible frontier + parked unknowns + cost -> consent read-back -> `chart create --initial-map-file` (resolve nothing) |
| `<chart-id>` or "work the next decision on ..." | **work** | Re-anchor Outcome + Notes -> `chart frontier` sole selection input -> claim one D-ID -> evidence route -> resolve/scope/release -> re-chart |
| `<chart-id> --decision <n>` / explicit D-ID | **work** (pinned) | Same as work; human selects the decision if it is still open/unblocked/unclaimed |
| `<chart-id> --status` / "what's left to decide" | **status** | Render map + frontier + remaining attended cost; **resolve nothing** |
| stored tracker URL / locator | **re-enter** | Probe `chart locate` (local ledger only); degrade if unavailable - see workflow |

Plain-language equivalents reach the same modes (R17).

## Verdict grammar (exact)

Every **work** invocation ends with **exactly one** greppable line and nothing after it:

```
CHART_VERDICT=<RESOLVED|BLOCKED|NEEDS_HUMAN|COMPLETE|NO_WORK> chart=<id> decision=<D> reason="<one line>"
```

| Verdict | When |
|---|---|
| `RESOLVED` | One D-ID closed via resolve or out-of-scope; frontier recomputed |
| `BLOCKED` | Claim conflict, graph/store refusal, or no actionable path without human repair |
| `NEEDS_HUMAN` | Stored `attendance:attended` decision reached by an unattended driver - **no answer write** |
| `COMPLETE` | Chart briefable (no open decisions, no parked questions) after this tick, or briefing emitted |
| `NO_WORK` | Empty frontier, skip-chart (no consequential unknowns), status-only, or chart mode finished without resolving |

Chart mode and status mode also print one terminal line so host `/loop`/`/goal` drivers can parse uniformly (`decision=-` when no D-ID was claimed).

**Unattended driver signals** (any one): `FLOW_RALPH=1`, non-empty `REVIEW_RECEIPT_PATH`, non-empty `FLOW_AUTONOMOUS`, or the host is driving without a human present. Interactive terminal sessions are attended.

## Decision types = evidence routes

| Type | Attendance | Resolves by |
|---|---|---|
| `research` | unattended | Scout reads docs / primary sources / knowledge bases; returns a fact |
| `probe` | unattended | Measure or reproduce against the real system |
| `eval` | unattended | Bake-off / benchmark on real fixtures; winner + why |
| `prototype` | **attended** | Throwaway artefact + human reaction (hard gate) |
| `interview` | **attended** | Conversation, one question at a time (default for product judgment) |
| `task` | **explicit** at create | Manual work that only unblocks a decision (not implementation smuggling) |

Attendance is stored and validated by flowctl for five types; `task` requires `--attendance attended|unattended`. Cost estimates and unattended gates read the stored field, never prose.

## Invariants (hard)

- **One invocation = one D-ID = one claim = one verdict.** Independent unattended frontier decisions fan out only as **separate** invocations. No batch or mixed-result grammar.
- **Charting resolves nothing.** Chart mode ends after map + first decision records + cost exist.
- **`flowctl chart frontier` is the sole selection input** for work mode (optional human pin still must appear on that frontier).
- **Claim before any work.** Refuse double-claim; release with note on stop; crash leaves claim visible.
- **Attended hard gate.** Unattended driver + `attendance:attended` -> persist no answer, release or leave claim per workflow, terminate `NEEDS_HUMAN`.
- **Prototype lifecycle.** Create/import one scoped throwaway artefact -> `chart attach-asset` while open -> present exact safe reference/revision -> record human reaction -> resolve/supersede. Interruption leaves asset + open D-ID resumable. Never rebuild, never infer approval, never promote prototype code into implementation.
- **No nameable destination -> STOP.** Chart's premise is *destination known, route unknown*. A theme or direction ("make X more Y") has no end state to state as an Outcome and no boundary to rule anything out of scope. Offer narrowing to one effort with a stateable end state, or `/flow-next:prospect` when the real ask is which effort to pick; create nothing.
- **No consequential unknowns -> STOP.** Recommend `/flow-next:capture` or the smaller direct route; create nothing.
- **Over `chart.maxDecisions` (default 12).** Offer narrow Outcome or split first. Pass `--force-size --reason` only after explicit warning + consent read-back.
- **Provenance lanes stay separate.** Grounding facts get citations under `## Notes` and never become D-IDs or acceptance-criterion trailing tags (`[user]` / `[paraphrase]` / `[inferred]` / `[strategy:*]`). fn-148 closed STOPPED with no verdict - **include NO verified/inferred fact grammar**.
- **Unsafe evidence by reference.** Never embed secrets or literal destructive shell command strings in chart artefacts; store a safe redacted summary + approved path/HTTPS reference. Describe such operations in prose only.
- **Context discipline.** Status/frontier navigation loads compact metadata only. Full decision bodies and assets load only for the selected D-ID or briefing.
- **Skill never edits Open Questions, edges, or sharpened decisions directly.** Use park/remove/wire/resolve `--sharpen-file` / create `--initial-map-file`.

## Flags (automation only - not required vocabulary)

Documented for scripting; the full flag table, the human-intent -> flowctl map, and conversational equivalents live in [references/examples.md](references/examples.md). Only `--status` (status mode) and `--decision <n>` (pin a D-ID for work mode) affect routing; `--json` is available on every `flowctl chart` subcommand.

## Workflow

Execute [workflow.md](workflow.md):

0. **Route** - parse args, probe locator for URL-like selectors, choose mode.
1. **Mode dispatch** - read only the routed mode's reference:
   - **Chart mode** - Grounding Snapshot (ordered) -> read-back Outcome/frontier/cost -> create or stop.
   - **Work mode** - re-anchor -> frontier -> claim -> evidence route -> resolve/scope/release -> sharpen -> re-chart -> one verdict; supersession when steering says the direction changed.
   - **Briefing handoff / reopen** - when briefable, propose clusters, confirm, `briefing --proposal-file`, hand to capture.
2. **Status mode** - compact show + frontier + cost; no mutations (inline in workflow.md).

## Forbidden

- Writing under `.flow/specs/` or mutating a spec's `ready` flag.
- Answering attended decisions without the human side of the exchange.
- Turning imported background into fabricated resolved D-IDs or acceptance-criterion tags.
- Shipping verified/inferred fact grammar (fn-148 did not land guidance).
- Precomputing a complete discovery route or treating adaptive traces as mandatory phases.
- Embedding literal destructive shell command strings or realistic secrets in chart bodies, answers, briefings, or this skill's examples.
- Silent claim expiry, silent supersession cascade, or silent prototype-to-implementation promotion.
- Setting `context: fork` (blocking questions must stay reachable).
