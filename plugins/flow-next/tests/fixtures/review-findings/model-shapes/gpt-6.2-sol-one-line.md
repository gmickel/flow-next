I’ll read the task first, then review the commit range against its acceptance criteria.
The schema checks passed. The focused suites that create temporary files could not start in this read-only sandbox, so I’m tracing those paths and checking what I can without writes.
## Findings

- **Severity** P1 · **Confidence** 100 · **Classification** introduced · **File:Line** `plugins/flow-next/scripts/flowctl_tracker/resolve_verb.py:86` · **R-IDs** `[R1]`  
  **Problem** The executor trusts `tokenCommand` directly from the checked-out `.flow/config.json`. A routine Linear or Jira request with no token in the environment can execute a command supplied by a PR branch under the caller’s account, without the caller selecting that command. Passing argv directly limits shell interpretation and still launches the configured executable.  
  **Suggestion** Keep the config key and require a trusted local authorization for the exact command before running it. A changed command must require fresh authorization.

- **Severity** P1 · **Confidence** 100 · **Classification** introduced · **File:Line** `plugins/flow-next/scripts/flowctl_tracker/credentials.py:108` · **R-IDs** `[R1]`  
  **Problem** `text=True` decodes both streams before the code checks the exit status. If a helper exits nonzero and writes an undecodable byte to stderr, the executor reports the decoder exception, including the offending byte, instead of the helper’s exit code. The exception also bypasses the cache, so the next request reruns the helper.  
  **Suggestion** Discard stderr, check the exit status before decoding stdout, and cache decoding failures with a fixed diagnostic.

- **Severity** P1 · **Confidence** 100 · **Classification** introduced · **File:Line** `plugins/flow-next/scripts/flowctl_tracker/credentials.py:106` · **R-IDs** `[R1]`  
  **Problem** Two concurrent authenticated requests reaching an empty cache can both pass `if key not in _COMMAND_RESULTS` before either stores a result. Both then launch the helper, violating the once-per-process requirement.  
  **Suggestion** Synchronize the first lookup and execution so concurrent callers share the same success or failure.

- **Severity** P2 · **Confidence** 100 · **Classification** introduced · **File:Line** `plugins/flow-next/scripts/flowctl_tracker/credentials.py:143` · **R-IDs** `[R1]`  
  **Problem** With `JIRA_API_TOKEN` explicitly set to an empty string and `JIRA_EMAIL` set, `if not value` launches the helper. R1 limits execution to an unset variable.  
  **Suggestion** Distinguish an absent variable from a present empty value and preserve the existing missing-credential behavior for the latter.

- **Severity** P2 · **Confidence** 100 · **Classification** introduced · **File:Line** `plugins/flow-next/scripts/flowctl.py:30046` · **R-IDs** `[R3]`  
  **Problem** `https://gitlab.com/project.git` produces `/project/-/blob/<sha>/…` even though the remote has no namespace. The briefing renders a link where R3 requires a plain path.  
  **Suggestion** Require at least a namespace and a project for GitLab, while allowing nested namespaces.

- **Severity** P2 · **Confidence** 100 · **Classification** introduced · **File:Line** `plugins/flow-next/scripts/make-pr-gitlab.sh:108`, `plugins/flow-next/scripts/make-pr-bitbucket.sh:95` · **R-IDs** `[R5]`  
  **Problem** Both helpers validate with `for KEY in ${KEYS//,/ }; do` and project with `split(",")`. Those operations disagree. `--json 'number, state'` passes validation and silently omits `state`. An explicit `--json ''` returns every field.  
  **Suggestion** Parse and validate one key list and use that same list for projection. Reject empty and unsupported entries before fetching.

- **Severity** P2 · **Confidence** 100 · **Classification** introduced · **File:Line** `plugins/flow-next/scripts/make-pr-bitbucket.sh:126`, `plugins/flow-next/scripts/make-pr-gitlab.sh:133` · **R-IDs** `[R5]`  
  **Problem** When a listing row lacks the requested source field, the projection fabricates a value. An omitted Bitbucket `draft` becomes `isDraft: false`, and an omitted `description` on either forge becomes `body: ""`. Callers cannot distinguish a missing field from a PR that is ready or has an empty body.  
  **Suggestion** Validate the source fields for requested keys and fail naming any key the listing cannot answer. Preserve documented null-to-empty conversions.

- **Severity** P2 · **Confidence** 100 · **Classification** introduced · **File:Line** `plugins/flow-next/skills/flow-next-land/forge-gitlab.md:26` · **R-IDs** `[R4]`  
  **Problem** The GitLab readiness paragraph gives the full path for `head_sha`, then uses bare `readiness` when telling the reader where to find the remaining fields. The Codex mirror does the same. R4 requires the full path in both places.  
  **Suggestion** Use `.selected.pr.open.readiness` for the field inventory in both copies, as the Bitbucket reference does.

## Requirements coverage

| R-ID | Status | Evidence |
|---|---|---|
| R1 | partial | Configured helpers reach the authenticated HTTP executor. Command trust, concurrent execution, environment precedence, and output handling have gaps. |
| R2 | met | The shared land workflow calls for `BLOCKED`, no commit, and the check and reason. Bitbucket retains `NEEDS_HUMAN` when the cause cannot be found. |
| R3 | partial | All three forge path shapes are implemented. A namespace-free GitLab remote still produces a link. |
| R4 | partial | Bitbucket uses the full path. GitLab retains bare `readiness` in its field inventory. |
| R5 | partial | Both helpers project keys from the existing listing. Malformed selectors can silently omit keys, and missing listing fields can produce substituted values. |
| R6 | met | The aid guidance directs the briefing to follow the head diff when a task summary disagrees. |
| R7 | met | Both workflow copies allow only repository-required trailer lines before `Ref`. |

Unaddressed R-IDs: []

## Global criteria

G1: met - The spec ties the added guidance to reported failures and explains why guidance suffices for stale claims and trailers.  
G2: met - Changed tests check behavior, schema coverage, or output contracts.  
G4: met - The token command is optional. The workflow changes use existing steps and verdicts.

The 30 schema drift tests and `git diff --check` passed. Read-only checks confirmed the GitLab link and selector cases. The remaining focused suites could not complete because the sandbox provides no writable temporary directory.

Classification counts: 8 introduced, 0 pre_existing.

```json
{"classification_counts":{"introduced":8,"pre_existing":0},"unaddressed":[]}
```

<verdict>NEEDS_WORK</verdict>