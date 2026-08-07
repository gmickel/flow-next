# Weekend execution handover - 2026-08-07 (Fri)

Session handover for the weekend push. Delete this file once the queue is done.
Cold session: run `.flow/bin/flowctl brief` first, then work THIS order.
Hard deadline: **fn-167 (Bugbot) must be LANDED + RELEASED before Monday** -
maintainer is at a Cursor shop Monday.

## Order (work through the weekend, no idle gaps - parallelize the two tracks)

### Track A - Bugbot (deadline-critical)
1. **BLOCKED ON GORDON**: fn-167.1 manual smoke. Runbook:
   `scratch/bugbot-smoke/RUNBOOK.md` on branch `fn-167-smoke/bugbot-target`
   (7 steps; fixtures prebuilt by fn-167.4, patch-ids verified identical
   `6c49a82a`). Nothing to set up beyond following it.
2. The moment smoke notes arrive: build fn-167.2 (prepush-review pilot stage)
   + .3 (docs + downstream) -> make-pr -> land SAME DAY. The three smoke
   answers (dedup fires? findings on PR? draft behavior?) decide design
   details in .2 - read task files first.
3. Release it (per-spec release justified by the deadline; follow
   agent_docs/releasing.md incl. flow-next.dev changelog + notable updates).

### Track B - runs in parallel with A
4. **fn-170** (chart notes_append, closes issue #292): `flowctl spec ready
   fn-170-chart-notes-correction-path-notes` then normal pilot -> land.
   Plan-review runs as pilot's first tick (never reviewed - intended).
   After landing: reply on #292 (promised the reporter).
5. **fn-171** (setup-block ids + check, closes #294): same flow, after or
   overlapping fn-170 (disjoint flowctl regions). Reply on #294 after.
6. **Stacked-PR trio, strict order fn-149 -> fn-152 -> fn-150** (dependency
   edges enforce it): each needs `/flow-next:plan <id>` FIRST (all three are
   ready=true but have ZERO tasks). Pre-pilot assessment already done
   2026-08-07, edits applied to specs; key facts: all-prose+gh (no flowctl
   except fn-152's `stacks.enabled` config key which NEEDS the
   gen_flow_config_schema.py TABLE entry - it's in the spec Boundaries),
   default-off gating verified, fn-149 merge-async loop goes in workflow
   bash NOT a flowctl poller.
7. **fn-160** (setup speed) after fn-171 lands (edge encoded). Biggest item;
   start Sunday if the queue above is done, else it opens next week.

### Autonomy recipe (preferred once fn-167 lands)
Bless the queue (`spec ready` per item as its turn comes - the dep edges
gate order) and drive with `/loop /flow-next:pilot` + `/flow-next:land`
cadence; intervene only on NEEDS_HUMAN. Releases: batch per land-run
judgment unless user says otherwise.

## Parked - do NOT pick up this weekend
- fn-158 (chart alias namespace): deferred until field report or region is
  warm; depends on fn-170 (edge encoded). Breaking-change design spec.
- fn-173 + fn-162 (cua browser-use ladder + cursor rung smoke): plan when
  maintainer says; fn-162 depends on fn-173 (edge encoded).
- fn-172 (eval suite): maintainer builds ad-hoc; stub only.
- fn-98: watch-stub; R2/R4-R9 doc-correction work is real but unscheduled.
  CAUTION: its Acceptance section records MEASURED probe results (steering
  WORKS; sandbox_mode read-only is prompt-only) - Goal prose is stale;
  Acceptance supersedes Goal. Do not "re-check" from the Goal text.
- fn-132/133/142/143/129/157/61/73/144: no weekend relevance.

## Standing context a fresh session needs
- 3.16.1/2/3 all released today (plan-sync fix; capture spec-count proposal;
  split-path hardening). CI restructured: ~7-8m wall, parallel units/smokes.
- Test policy changed TODAY: all prompt-size ratchets + prose pins removed;
  .flow/criteria.md G1 (prose growth justified) + G2 (tests = behavior/tokens,
  never prose sentences) now judged by completion review; CLAUDE.md carries a
  never-reintroduce tombstone. test_prompt_text_pinned.py is the ONLY
  deliberate-change guard left.
- flowctl edits: dual copy + gen_tracker_manifest.py + sync-codex twice
  (checklist in CLAUDE.md). Skill prose edits: sync-codex twice.
- Tracker: Linear links exist for new specs (FLOW-96/97); status projection
  errors on unmapped states (no tracker.statuses map) - best-effort, ignore.
- Docs-only changes: no version bump. Feature releases: full downstream walk
  (repo -> flow-next.dev -> guide -> vault) per downstream-properties.md.
- Issues open: #292 (fn-170), #294 (fn-171), #89 (linked to fn-61, replied).
