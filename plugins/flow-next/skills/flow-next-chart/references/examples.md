# Chart - native examples and adaptive traces

Examples are **illustrative**. They show how free-form steering maps to guarded operations. They are **not** a mandatory phase order or checklist. Adaptive traces below are possible journeys only.

Each native example lists: inferred operation, read-back point, evidence/consent boundary, terminal `CHART_VERDICT`.

Use plain hyphens only. Never embed literal destructive shell command strings or realistic secrets - describe risky operations in prose.

- [Native examples](#native-examples)
- [Four adaptive traces (illustrative - not phases)](#four-adaptive-traces-illustrative---not-phases)
- [Flags (automation only - not required vocabulary)](#flags-automation-only---not-required-vocabulary)
- [Automation flag map (not required vocabulary)](#automation-flag-map-not-required-vocabulary)
- [Conversational equivalents for common flags](#conversational-equivalents-for-common-flags)
- [Verdict grammar reminder](#verdict-grammar-reminder)

---

## Native examples

### 1. "This is too broad to capture; help me find the first decision worth making."

| Field | Value |
|---|---|
| **Inferred operation** | Chart mode: bounded Grounding Snapshot -> propose Outcome + smallest breadth-first frontier + parked unknowns + cost -> create if consequential unknowns exist |
| **Read-back point** | Before `flowctl chart create --initial-map-file`: Outcome, known facts with citations, frontier titles/types, parked unknowns, attended/unattended cost |
| **Evidence/consent boundary** | Charting resolves nothing. No imported fact becomes a D-ID. User approves the map shape; unattended frontier may be offered for later parallel work invocations only |
| **Terminal verdict** | `CHART_VERDICT=NO_WORK chart=<id> decision=- reason="chart created; frontier offered; chart mode resolves nothing"` |

If grounding finds nothing consequential: create nothing; `CHART_VERDICT=NO_WORK chart=- decision=- reason="no consequential unknowns; capture or direct route"`.

---

### 2. "Here is the outcome and what we already know. Ground this in the repo, show the smallest initial frontier, and do not turn background facts into decisions."

| Field | Value |
|---|---|
| **Inferred operation** | Chart mode with user-supplied Outcome + known facts forced into Notes lane; Grounding Snapshot ordered over prompt, strategy/implementation, relevant specs/charts, connected sources |
| **Read-back point** | Snapshot: candidate Outcome; known_facts with safe ref/revision; conflicts_or_staleness as uncertainty; smallest_visible_frontier; parked_unknowns; cost - then consent before create |
| **Evidence/consent boundary** | Background stays under Notes with citations. Never fabricate resolved D-IDs or acceptance-criterion tags. Conflicts/staleness stay uncertainty. Resolve nothing in chart mode |
| **Terminal verdict** | `CHART_VERDICT=NO_WORK chart=<id> decision=- reason="grounded map persisted; background cited under Notes only"` |

---

### 3. "We know the storage choice. Record it as cited background and show what uncertainty disappears; do not invent a resolved decision or source tag."

| Field | Value |
|---|---|
| **Inferred operation** | Chart or work re-anchor: fold storage choice into `## Notes` with citation; recompute which proposed frontier items or parked unknowns collapse; do **not** call `chart resolve` to invent history |
| **Read-back point** | Show Notes line with evidence reference; list uncertainties removed vs still open; if map changes require create/wire, read back before persist |
| **Evidence/consent boundary** | Cited background is not a D-ID and not `[user]`/`[paraphrase]`/`[inferred]`/`[strategy:*]`. fn-148 verified/inferred grammar is out of scope (STOPPED). No fake ledger line |
| **Terminal verdict** | Chart mode: `CHART_VERDICT=NO_WORK chart=<id> decision=- reason="storage noted as cited background; frontier narrowed without fabricated resolve"`. Work mode after real resolve of a different D-ID only if one was claimed: `CHART_VERDICT=RESOLVED chart=<id> decision=<D> reason="..."` |

---

### 4. "Use the cheapest real-world check for viability."

| Field | Value |
|---|---|
| **Inferred operation** | Work mode: `chart frontier` sole selection; prefer smallest unattended `probe` or `eval` (or `research` if measurement is impossible) over prototype/interview |
| **Read-back point** | When type is ambiguous between probe/eval/research, ask once; otherwise claim and run. Present measured result before resolve |
| **Evidence/consent boundary** | Claim before work. One D-ID only. Unsafe outputs stored by reference + safe summary. Attended types not selected when a cheaper unattended check answers viability |
| **Terminal verdict** | `CHART_VERDICT=RESOLVED chart=<id> decision=<D> reason="viability settled via cheapest probe"` |

---

### 5. "The prototype changed direction. Preserve the old assumption and redraw."

| Field | Value |
|---|---|
| **Inferred operation** | Work mode on the prototype (or follow-on) decision: ensure asset attached; record human reaction; `chart resolve --answer-file ... --supersedes <prior D-ID>` after read-back; recompute frontier; sharpen newly visible decisions |
| **Read-back point** | Name superseded D-ID(s), new answer gist, cascade (`depends_on` open dependents lose claims; resolved dependents get replacement D-IDs unless `--keep-dependents`) |
| **Evidence/consent boundary** | Prior answer stays immutable; ledger line struck-through, never deleted. Prototype code stays evidence - not implementation. Human reaction required for prototype resolve |
| **Terminal verdict** | `CHART_VERDICT=RESOLVED chart=<id> decision=<Dnew> reason="prototype reversed prior assumption; D3 superseded; frontier redrawn"` |

---

### 6. "Continue this chart from this decision link: `<stored tracker URL>`."

| Field | Value |
|---|---|
| **Inferred operation** | Re-entry: probe `flowctl chart locate <selector>` (local ledger only). On success, read back canonical D-ID/title/record link; re-anchor chart; if open decision, pin and enter work mode. If locate missing, ask for local chart id - no mutation |
| **Read-back point** | Always read back local id + title + record link before claim/work. Resolved/superseded URLs show history + frontier options - never silent reassignment |
| **Evidence/consent boundary** | No remote search, no title inference, no create-on-miss. Failures mutate nothing. Parent URL -> chart status/frontier; open decision URL -> that D-ID only |
| **Terminal verdict** | After work: normal one-decision verdict. Locate-only history view: `CHART_VERDICT=NO_WORK chart=<id> decision=<D> reason="historical decision; no new work selected"`. Locate failure: `CHART_VERDICT=BLOCKED chart=- decision=- reason="locator failed local ledger; no mutation"` |

---

### 7. "Show whether this should become one spec or two; do not build yet."

| Field | Value |
|---|---|
| **Inferred operation** | Briefing path (or pre-briefing status if not yet briefable): cluster resolved decisions; default N=1; propose split only if disjoint; write proposal file; `chart briefing --proposal-file` only after confirmation. **Do not** implement code |
| **Read-back point** | Clusters + one-line rationale each + shared_context D-IDs; user confirms merge/split/override before emit |
| **Evidence/consent boundary** | Chart never writes `.flow/specs/`. Forced briefing while open/parked is draft-only and not capture-ready. Build/plan/work are out of scope |
| **Terminal verdict** | Final: `CHART_VERDICT=COMPLETE chart=<id> decision=- reason="briefing proposal confirmed; B1 emitted for capture"`. Not briefable: `CHART_VERDICT=BLOCKED chart=<id> decision=- reason="open or parked items remain; cannot final-brief"` |

---

### 8. "Keep this as one chart despite the size warning"

| Field | Value |
|---|---|
| **Inferred operation** | Chart mode after ceiling refusal: prefer narrow/split; on explicit insist, warn with count + `chart.maxDecisions` + consequence; consent read-back of reason; then `chart create --initial-map-file ... --force-size --reason "<consent>"` |
| **Read-back point** | Exact decision count, configured ceiling, audit fields (actor, timestamp, reason), and that later sharpening may grow further |
| **Evidence/consent boundary** | No force without warning + explicit consent. Override is audited on the create transaction. Charting still resolves nothing |
| **Terminal verdict** | `CHART_VERDICT=NO_WORK chart=<id> decision=- reason="over-ceiling create after consent; force-size audited"` |

Without consent after warning: create nothing; `CHART_VERDICT=NO_WORK chart=- decision=- reason="size ceiling held; narrow or split offered"`.

---

### 9. "Make flow-next more deterministic - chart it"

| Field | Value |
|---|---|
| **Inferred operation** | Chart-mode refusal before grounding spend: the prompt names a **direction**, not a destination. No end state means no stateable Outcome, no boundary that can rule anything out of scope, and a map that never closes. Create nothing |
| **Read-back point** | Say plainly what is missing (the end state), then offer exactly two routes: narrow to one effort whose arrival is nameable (invite the narrowed prompt), or `/flow-next:prospect` when the real ask is which determinism effort to pick |
| **Evidence/consent boundary** | Do not silently chart a guessed narrowing - the user picks the effort. Do not chart "all of determinism" behind a `--force-size` override; the ceiling is not the problem here, the missing destination is |
| **Terminal verdict** | `CHART_VERDICT=NO_WORK chart=- decision=- reason="direction not destination; narrow to one effort or run prospect"` |

Same prompt, narrowed by the user to *"make `flowctl list` output byte-identical across machines"*: now the destination is nameable and the route is genuinely unknown - chart it.

---

### 10. "We reopened that chart and finished the extra work - brief it again"

| Field | Value |
|---|---|
| **Inferred operation** | Briefing path on a reopened chart: confirm it is briefable again, reuse or re-confirm the cluster proposal, `chart briefing --proposal-file`. The reopen is a new epoch, so the **identical** proposal mints the next B-ID instead of echoing the staled one |
| **Read-back point** | Before emit: which B-IDs the reopen staled, the clusters being re-briefed, and that the new package supersedes rather than restores. After emit: the minted B-ID plus what it supersedes - `fn-1 briefing B2 status=final (supersedes stale B1)`, `supersedes_stale: ["B1"]` under `--json` |
| **Evidence/consent boundary** | Draft-vs-final is recomputed from the live chart: open or parked items still mean `--force` draft only, never an inherited `final`. Staled `produced_specs[]` links stay stale - whether specs built from B1 still hold is a human call. Chart still writes nothing under `.flow/specs/` |
| **Terminal verdict** | `CHART_VERDICT=COMPLETE chart=<id> decision=- reason="re-briefed after reopen; B2 emitted for capture"` |

The staled B1 stays on disk and in the ledger. A re-brief supersedes history; it never rewrites it.

---

## Four adaptive traces (illustrative - not phases)

These are **possible** journeys. Real charts re-draw after every answer. Do not treat the steps as a fixed ceremony.

### Trace A - Research-led (illustrative)

1. User: oversized multi-tenant idea; chart mode grounds repo + strategy.
2. Frontier opens with unattended `research` (provider limits) and a parked billing unknown.
3. Separate work invocation claims research D-ID, scout returns cited facts, resolve + sharpen removes the parked key into an interview decision.
4. Later attended interview settles product constraint; frontier shrinks.
5. Briefing N=1 when briefable; capture next.

Sample terminal lines across invocations:

```text
CHART_VERDICT=NO_WORK chart=fn-140 decision=- reason="chart created; research frontier offered for parallel work"
CHART_VERDICT=RESOLVED chart=fn-140 decision=fn-140.D1 reason="provider limits cited; parked billing sharpened"
CHART_VERDICT=NEEDS_HUMAN chart=fn-140 decision=fn-140.D4 reason="attended interview; unattended driver wrote no answer"
CHART_VERDICT=COMPLETE chart=fn-140 decision=- reason="briefing B1 emitted; hand off to capture"
```

### Trace B - Prototype reversal with supersession (illustrative)

1. Chart includes prototype "tenant switcher mental model" blocked by a prior research premise.
2. Work: research resolves; prototype becomes frontier; attach throwaway mock; human reacts "wrong direction".
3. Resolve prototype with reaction; `--supersedes` the earlier product assumption D-ID; cascade invalidates open dependents' claims.
4. Newly visible interview/probe decisions appear via sharpen; redraw continues.
5. Superseded ledger lines remain struck-through in the eventual briefing.

Sample terminals:

```text
CHART_VERDICT=RESOLVED chart=fn-140 decision=fn-140.D2 reason="research premise closed; prototype unblocked"
CHART_VERDICT=RESOLVED chart=fn-140 decision=fn-140.D3 reason="prototype reversed D2 assumption; cascade reported"
```

### Trace C - Skip-chart (illustrative)

1. User pastes a clear idea with stated intent, boundaries, and no consequential unknowns.
2. Grounding Snapshot confirms repo already answers the few technical points; nothing to park.
3. Skill stops without create; recommends capture or direct path.

```text
CHART_VERDICT=NO_WORK chart=- decision=- reason="no consequential unknowns; capture or direct route"
```

### Trace D - Multi-spec split (illustrative)

1. Chart walks decisions spanning two disjoint product surfaces discovered only mid-route.
2. At briefable state, agent proposes N=2 clusters with rationales; one auth decision listed in `shared_context`.
3. User confirms; `briefing --proposal-file` emits index + two cluster files.
4. Capture runs per cluster; `chart link-spec` per successful spec (owned by capture, not this skill).

```text
CHART_VERDICT=COMPLETE chart=fn-140 decision=- reason="multi-spec briefing B1 confirmed; shared_context preserved"
```

---

## Flags (automation only - not required vocabulary)

| Flag / form | Purpose |
|---|---|
| `--status` | Status mode - render only |
| `--decision <n>` | Pin a D-ID for work mode |
| `--json` on every `flowctl chart` subcommand | Machine envelope for drivers |
| `chart create --initial-map-file` / `--force-size --reason` | Atomic chart + ceiling override (audited) |
| `chart resolve --answer-file` / `--sharpen-file` / `--supersedes` / `--keep-dependents` | Close + optional sharpen/cascade; `--sharpen-file` also carries a dated `notes_append` correction when the answer disproves a grounding note (unattended: only on direct contradiction, never speculative); unrecognized keys fail the whole resolve |
| `chart attach-asset --asset-file` | Safe artefact while open |
| `chart briefing --proposal-file` / `--force` | Confirmed split proposal; force is draft-only; after a `chart reopen` the same proposal mints the next B-ID |
| `chart claim` / `release-claim [--break-stale --reason]` | Claims; no silent expiry |
| `chart locate <selector>` | Local ledger re-entry (may be absent - degrade) |

## Automation flag map (not required vocabulary)

| Human intent | flowctl |
|---|---|
| Start discovery on an idea | `chart create --title --outcome --initial-map-file` |
| Keep one chart past ceiling | same + `--force-size --reason` after consent |
| What's next | `chart frontier` / `chart show` |
| Work this decision | `chart claim` then route then `resolve` / `out-of-scope` |
| Park a vague unknown | `chart park-question --body-file` |
| Wire edges after create | `chart wire-decision` |
| Attach prototype evidence | `chart attach-asset --asset-file` |
| Sharpen after answer | `resolve --sharpen-file` |
| Correct a disproved note | `resolve --sharpen-file` (`notes_append`) |
| Reverse prior answer | `resolve --supersedes` |
| Brief for capture | `chart briefing --proposal-file` |
| Re-enter from tracker URL | `chart locate` (local only; degrade if missing) |

---

## Conversational equivalents for common flags

| Automation form | Conversational equivalent |
|---|---|
| `/flow-next:chart "idea"` | "Chart out the multi-tenant migration" |
| `/flow-next:chart fn-140` | "Work the next decision on the billing chart" |
| `/flow-next:chart fn-140 --decision 3` | "Continue from the tenancy prototype decision" |
| `/flow-next:chart fn-140 --status` | "What's left to decide on fn-140?" |
| `create --force-size --reason` | "Keep this as one chart despite the size warning" |
| `resolve --supersedes D3` | "That prototype changed the direction; preserve the old assumption" |
| `briefing --proposal-file` | "Show whether this is one spec or two; do not build yet" |
| `chart locate <url>` | "Continue from this tracker link" |

---

## Verdict grammar reminder

```text
CHART_VERDICT=<RESOLVED|BLOCKED|NEEDS_HUMAN|COMPLETE|NO_WORK> chart=<id> decision=<D> reason="<one line>"
```

Every work invocation ends with exactly one such line. Chart/status modes emit one line for driver uniformity (`decision=-` when none claimed).
