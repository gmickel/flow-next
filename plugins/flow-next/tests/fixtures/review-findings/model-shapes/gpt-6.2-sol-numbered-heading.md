I’ll read the task contract first, then trace the changed code and run the focused checks.
The schema checks and three focused link tests passed. The broader suites stop at fixture setup because the sandbox has no writable temporary directory. I’ll verify the remaining edge cases with checks that can run in memory.
One blocking finding. A repository-controlled tracker configuration can execute a local command during an authenticated read.

## Findings

### 1. Repository config gains execution authority

- **Severity** P1
- **Confidence** 100
- **Classification** introduced
- **File:Line** `plugins/flow-next/scripts/flowctl_tracker/resolve_verb.py:86`
- **R-IDs** `[R1]`
- **Problem** An authenticated Linear or Jira read in a checkout with no provider token in the environment executes `tokenCommand` from the checkout’s `.flow/config.json` with the caller’s local permissions. Land’s post-merge tracker replay also passes the head-read bridge config to this executor. Authorization to read tracker state or replay a transition gives the repository control over which local program runs.
- **Suggestion** Source executable argv from trusted local configuration or verify the exact argv against a locally approved value before execution. Keep head-read tracker routing data usable independently.

### 2. Non-text helper output reaches the error message

- **Severity** P2
- **Confidence** 100
- **Classification** introduced
- **File:Line** `plugins/flow-next/scripts/flowctl_tracker/credentials.py:108`
- **R-IDs** `[R1]`
- **Problem** A helper that writes a non-UTF-8 byte to stderr and exits 3 produces an error containing the byte’s hex value. `text=True` decodes both streams before checking the exit status. The executor then stringifies the decoding exception, exposing a fragment of the output and losing the exit cause.
- **Suggestion** Discard stderr, capture stdout as bytes, check the return code first, and map stdout decoding failures to a fixed message.

### 3. Concurrent first requests can run the helper twice

- **Severity** P2
- **Confidence** 100
- **Classification** introduced
- **File:Line** `plugins/flow-next/scripts/flowctl_tracker/credentials.py:106`
- **R-IDs** `[R1]`
- **Problem** Two authenticated requests can both miss `_COMMAND_RESULTS` while the first subprocess is running. A two-thread check confirmed two executions for the same argv.
- **Suggestion** Serialize the cache lookup and first execution for a given argv. Share the cached result with waiting requests.

### 4. An empty environment variable runs the helper

- **Severity** P2
- **Confidence** 100
- **Classification** introduced
- **File:Line** `plugins/flow-next/scripts/flowctl_tracker/credentials.py:143`
- **R-IDs** `[R1]`
- **Problem** `LINEAR_API_KEY=""` runs the helper because the fallback tests truthiness. R1 and the published schema say the helper runs only when the variable is unset.
- **Suggestion** Fall back only when `os.environ.get(name)` returns `None`. Preserve the existing missing-credential behavior for an empty value.

### 5. Tracker discovery still describes environment-only credentials

- **Severity** P2
- **Confidence** 100
- **Classification** introduced
- **File:Line** `plugins/flow-next/docs/tracker-sync.md:57`
- **R-IDs** `[R1]`
- **Problem** A Jira Cloud user with `JIRA_BASE_URL`, `JIRA_EMAIL`, and a configured helper gets conflicting setup instructions. The new paragraph describes helper-backed auth, while the discovery table still requires `JIRA_API_TOKEN` to offer Jira and the Jira section still says credentials come from the environment each run. The Codex copy has the same conflict.
- **Suggestion** Update both copies to describe when a helper-backed provider is offered and how `tracker resolve` verifies it.

### 6. A GitLab remote with no namespace gets a file link

- **Severity** P2
- **Confidence** 100
- **Classification** introduced
- **File:Line** `plugins/flow-next/scripts/flowctl.py:30046`
- **R-IDs** `[R3]`
- **Problem** `https://gitlab.com/repo.git` produces `/repo/-/blob/<sha>/`. The GitLab branch accepts a one-segment path, so a remote with no namespace creates a broken link where R3 requires a plain path.
- **Suggestion** Require at least two segments for GitLab and cover the one-segment remote in the fallback test.

### 7. Both stand-ins can silently omit a requested key

- **Severity** P2
- **Confidence** 100
- **Classification** introduced
- **File:Line** `plugins/flow-next/scripts/make-pr-bitbucket.sh:95`, `plugins/flow-next/scripts/make-pr-gitlab.sh:108`
- **R-IDs** `[R5]`
- **Problem** With `--json 'number, body'`, shell word splitting validates `body` while jq looks for ` body`. Both helpers exit 0 and return only `number`. An explicitly empty `--json ''` returns every field.
- **Suggestion** Parse and validate one comma-separated key list, then pass that same list to the projector. Reject empty or invalid entries explicitly.

### 8. GitLab’s readiness field list still uses the bare name

- **Severity** P2
- **Confidence** 100
- **Classification** introduced
- **File:Line** `plugins/flow-next/skills/flow-next-land/forge-gitlab.md:24`
- **R-IDs** `[R4]`
- **Problem** The revised GitLab paragraph qualifies the head SHA but still introduces the remaining fields with `` `readiness` holds ``. R4 requires the full path wherever the reference describes reading readiness. The Codex copy repeats the omission.
- **Suggestion** Use `.selected.pr.open.readiness` when introducing the GitLab field list, as the Bitbucket reference does.

**FYI (Duplicated Code)** Both forge helpers add the same projection hunk, `def pick: if $keys == "" then . else with_entries(select(.key | IN($keys | split(",")[]))) end;`. This duplication shares the malformed-key failure in finding 7.

## Requirements coverage

| R-ID | Status | Evidence |
|---|---|---|
| R1 | partial | Helper-backed auth works through `bound_executor`. Command trust, redaction, precedence, and one-run behavior have gaps. |
| R2 | met | The shared workflow specifies `BLOCKED` with the check and reason. Bitbucket retains `NEEDS_HUMAN` for an unknown cause. |
| R3 | partial | The tested forge paths bind links to the head SHA. A GitLab path without a namespace still gets a link. |
| R4 | partial | Both references qualify the head SHA. GitLab still uses the bare name for the field list. |
| R5 | partial | Recorded listings return `isDraft` and `body` without a detail call. Malformed key lists can succeed with the wrong fields. |
| R6 | met | The aid follows the head diff when it conflicts with a task summary. |
| R7 | met | The workflow allows only repository-required trailers before `Ref`. |

Unaddressed R-IDs: []

## Global criteria

G1: met - The spec ties each added instruction to a field-report failure and explains why guidance suffices.  
G2: met - The changed tests assert executable behavior, structured output, and schema contracts.  
G4: met - The helper is optional, and the new `BLOCKED` rule addresses the documented risk of weakening the PR to pass CI.

**Verification** 47 focused tests passed, along with shell syntax and diff checks. Read-only fixture replays exercised both forge helpers. The broader suites hit fixture setup errors because the sandbox had no writable temporary directory.

Classification counts: 8 introduced, 0 pre_existing.

```json
{"classification_counts":{"introduced":8,"pre_existing":0},"unaddressed":[]}
```

<verdict>NEEDS_WORK</verdict>