# Opt-in development evidence and spec approval for regulated teams

## Goal & Context

Teams in regulated environments (GxP, medical, finance) must show what was required, what was built, how it was tested and reviewed, and who approved it. flow-next already produces most of that during a normal run: R-ID acceptance criteria, R-ID-named tests, review receipts with findings, QA receipts with captures, and PRs. But much of it is temporary, and nothing turns it into a traceability record. [paraphrase]

Two end-to-end demo runs on a neutral sample application showed that agent instructions alone get most of the way there:
- an evidence policy in the instruction file;
- standing criteria in `.flow/criteria.md`. [paraphrase]

Three gaps need code, because instructions are probabilistic and the record has to be mechanical: [paraphrase]
- **Agent-copied evidence.** The agent copied receipts by hand. A round-1 review receipt was overwritten, and the review flagged the evidence folder as missing because it is created only after review.
- **Self-reported traceability.** A private script built the traceability matrix. An agent-written matrix would be the agent reporting on its own work.
- **No spec approval gate.** Spec approval had no place in the pipeline: after a human approved the spec PR, readiness was flipped by hand before `flow --auto` continued.

This should be useful for everyone in that kind of business, with no customer-specific content. It should have completely no effect for anyone not in this kind of regulated business. [paraphrase]

<!-- Source: 60% user / 30% [paraphrase] / 10% [inferred] -->

## Architecture & Data Models

The feature has three parts. Each is off or inert unless a team opts in. [paraphrase]

- **Evidence persistence (`evidence.persist`).** flowctl writes each record into a committed per-spec evidence folder at the moment it writes or reads that record today. The agent does no copying. [paraphrase]
- **Spec approval gate (`spec.approval`).** Under `pr`, spec authoring ends by opening the spec as a pull request instead of marking it ready. Routing code treats the spec as ready only once that PR is merged with an approving review. The forge's branch protection and the agent's identity decide who may approve; flow-next reads and records the approval and does not enforce it. [paraphrase]
- **Traceability export (`flowctl trace <spec>`).** A read-only command that builds a per-criterion matrix from the spec, the task evidence, the evidence folder and the forge approvals, and runs a mechanical gap check. [paraphrase]

The three parts compose but don't depend on each other. `trace` works without persistence and reports what is missing. [inferred]

## API Contracts

Config, in the existing `.flow/config.json` and `flowctl config set` surface:

| Key | Values | Default | Effect when not default |
|---|---|---|---|
| `evidence.persist` | `off` \| `on` | `off` | flowctl writes committed evidence per spec (R2-R4) |
| `evidence.dir` | repo-relative path | `.flow/evidence` | Root of the per-spec evidence folders |
| `spec.approval` | `local` \| `pr` | `local` | Spec readiness comes from a merged, approved spec PR (R6-R7) |

Command: `flowctl trace <spec-id> [--format csv|md] [--json]`. It writes to stdout, and the `--json` form carries the gap-check result. Exit code `0` means no gaps, `1` means gaps were found, `2` means an error. [inferred]

## Edge Cases & Constraints

- **Committed captures.** Evidence folders hold QA captures (images). Committing them grows the repository; teams that enable persistence accept that. [inferred]
- **Forge access.** Approvals are read from the forge flow-next already lands through. If the forge can't be reached, the result is "unknown", never a guessed approval. [inferred]
- **Identity separation.** Self-approval is prevented by forge configuration (an agent identity separate from the human, plus branch protection). flow-next documents this and doesn't add its own identity checks. [paraphrase]

## Acceptance Criteria

- **R1:** Nothing changes for normal users. With default config (`evidence.persist` absent or `off`, `spec.approval` absent or `local`), the following are byte-identical to the release before this change, on every supported host and the Codex mirror: [paraphrase]
  - every skill prompt;
  - every receipt;
  - every file written;
  - every routing decision;
  - every existing command's output.
  
  The gated references are never read on the default path, and `/flow-next:setup` asks no new question. Existing `.flow/config.json` files without the new keys stay valid against the published config schema. A smoke test proves the default path, and the existing test suites pass unchanged. [paraphrase]
  - Errors: only the literal `on` activates persistence. Any other value for `evidence.persist` (bool, typo, null) behaves as `off`. [inferred]
- **R2:** With `evidence.persist on`, flowctl writes committed copies into `<evidence.dir>/<spec-id>/` at the moment each record is produced:
  - every plan, implementation and completion review receipt, one file per review round, so a later round never overwrites an earlier one;
  - the QA receipt and its captures;
  - the test output each task records as evidence. [paraphrase]
  
  The agent never needs to copy anything.
  - Errors: an `evidence.dir` that resolves outside the repository, or through a symlink, is refused with a clear message.
  - Errors: a failed write fails the stage that produced the record, with the reason. The stage never reports success. [inferred]
