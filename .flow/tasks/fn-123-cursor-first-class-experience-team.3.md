---
satisfies: [R5]
---
# fn-123-cursor-first-class-experience-team.3 host-native review backend (host)

## Description
Add the host-native review backend `host`. flowctl side (deterministic plumbing only): a non-executable registry/selection sentinel in `plugins/flow-next/scripts/flowctl.py` + byte-identical `.flow/bin/flowctl.py`; `review.backend=host`, env override, and per-task/spec overrides resolve normally; `host:<model>`/`host:<model>:<effort>` are REJECTED with an error pointing at the AGENTS.md model-routing section (pins live in caller routing instructions, not the backend string); no subprocess, no `flowctl host` command. Skill side (judgment): host branches in flow-next-plan-review, flow-next-impl-review, flow-next-spec-completion-review - dispatch a fresh READ-ONLY reviewer subagent pinned via the host's model slugs to a family that did not write the diff, reusing the existing review rubrics + prior-finding convergence context; on Claude Code this maps to the existing native reviewer-subagent arrangement. Update backend-passthrough wording in plan/work/pilot skills. Update sync-codex.sh guards + regenerate the mirror.

## Acceptance
- Backend resolution/precedence for `rp`, `codex`, `copilot`, `cursor`, `none` unchanged; `host` is additive and never treated as a subprocess backend.
- `host:<model>` forms rejected with a hint to the AGENTS.md routing section.
- Host reviews preserve verdict grammar, iteration caps, fix/re-review behavior, receipt shape (record actual reviewer model + `mode: "host"`); each re-review is a fresh subagent context (no fabricated resume ids); receipt shape stays compatible with existing convergence/cap/pilot/land consumers.
- Hosts unable to honor a cross-family pin fail closed: interactive => explicit choice; autonomous => NEEDS_HUMAN. Never silent same-family self-review.
- Focused suites green (`test_backend_spec`, new `test_host_review_backend`); `cmp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py` clean; sync-codex twice-idempotent.
- NEEDS-HUMAN CHECKPOINT: one live host-review smoke on Claude Code AND one on Cursor with reviewer-family evidence recorded (maintainer-run).


## Done summary
host backend: non-executable registry sentinel (models/efforts None, excluded from MODEL_ROLE_BACKENDS); host:<model>/effort rejected with AGENTS.md-routing hint; byte-identical .flow/bin/flowctl.py. Skill side: host branches in plan-review (inline) + impl-review/spec-completion-review (workflow-host.md): fresh cross-family read-only reviewer subagent, per-host pin table (Claude model param / Cursor in-prompt slug / other generic), fail-closed (interactive ask / autonomous NEEDS_HUMAN), receipts mode:host + actual model, fresh context per re-review. Backend enumerations updated in plan/work/pilot. 157 tests green; mirror twice-idempotent. Reviewed by session model: approved. Live host-review smoke on Claude+Cursor REMAINS OPEN (needs-human).
## Evidence
- Commits: 9ccbec27
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_backend_spec test_host_review_backend -q
- PRs: