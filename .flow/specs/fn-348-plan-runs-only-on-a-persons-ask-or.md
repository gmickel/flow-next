## Goal & Context

Since 9.8.0 a spec is planned into tasks only when a person asks for a plan or a task breakdown, or
when `flow-next-flow` routes there. Agents still land in plan when one agent briefs another to
"create a spec from this and deliver it". A study on 9.18.0
(`~/work/agent-evals/studies/plan-leak-indirect-2026-11/REPORT.md`, 228 draws) found the cause:
the setup snippet in every project's CLAUDE.md / AGENTS.md says "create the spec, then
`flow-next-plan`", and flow reads that line as a request for a plan. Every leaking session quoted
it. With no instruction file the same prompt never planned; with the old snippet it planned in 6
of 7 draws that reached a route.

Two changes removed the leak without blocking any explicit ask (guards 9 of 9 each): correcting the
snippet line, and narrowing the plan skill's description. The description ships with the plugin, so
it is the change that reaches projects that never re-run setup (0 of 4 with the old snippet still
in place; small sample). Guidance at the top of the plan skill did not work and is not shipped.

## Edge Cases & Constraints

- A project whose block was hand-edited keeps the old line after an update; only the changelog
  and the narrowed description reach it.
- A host with a description length cap: shorten without dropping "only when a person explicitly
  asks" and "never for a request to build".
- Legacy specs that carry tasks are unaffected.

## Acceptance Criteria

- **R1:** Snippet. In `skills/flow-next-setup/templates/claude-md-snippet.md` and
  `agents-md-snippet.md`, the "Creating a spec" line no longer says to run plan afterwards, and a
  line says that building, implementing or delivering a spec, whether a person or another agent
  asks, goes through `flow-next-flow`, and that plan runs only on a person's ask for a plan or task
  breakdown or on flow's route. Use the study's measured wording (`arms/B.diff`) with each host's
  own invocation spelling. The Cursor rule `rules/flow-next.mdc` carries the same correction. The
  installed snippet for Claude Code, Codex and Cursor contains no instruction to run plan after
  creating a spec, and names `flow-next-flow` as the way to build a spec.
- **R2:** Plan description. The plan skill's description is the study's shorter measured wording
  (`arms/C2.diff`): task breakdown, only on a person's explicit ask (direct or relayed in a brief),
  through the plan command, or on flow's route; never for a request to build, implement, deliver
  or run a spec, whoever sends it. Any host limit on description length is respected. On
  Claude-format hosts it equals the C2 wording.
- **R3:** Codex. The Codex plan skill's `agents/openai.yaml` `short_description` and
  `default_prompt` no longer advertise plan for any feature request ("Plan out this feature" and
  the build-plan advertisement are gone); they agree with R2. Whether implicit invocation stays on
  is unchanged.
- **R4:** Smaller pointers. `flowctl next` no longer answers `plan <id> needs_tasks` for a ready
  zero-task spec in a way that contradicts the direct-by-default rule, with a test;
  `scripts/map.sh`'s "Next steps" no longer names plan as the next step; the docs lines the study
  lists (`docs/teams.md`, `docs/orchestration.md`, `docs/pipeline-variations.md`,
  `docs/running-lean.md`, `docs/flowctl.md`) describe plan as something a person asks for, not
  something decided from a spec's size. Work's zero-task stop message and question keep their
  behaviour; the unattended message names the direct route and `flow-next-flow` first and plan as
  what a person may ask for.
- **R5:** Existing projects. No detection code and no new flag. `docs/troubleshooting.md`'s answer
  to "do I re-run setup after an update?" says to re-run when the changelog says the snippet
  changed, and to choose Overwrite if the block was edited.
- **R6:** Changelog. The entry is prominent: it opens the release's section, says in plain words
  that agents briefed by other agents could be sent to plan by a line in the installed snippet,
  that updating the plugin fixes it for most cases, and what existing projects should do (re-run
  setup and overwrite the block; remove any line of their own that says to plan before building).
  It credits nobody externally and names no private consumer.
- **R7:** Mirrors and gates. Codex mirror regenerated after the last edit, help text and its hash
  regenerated if `flowctl next` output or help changes, the conduct checklists for setup, plan,
  flow and work updated where their contract text changed, and tests that pin the snippet or
  description text updated to the new text. The repository's test suite, mirror checks and
  help-hash check pass.

## Boundaries

- Plan stays invocable by the model; no `disable-model-invocation`, no hard switch. An explicit
  `/flow-next:plan <spec>` and a relayed "produce a task breakdown" still reach plan (covered by
  the study's guards and by existing tests).
- No guidance block added to the plan skill's body (measured: it does not work).
- No snippet-version detection, no new config key, no new flowctl verb.
- Flow's routing rule (`plan-vs-no-plan.md`) is not changed; a project's own doc that asks for a
  plan remains a person's standing ask.
- Capture's and refine's "Recommended next" lines are not touched (they already follow the rule).
- The readiness mark and work's `mode:autonomous` stop on zero-task specs are out of scope.

## Decision Context

Gordon's direction: plan reachable only by a person or by flow, done through wording and not by
making the skill non-invocable, and it must help projects that never re-run setup. The study's
arms: B (snippet) 0/24, C1 and C2 (description, old snippet kept) 0/24 each, E (plan-top guidance)
2/24, D (zero-task wording) not on the leak path. The pre-registered endpoint was formally
inconclusive because the leak sits in one prompt shape; the mechanism evidence is the sessions'
own quoted reasons.
