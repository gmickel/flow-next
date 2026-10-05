# Create-first receipt and retry contract (gated reference)

> Read from steps.md §2 before any remote create (create-first, or a Flow-first issue create).

## Receipt / retry contract

Before creating remotely, derive the first 16 hex characters of
`sha256(type NUL title NUL body)` with `sync create-first-key`, then query that
key with `sync create-first-get`. A hit resumes by linking the recorded issue;
it never creates another.

After a successful remote create, immediately persist the returned identity
with `sync create-first-put`. Keep that recovery record across any later
failure. **After minting the local spec, record the claim with
`sync create-first-put --spec-id <id> --if-absent`** - the CAS
form, so two promoters racing on the same candidate end with one recorded
spec. On exit `10` with `subtype=spec_already_minted`, another promoter won:
adopt `details.recordedSpecId` and retire the locally minted duplicate with
`flowctl spec close <loser-id> --retire superseded --by <winner-id>` - a
retired duplicate is inert and auditable, and there is deliberately no
spec-delete verb. Never re-put. On `subtype=record_missing`, the candidate
was already promoted and cleared (or never recorded here): locate the issue's
attached spec via the tracker id and adopt it. **Under any autonomy marker**
(`FLOW_AUTONOMOUS=1`, `mode:autonomous`) a CAS conflict resolves to `sync defer` like every other
collision - adopting a winner and retiring a spec is a human-confirmed
resolution, not an autonomous one. Only after the linked mint, merge-base seed,
back-reference, and the normal spec-keyed receipt all succeed may the caller
consume the record with `sync create-first-clear`. These four helpers
exclusively own the retry record; do not recompute its hash or read, write, or
delete its file directly.

**Back-reference:** write `flow:<spec-id>` only after the durable local link
exists. A failed back-reference leaves the recovery record available for a
safe retry.
