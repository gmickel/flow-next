# Briefing handoff, abandon, and reopen

Read this file only when the chart is **briefable** (Phase 2 frontier reports no open decisions and no parked questions), when the user asks "one spec or two" / "ready to capture", or when an explicit abandon / reopen is requested. Ordinary chart-mode and mid-route work invocations never need it.

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

---

## Phase 4: Briefing handoff

Briefing rationale prose follows the artifact prose contract in [docs/prose.md](../../../docs/prose.md); proceed without it when the doc is absent.

When `frontier` / completion reports **briefable** (no open decisions including blocked/claimed; no parked Open Questions), or the user asks "one spec or two" / "ready to capture":

1. Cluster resolved decisions; **default N=1**. Propose split only when clusters are genuinely disjoint.
2. For each cluster: one-line rationale; name multi-cluster D-IDs as **shared context** (not duplicated requirements).
3. Read back the proposal for confirmation (merge / split further / override / abort).
4. Write proposal file:

```json
{
  "clusters": [
    {
      "key": "1",
      "rationale": "Single product surface; all decisions share one Outcome",
      "decisions": ["fn-140.D1", "fn-140.D2"]
    }
  ],
  "shared_context": []
}
```

5. Call:

```bash
"$FLOWCTL" chart briefing "$CHART_ID" --proposal-file proposal.json [--force] --json
```

- Ordinary briefing refuses while open/parked remain unless `--force` (draft-only, chart stays open, never capture-ready).
- A non-draft briefing sets chart `done`.
- The same proposal over an untouched ledger is idempotent (same B-ID back, `noop`) - within one epoch. A `chart reopen` starts a new epoch: the identical proposal then mints the next B-ID, recomputes draft-vs-final from the live chart, and returns `supersedes_stale` naming the B-IDs it supersedes.

6. Hand off to capture by running `/flow-next:capture .flow/charts/<chart-id>-briefing.md` (paste-ready; name the B-ID alongside it when several exist). Capture owns source tags on criteria it newly authors; chart evidence stays as D-ID links.

**Host command form:** print every copy-pasteable flow-next command here in the spelling this host invokes - the flat `/flow-next-<name>` form when the resolved plugin root carries `.flow-next-opencode-manifest` (an OpenCode install - the same signal setup's host detection uses); on any other or indeterminate host, exactly as spelled here.

Terminal on successful final briefing:

```text
CHART_VERDICT=COMPLETE chart=<id> decision=- reason="briefing B1 emitted; hand off to capture"
```

---

## Phase 6: Abandon / reopen (explicit only)

- `chart abandon --reason` - terminal stop mid-discovery; decisions preserved.
- `chart reopen --reason` - audited; stales prior briefings and spec links before new work.

A reopen does not close the capture door. Once the chart is briefable again, `chart briefing` with the **same** proposal mints the next package instead of echoing the staled one, and says so:

```text
fn-1 briefing B2 status=final (supersedes stale B1)
```

- Draft-vs-final is recomputed per invocation, never inherited: a chart that is not briefable again still gets a `--force` draft only.
- Staled `produced_specs[]` links stay stale. Whether specs built from the earlier briefing still hold is a human call, not a re-brief side effect.
- The staled B-ID stays on disk and in the ledger - a re-brief supersedes history, it never rewrites it.

Always read back reason and consequence first.

