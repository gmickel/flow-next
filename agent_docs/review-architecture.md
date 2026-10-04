# Review command architecture

Maintainer notes on how `flowctl`'s review commands are built. Moved from the shipped
`plugins/flow-next/docs/flowctl.md`, which keeps only the user-facing behaviour (see its
[Review commands](../plugins/flow-next/docs/flowctl.md#review-commands) section).

All twelve `flowctl {codex,copilot,cursor,claude} {impl,plan,completion}-review` commands are thin wrappers over one driver: `cmd_backend_review(backend, kind)`. Per-backend variance (sandbox flags, session markers, argv-budget fit or stdin delivery, receipt shape) lives as hooks on `BACKEND_REGISTRY` entries, wired lazily by `_wire_backend_review_hooks`. Adding a review backend is a registry entry (hooks + models/efforts), not a new clone of the pipeline. The first-round fan-out (`flowctl <backend> impl-review-fanout` and `impl-review-fanout-finalize`) is one runner registered under every CLI backend, with no per-backend gating.

Reviewer tallies prefer one fenced `json` block (`suppressed_count`, `classification_counts`, `unaddressed`, `deep_findings`); prose tally lines remain a logged fallback. The `<verdict>SHIP|NEEDS_WORK|MAJOR_RETHINK</verdict>` tag contract is unchanged. Plan/completion handlers self-write `*_review_status` from the verdict; the standalone `spec set-*-review-status` commands still work.
