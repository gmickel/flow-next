# capture — chart-briefing ingestion (fn-135) (loaded on demand)

> Loaded ONLY when the conversation or `$ARGUMENTS` references a chart briefing — a path under
> `.flow/charts/*-briefing*.md`, an explicit B-ID (`B1`, `B2`, …), or a chart id with a published
> briefing. A capture with no chart in play never reads this file.

Contents:

- [Ingestion contract](#ingestion-contract) — the six ingestion rules (detect / admission / override / provenance / write order / retry)
- [0.5b — Chart briefing admission](#05b--chart-briefing-admission) — the fail-closed refusal and the risk override
- [1.2b — Chart briefing evidence](#12b--chart-briefing-evidence) — what lands in the evidence surface
- [2.2 — Chart provenance separation](#22--chart-provenance-separation) — the tagging boundary
- [5.2 — Chart handoff](#52--chart-handoff) — `link-spec` order + retry rules
- [Provenance lanes](#provenance-lanes--do-not-collapse) and [forbidden behaviors](#forbidden-behaviors-chart-rows)

---

## Ingestion contract

Capture treats an admitted briefing as **attributable evidence**, not as pre-tagged acceptance criteria:

1. **Detect** the briefing input early (Phase 1 evidence). Read the index (and cluster file when multi-spec). Record chart id, B-ID, cluster key (if any), D-ID links, and approved asset references.
2. **Admission (fail closed):** ordinary capture **REFUSES draft or stale briefings**. A forced draft (`status: draft`) is never treated as final. A stale B-ID (after `chart reopen` or supersession of linked D-IDs) is refused by default.
3. **Explicit risk override only:** to admit a draft or stale briefing, the user must name the unresolved or invalidated D-IDs and the agent must **read back the exact risk** before write. The override never promotes a forced draft into a final briefing and never rewrites chart history.
4. **Provenance separation (load-bearing):**
   - Chart/B-ID/cluster/D-ID evidence and approved assets go into `## Decision Context` / evidence sections as **links and references** — never with trailing `[user]` / `[paraphrase]` / `[inferred]` / `[strategy:<track>]` tags.
   - The four source tags apply **only** to acceptance criteria capture **newly authors**. Never retag existing criteria. A criterion derived from an unattended resolved D-ID is **not** automatically `[user]`.
   - Do **not** introduce verified/inferred fact or decision grammar (fn-148 closed STOPPED — no verdict; it licenses nothing here).
5. **Write order after approval:** `spec create` → `spec set-plan` → `flowctl chart link-spec <chart> --briefing <B> --spec <S> --decisions <D,...> [--cluster <k>]`. Call `link-spec` **only after** each successful spec creation. Decline records nothing and leaves the chart resumable.
6. **Retry / partial multi-spec:** on retry, first check `produced_specs[]` (and existing specs) for this B-ID+cluster identity; if a link already exists, link/use that spec instead of minting a duplicate. Partial multi-spec capture records only successful links and resumes the failed cluster without duplicating the first. Shared-context D-IDs stay attributable in each handoff but become acceptance requirements only where read-back confirms the target spec needs that guarantee.

Done when: the briefing was admitted or refused on its own `status` (no forced draft treated as final, no stale B-ID admitted without a read-back naming every unresolved D-ID); its chart id, B-ID, cluster key, D-ID links, and approved assets all appear in the evidence surface as untagged links; and every spec this run created carries exactly one matching `chart link-spec` call, made after its own successful `spec create` + `spec set-plan`.

---

## 0.5b — Chart briefing admission

When the conversation or `$ARGUMENTS` names a chart briefing input — a path matching `.flow/charts/*-briefing*.md`, an explicit B-ID (`B1`, `B2`, …), or a chart id whose sidecar lists briefings — resolve it before drafting:

```bash
# Example probes (agent-owned paths; type literal paths, never shell vars across prompt turns):
# Read the briefing markdown, and the chart sidecar for status of that B-ID:
#   .flow/charts/<chart-id>.json  -> briefings[].id / .status (final|draft|stale)
#   .flow/charts/<chart-id>-briefing.md
#   .flow/charts/<chart-id>-briefing-<k>.md   # multi-cluster
```

**Refuse (ordinary capture, fail closed):**

- Briefing `status: draft` (forced incomplete briefing) — never treat a forced draft as final.
- Briefing `status: stale` (after `chart reopen` or supersession of linked D-IDs).

```text
Error: chart briefing <B> is <draft|stale> and is refused for ordinary capture.
Unresolved / invalidated items: <named D-IDs or parked questions from the briefing>.
A forced draft can never be promoted to final.

To proceed anyway, re-run with an explicit risk override that names those D-IDs;
capture will read back the risk and still leave the briefing draft/stale in provenance.
```

**Explicit risk override:** the user must name the unresolved or invalidated D-IDs. The agent reads back the exact risk (print-then-ask) before any write. The override never rewrites the briefing status to final and never erases the draft/stale flag from evidence recorded in the spec.

**Decline** (user aborts): record nothing in `produced_specs[]`; the chart remains resumable.

When no chart briefing is in play, this step is a silent no-op.

---

## 1.2b — Chart briefing evidence

When 0.5b admitted a chart briefing (final, or draft/stale under explicit risk override), extract into the evidence surface (and later into `## Decision Context` / evidence sections of the draft):

- Chart id, B-ID, cluster key (if multi-spec / cluster file), briefing path(s).
- Each cluster D-ID with title, gist, and record link from the briefing.
- Shared-context D-IDs (attributable evidence; not automatic acceptance requirements).
- Approved asset references (kind/reference/display) listed on those decisions.
- If override: the named unresolved/invalidated D-IDs and the risk read-back text.

These are **structural evidence references**. Do **not** attach acceptance-criterion source tags (`[user]` / `[paraphrase]` / `[inferred]` / `[strategy:<track>]`) to D-ID lines, chart facts, assets, or briefing membership. Preserve them as navigable links.

Also check for an already-linked identity (retry recovery):

```bash
# From chart sidecar produced_specs[]: match briefing + cluster (+ optional spec).
# If a linked entry already exists for this B-ID+cluster, record SPEC_ID_EXISTING
# and skip minting a duplicate in Phase 5 — link-spec the existing spec instead.
```

---

## 2.2 — Chart provenance separation

**Chart provenance separation (fn-135 / R49):** chart decision provenance is structural (D-ID, answer gist, assets, briefing membership). Preserve those as evidence links in `## Decision Context` (and conversation-evidence footnotes). Never source-tag D-ID evidence. Never retag an existing criterion authored by an earlier pass. A criterion derived from an unattended resolved D-ID is **not** automatically `[user]` — apply the four-tag grammar only to acceptance criteria this capture pass newly authors, judged against conversation + briefing context. Shared-context D-IDs do not become duplicated acceptance requirements across output specs unless each target's read-back independently confirms that guarantee. **No verified/inferred fact or decision grammar** (fn-148 closed STOPPED with no verdict — licenses nothing here).

---

## 5.2 — Chart handoff

Runs inside the Phase 5 new-spec ceremony, immediately after `spec create` + `spec set-plan` succeeded:

```bash
# Chart handoff (fn-135) — ONLY after successful create + set-plan.
# Order is load-bearing: never link-spec before the spec body exists.
# On retry: if produced_specs already has this B-ID+cluster identity, discover
# that entry and link the existing spec instead of minting another (Phase 1.2b).
if [[ -n "$CHART_ID" && -n "$BRIEFING_ID" ]]; then
  # Subcommand tokens stay LITERAL on the command line (the Ralph guard blocks
  # a variable in either of the two tokens after the launcher); only arguments
  # come from the array.
  LINK_ARGS=("$CHART_ID" --briefing "$BRIEFING_ID" --spec "$SPEC_ID" --decisions "$CHART_DECISIONS" --json)
  [[ -n "$CLUSTER_KEY" ]] && LINK_ARGS+=(--cluster "$CLUSTER_KEY")
  "$FLOWCTL" chart link-spec "${LINK_ARGS[@]}"
fi
```

**Chart handoff retry rules (fn-135 R50):**

- Capture decline / abort: call nothing; no `produced_specs[]` entry; chart stays resumable.
- Partial multi-spec: record only successful `link-spec` calls; resume the failed cluster without duplicating the first.
- Interruption after `spec create` / `spec set-plan` but before `link-spec`: on retry, discover the existing B-ID+cluster identity (chart sidecar `produced_specs[]` or matching specs) and link that same spec — never mint a second.

---

## Provenance lanes — do not collapse

Three provenance lanes must not collapse:

1. **Chart decision provenance** — D-ID, type, answer/gist, assets, supersession, briefing membership. Briefings preserve links; capture copies them into evidence sections as references.
2. **Acceptance-criterion author tags** — `[user]` | `[paraphrase]` | `[inferred]` | `[strategy:<track>]` only on criteria **this capture pass newly authors**. Never retag existing criteria. Never tag D-ID evidence or chart facts. A criterion derived from an unattended resolved D-ID is **not** automatically `[user]`.
3. **Verified-versus-inferred technical facts** — fn-148 closed 2026-07-30 as STOPPED with **no verdict**. Capture adds **no** `[verified]` / verified-vs-inferred decision grammar. Do not invent one.

Draft/stale briefings fail closed for ordinary capture; explicit risk override must name unresolved/invalidated D-IDs and read back the risk without promoting a forced draft to final. `link-spec` runs only after `spec create` + `spec set-plan`; retry discovers B-ID+cluster identity first.

---

## Forbidden behaviors (chart rows)

| Forbidden | Why |
|-----------|-----|
| Treating a forced draft briefing as final, or silent draft/stale admission | Fail closed; override requires named D-IDs + risk read-back; never promotes draft to final. |
| Source-tagging D-ID / chart evidence as `[user]` | Chart provenance is structural links; four-tag grammar is for newly authored criteria only. |
| `chart link-spec` before `spec create` / `spec set-plan`, or minting a duplicate after interruption | Order: create → set-plan → link-spec; retry discovers B-ID+cluster identity first. |
| Chart facts get no verified/inferred grammar | fn-148 stopped - no verdict. |
