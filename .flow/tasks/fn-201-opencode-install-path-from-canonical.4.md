---
satisfies: [R7, R8]
---
# fn-201-opencode-install-path-from-canonical.4 Docs, CHANGELOG, and experimental OpenCode platform sentence

## Description
Same-workstream docs only. No version bump. No first-class tier promotion and no setup detection — R8 defers promotion until the R2 manual live-OpenCode verification plus a full dogfood run (the Grok-promotion bar).

Record the R8 wording decision in the spec Decision Context, then edit the canonical platform sentence in plugins/flow-next/docs/platforms.md (its only home) so OpenCode is a named EXPERIMENTAL install path — not a community port, not first-class. Restate the updated sentence verbatim on EVERY surface that quotes it — SIX in-repo occurrences: platforms.md:3 (canonical), README.md x2 (~lines 78 and 462), CLAUDE.md:3, STRATEGY.md x2 (~lines 15 and 69) — PLUS the flow-next.dev restatement surface that platforms.md:5 names (updated in the docs-site repo, same pnpm build gate as the changelog entry). Also update the three ADJACENT claims that would contradict it: the CLAUDE.md host-roster row "| OpenCode | community port | out-of-repo |", the STRATEGY.md:~35 "OpenCode port" mention, and the STRATEGY.md:~37 community-port adoption METRIC — restate that metric in terms of the in-repo installer (the port repo it measured is superseded).

platforms.md: add an OpenCode section covering install (./scripts/install-opencode.sh), installed layout (skills/ as-is; support dirs scripts/, templates/, references/, docs/ at config root; ownership manifest; generated agents/commands), and limitations (no native ask primitive -> numbered-prompt fallback already in canonical prose; setup NOT SUPPORTED on OpenCode - the setup SKILL is not installed and no stub exists, manual alternative: flowctl init + flowctl config set; the slash form on OpenCode is flat /flow-next-<name>, mapping from the /flow-next:<name> form every other doc uses; a co-existing Codex install wins the flowctl cascade's first rung via ~/.codex - stated explicitly; Ralph unsupported; model tiers inherit the session model). Every claim that agents/commands/flowctl WORK on OpenCode is gated on the spec's R2 manual live verification (path injection, agent+command discovery, flowctl co-existence echo). Update the install-matrix OpenCode row to the in-repo installer. Add OpenCode to the Ralph hooks table as none. Mark gmickel/flow-next-opencode superseded in the community-ports table (pointer only; do not edit that repo). Root README Platforms table + Ecosystem table: installer instead of the port repo; old port marked superseded.

Also refresh reach/opencode.md + reach/README.md (drop stale community-port framing; note the R2 manual-verification gate on the flowctl-resolution claim), agent_docs/releasing.md re-sync list (add the OpenCode installer beside Cursor/Codex), and troubleshooting uninstall notes if they still point at the port. Stage the repo ## Unreleased CHANGELOG entry user-outcome-first. The docs-site changelog entry FOLLOWS THE FORMAT CONTRACT in agent_docs/releasing.md section "Docs-site changelog entry (flow-next.dev)" — including its register rules and the "pnpm build must pass" gate, committed separately in that repo. Optionally one Notable-updates line on plugins/flow-next/docs/README.md.

Touches: plugins/flow-next/docs/platforms.md, README.md, CLAUDE.md, STRATEGY.md, CHANGELOG.md, plugins/flow-next/docs/reach/opencode.md, plugins/flow-next/docs/reach/README.md, plugins/flow-next/docs/README.md, plugins/flow-next/docs/troubleshooting.md, agent_docs/releasing.md, .flow/specs/fn-201-opencode-install-path-from-canonical.md, flow-next.dev changelog
Files:
- plugins/flow-next/docs/platforms.md
- README.md
- CLAUDE.md
- STRATEGY.md
- CHANGELOG.md
- plugins/flow-next/docs/reach/opencode.md
- plugins/flow-next/docs/reach/README.md
- plugins/flow-next/docs/README.md
- plugins/flow-next/docs/troubleshooting.md
- agent_docs/releasing.md
- .flow/specs/fn-201-opencode-install-path-from-canonical.md (Decision Context only)
- ~/work/flow-next.dev/src/content/docs/releases/changelog.mdx

## Acceptance
R7: platforms.md has an OpenCode section with install command, full layout (incl. support dirs + manifest), and the limitations incl. the explicit setup-unsupported statement with the manual alternative; README install-matrix/status row points at scripts/install-opencode.sh not the port repo; community-ports / Ecosystem tables mark flow-next-opencode superseded; ## Unreleased CHANGELOG exists in the repo, and the docs-site entry follows the releasing.md format with its pnpm build gate green; no version manifests / FLOW_NEXT_VERSION / bump.sh. R8: spec Decision Context records the sentence decision; the updated sentence appears verbatim at all six in-repo occurrences (platforms.md, README x2, CLAUDE.md, STRATEGY.md x2) AND on the flow-next.dev restatement surface; the three adjacent claims (CLAUDE.md roster row, STRATEGY.md port mention, STRATEGY.md community-port metric) are updated consistently, the metric restated in installer terms; the sentence does not call OpenCode first-class or a community port; no setup detection rung and no first-class promotion in this change.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
