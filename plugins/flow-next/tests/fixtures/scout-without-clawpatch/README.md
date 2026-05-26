# scout-without-clawpatch fixture

Minimal fixture directory intentionally **without** a `.clawpatch/` subdirectory.

Used by `tests/test_scout_fallback_contract.py` to verify that
`flowctl repo-map list --json` returns `{success: true, count: 0,
features: [], clawpatch_present: false}` with exit 0 when invoked against a
working tree that has no clawpatch state.

This proves the *plumbing-side* fallback contract: scouts that call
`flowctl repo-map list --json` first get a clean zero-result envelope when
`.clawpatch/` is absent, so the agent prose's "skip Step 0 when absent"
branch is reachable without errors.

The *prose-side* contract (agent files document the fallback path and
schema) is verified by other assertions in the same test.

Do NOT add a `.clawpatch/` directory here — the absence is the contract.