- **R3:** With `evidence.persist on`, evidence written during a stage travels in that stage's existing commit, or in the next one. No reviewer is asked to judge evidence for a round that has not finished yet. [paraphrase]
  - No error surface beyond R2.
- **R4:** With `evidence.persist on`, the evidence folder holds a run record:
  - the flow-next version;
  - the host;
  - per review, the reviewer backend and model;
  - per stage, the implementing model where flow-next knows it. [paraphrase]
  
  An unknown value is written as unknown, never guessed. [inferred]
- **R5:** `spec.approval local` (default) leaves spec readiness exactly as today. [paraphrase]
  - No error surface beyond R1.
- **R6:** Under `spec.approval pr`, capture, plan and refine end by opening the spec as a pull request instead of marking it ready, and `flow --auto` never starts implementation before approval. Routing treats the spec as ready only when that PR is merged with at least one approving review; no manual readiness step is needed after the merge. [paraphrase] [strategy:Autonomous mode]
  - Errors: a spec PR closed without merge → not ready, and reported.
  - Errors: forge unreachable → not ready (fails closed), with the reason.
  - Errors: an invalid `spec.approval` value is rejected by `config set`, and on read it stops with a clear message instead of falling back to `local`. [inferred]
- **R7:** Under `spec.approval pr`, the approver's identity and time and the merge identity and time are recorded with the spec. With `evidence.persist on`, they are also recorded in its evidence folder. [inferred]
- **R8:** `flowctl trace <spec-id>` prints a matrix in CSV or Markdown with one row per R-ID. Each row lists:
  - the tests that cover it;
  - their result;
  - its QA evidence;
  - review findings that name it;
  - the spec and implementation approvals. [paraphrase]
  
  A gap check runs as part of it: every criterion must have evidence, and every piece of evidence must name a criterion. Gaps produce a non-zero exit. Without `evidence.persist` the command still runs and reports missing evidence as gaps. [paraphrase]
  - Errors: unknown spec id → exit 2.
  - Errors: forge unreachable → approvals show as unknown, with a warning, never invented. [inferred]
- **R9:** Repository docs cover the new keys and `trace`: the runtime docs, a one-line entry in the README, and the changelog. [paraphrase]
- **R10:** flow-next.dev has a "Flow-Next in regulated environments" page. It contains:
  - a copy-paste setup: the config keys, `.flow/criteria.md`, QA on, and an agent identity with branch protection;
  - the two-stage QA framing: development evidence feeds the team's QS;
  - a "what this does not replace" box;
  - example outputs from a neutral demo application. [paraphrase]
  
  The page sits in the site's single navigation source and in llms.txt. The landing page gains a bento for it. [paraphrase]
- **R11:** The downstream chain in `downstream-properties.md` is walked for this release: mickel.tech, the AI x SDLC guide, the microsite only if it needs a change, and the vault release timeline and messaging. [paraphrase]
- **R12:** Every doc and page says flow-next supports and feeds a team's validation. None claims that flow-next makes anything compliant or certified. None names a customer or customer project. [paraphrase]

## Boundaries

- No single `regulated: true` preset or mode switch; teams set explicit keys. [paraphrase]
- No customer-facing packaging (localization, PDFs, redaction); that stays outside flow-next. [paraphrase]
- No identity or approval enforcement inside flow-next; the forge enforces it. [paraphrase]
- No new spec template section for combination spaces, and no criterion-link fields: R-ID test names, standing criteria and docs cover them. [paraphrase]
- No "surface but don't block" variant of the spec approval gate. [paraphrase]

## Decision Context

**One spec, including the downstream work.** The maintainer chose one spec over three, and asked for the downstream work to be part of it. [paraphrase]

**Config keys instead of instructions.** The demo runs worked with instructions alone, but showed where the agent's copying and narration fail unattended. Under G4, each piece of structure names the unattended failure it prevents: [paraphrase]
- `evidence.persist` prevents review and QA evidence from being silently lost or overwritten;
- `spec.approval` prevents `flow --auto` from implementing a spec nobody approved;
- `trace` prevents a traceability record from being the agent's own account of its work. [paraphrase]

**Fit with strategy.**
- `spec.approval pr` turns the documented Spec-as-PR team pattern into a mechanism, and it keeps readiness as the human's explicit signal: a merged, approved PR is that signal. [strategy:Spec-driven team patterns] [strategy:Autonomous mode]
- `trace` and the evidence writes involve no judgment. They are receipt plumbing, which flowctl may carry under its burden-of-proof rule. [inferred]

**Behaviour when off.** Default-off follows the `pipeline.qa` and `pilot.autonomy` precedent: any value except the literal one that activates a feature behaves as off. The approval gate is the exception. It fails closed on an invalid value, because a typo would otherwise silently remove a gate a team chose. [inferred]

**Rejected alternatives.**
- A `regulated` preset hides what it changes and implies compliance. [paraphrase]
- A surfacing-only gate was rejected as YAGNI. [paraphrase]
