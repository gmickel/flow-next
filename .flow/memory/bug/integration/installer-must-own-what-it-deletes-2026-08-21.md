---
track: bug
category: integration
module: scripts/install-codex.sh, scripts/sync-codex.sh
tags: [installer, ownership, namespace, data-loss, codex, mirror]
status: active
---

# Installer must own what it deletes; validate at the consumer's layout

PR #363's docs-install stage (round-3 fix) recursively deleted `$CODEX_HOME/docs/reach`
and copied loose generic names (`README.md`) into the shared `$CODEX_HOME/docs/` —
destroying non-flow-next user data on every install. codex reproduced it with a
sentinel file (P1). Root cause chain: three consecutive review rounds came from
validating artifacts against the REPO tree while the real consumer is the INSTALLED
layout — shallower, partially populated, different invocation syntax.

## Prevention

- **Ownership invariant:** an installer creates/overwrites/deletes ONLY inside a
  directory it owns outright (`$CODEX_HOME/docs/flow-next/`); shared parents are
  never `rm -rf`'d and never receive loose generic filenames. Sentinel regression
  test shape: pre-create non-owned files in a temp home, run the real installer,
  assert byte-identical survival (`test_install_never_touches_non_owned_docs`).
- **Consumer-layout validation:** sync-codex.sh guards now enforce mirror docs-link
  resolution, installed link-universe closure (resolve on disk or absolute URL),
  and actionable-invocation rewrite (`/flow-next:` → `$flow-next-`). Guard failures
  are load-bearing — extend the transform or fix the content, never relax the guard.
- The mirror tree is copied verbatim into the same relative layout under
  `$CODEX_HOME`, so the repo-tree guard IS the install check — keep that property
  when adding install surfaces.
