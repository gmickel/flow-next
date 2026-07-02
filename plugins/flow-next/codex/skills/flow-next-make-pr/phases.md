# /flow-next:make-pr — phase reference (stub)

The per-phase **Done-when checklists live inline in [workflow.md](workflow.md)** — each phase ends with its own `### Done when` block (plus failure modes where they matter), directly beside the prose it verifies. This file is retained only as a stable link target and at-a-glance phase map; it is not part of the skill's working set.

| Phase | Goal |
|-------|------|
| Phase 0 | Pre-flight — gh ready, spec resolved, base valid, branch ahead, tasks done, no open PR. |
| Phase 1 | Gather inputs — single `flowctl spec export-cognitive-aid` call, parse payload. |
| Phase 1.5 | HTML render lens (opt-in) — PR artifact from payload + diff, narrow commit, body link line. Off/unset/`--dry-run` ⇒ no-op beyond one config read. |
| Phase 2 | Render body — TL;DR, R-ID table, critical changes; decisions, memory, glossary/strategy, open items, where to look. |
| Phase 3 | Mermaid generation — gated triggers, hard caps, fallback prose. |
| Phase 4 | Push + create PR — `git push`, `gh pr create`, draft/ready, dry-run short-circuit, Ralph behavior. |
| Phase 5 | Output + footer — PR URL, breadcrumb, optional `--memory` write. |

Cross-phase rules (hallucination guardrails, Forbidden list) live in [SKILL.md](SKILL.md); the anti-patterns list lives in [workflow.md §Anti-patterns](workflow.md).
