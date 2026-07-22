---
satisfies: [R1]
---
# fn-126-grok-build-host-fidelity-positive.1 Investigate a reliable Grok session signal (live)

## Description
INVESTIGATION GATE (NEEDS-HUMAN, live Grok) - no detector ships before this evidence exists. In two fresh real Grok Build sessions, probe the ordinary skill-shell environment BEFORE setup runs; record sanitized findings + the branch decision in a new `## Investigation outcome` section of the spec. Capture: env var NAMES (never values), resolved plugin root/manifest, grok version/mode, command path, parent-process comm names, `grok inspect --json` if it exists, candidate ~/.grok/ markers. Repeat from a plain shell AND from Codex on the same machine (incl. Codex launched from a Grok-owned shell if possible) as negative controls. A candidate signal is accepted ONLY if it identifies the ACTIVE host (not merely a Grok install) and does NOT leak into the Codex control. Reject GROK_PLUGIN_ROOT/GROK_HOME/.grok//grok-on-PATH/process-ancestry unless live evidence + an official xAI contract make it reliable. Likely outcome (per xAI docs): manual-selection branch.

## Acceptance
- Evidence: grok version/mode, two Grok sessions, same-machine negative controls (plain shell + Codex, incl. Codex-from-Grok-shell if possible).
- Candidate accepted only if it identifies the active host and is absent in the Codex control.
- Fragile signals (PATH/home/config/hook-only/process-name) rejected without a stable official contract.
- Outcome selects ONE branch: `positive signal` (exact predicate + false-positive guard) OR `no reliable signal` (manual-selection fallback).
- NEEDS-HUMAN: probes run inside real Grok Build; secret redaction + reproducibility reviewed.


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
