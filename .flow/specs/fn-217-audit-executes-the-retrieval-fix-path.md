## Goal & Context

Teams running `/flow-next:audit` get a third answer for a lesson that keeps being re-learned: fix how it is found. Today the audit's recurrence pre-scan sends every re-learned entry toward Harden, and an entry that recurs but states a rule no machine can check falls through to Keep. The intake filters already say "a rule that existed but did not fire gets a retrieval fix, not a rewrite" and the conduct checklist repeats it, but no phase executes it, so an audit run can never report one. This change wires the existing rule into the classify step and the Update outcome: recurrence without mechanizability is a retrieval defect, repaired by tuning the entry's retrieval surface (title, tags, module, `applies_when`) and never its body. Read-side telemetry does not exist in flow-next; the signal is the same write-side inference the Harden recurrence scan already uses.

## Acceptance Criteria

- **R1:** The Update outcome in `plugins/flow-next/skills/flow-next-audit/phases.md` gains a named retrieval-fix variant: when to use it (entry correct, recurrence-qualified per §0.75.1, not mechanizable), what it may touch (title, `tags`, `module`, `applies_when`, and the one-line summary the search index scores), and the boundary that a body or solution edit under this variant is a Replace in disguise.
- **R2:** Phase 2 classify in `workflow.md` routes an entry that is recurrence-qualified and fails the Harden mechanizability condition to Update (retrieval fix), before the Keep fallback, and records the reason in the entry's evidence bullets by citing the write-side artifacts, never a usage count.
- **R3:** The Phase 5 report distinguishes retrieval fixes inside the Updated count (a `retrieval fix` marker on the per-entry line and a `(of which retrieval fixes: N)` on the counts block) so a reader can tell a reference fix from a findability fix.
- **R4:** `docs/memory-schema.md`'s audit lifecycle section names the retrieval-fix path in one sentence, `CHANGELOG.md` gains an `## Unreleased` entry written user-outcome-first, and the codex mirror is regenerated with `scripts/sync-codex.sh` run twice.

## Boundaries

- No new memory status, frontmatter field, or flowctl subcommand. `audit_notes` via existing helpers carries any reason text.
- No read-side telemetry, no usage counter, no "skill-was-used" instrumentation. Recurrence inference stays exactly as §0.75.1 defines it.
- No new test. The conduct checklist in `agent_docs/conduct/audit.md` already carries this rule; G2 forbids pinning the prose. Added prose is judged under G1 in review.
- Skill prose outside the audit skill is out of scope.

## Quick commands

- `cd plugins/flow-next/tests && python3 -m unittest test_memory_marks test_skill_prose_flowctl_surface test_precheck_mode_contract -q`
- `./scripts/sync-codex.sh && ./scripts/sync-codex.sh && git status --short plugins/flow-next/codex`

## Decision Context

Recurrence without mechanizability is routed to a retrieval fix rather than a new status because the store has no read-side signal to make a status truthful; a findability repair is an Update by the existing definition (references drifted, here the references are the retrieval surface). A separate outcome name was rejected as vocabulary growth for a case the Update definition already covers.
