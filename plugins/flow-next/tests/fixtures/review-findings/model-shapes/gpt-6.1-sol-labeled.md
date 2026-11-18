I’ll read the task spec first, then review the diff and run the focused checks it names.
The guidance changes match the reported workflow gaps. I’m checking credential failures and the PR JSON projections for cases the new tests may miss.
The focused suites cannot run normally because the read-only sandbox blocks their temporary directories. A file-free reproduction confirms a cache race: four simultaneous credential requests run the helper four times. I’m checking whether a normal caller reaches it.
R1 remains incomplete in two reproducible cases.

## Findings

### 1. Concurrent requests run the token command multiple times

- **Severity**: P2
- **Confidence**: 75
- **Classification**: introduced
- **File:Line**: `plugins/flow-next/scripts/flowctl_tracker/credentials.py:106`
- **R-IDs**: [R1]
- **Problem**: The cache check and population are unsynchronized. Concurrent first requests can all enter `subprocess.run` before any result is cached. A reproduction through `bound_executor` with four simultaneous authenticated requests invoked the helper four times, violating R1’s once-per-process requirement.
- **Suggestion**: Synchronize cache lookup, command execution and result publication so concurrent callers reuse one result, including failures.

### 2. Decoding discarded stderr can reject a valid credential

- **Severity**: P2
- **Confidence**: 75
- **Classification**: introduced
- **File:Line**: `plugins/flow-next/scripts/flowctl_tracker/credentials.py:108`
- **R-IDs**: [R1]
- **Problem**: `text=True` decodes both stdout and stderr. A helper that exits successfully, prints a valid ASCII token to stdout and emits a non-UTF-8 diagnostic to stderr returns an authentication failure instead of using the token. Reproduced with stderr bytes `b'caf\xe9'`. The decoding exception also bypasses cache population, so subsequent requests rerun the helper.
- **Suggestion**: Capture bytes, discard stderr without decoding it, and decode stdout explicitly. Cache any stdout-decoding failure as a safe `TokenCommandError`.

## Requirements coverage

| R-ID | Status | Evidence |
|---|---|---|
| R1 | partial | Credential fallback and precedence implemented; concurrent caching and stderr handling fail above. |
| R2 | met | Shared land workflow defines the destructive-fix `BLOCKED` stop. |
| R3 | met | Forge-specific head-bound links; three focused link tests pass. |
| R4 | met | Both forge references identify `.selected.pr.open.readiness.head_sha`. |
| R5 | met | Both adapters project requested keys, supply draft/body values and reject unsupported keys. |
| R6 | met | Aid guidance makes the head diff authoritative over task summaries. |
| R7 | met | Delivery guidance permits repository-required trailers before `Ref`. |

Unaddressed R-IDs: [R1]

## Global criteria

G1: met - Added guidance addresses the documented failures with justification in the spec.
G2: met - Changed tests assert behavior and contracts.
G4: met - Added mechanisms support explicit requirements; no unjustified agent gate was added.

## Verification

Schema drift suite: 30 tests passed. Focused forge-link checks: 3 tests passed. Credential and forge helper suites were blocked by the sandbox’s inability to create temporary directories. Both findings were reproduced without filesystem writes.

Classification counts: 2 introduced, 0 pre_existing.

```json
{"classification_counts":{"introduced":2,"pre_existing":0},"unaddressed":["R1"]}
```

<verdict>NEEDS_WORK</verdict> - R1’s explicit requirements remain incomplete.