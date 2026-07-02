# Spec Template & Acceptance-Criteria Discipline

The canonical spec scaffold lives at [`../templates/spec.md`](../templates/spec.md). This doc covers the **rules** that surround it — R-ID semantics, confidence anchors, introduced-vs-pre-existing, protected artifacts, trivial-diff skip, and the 4-tier template discovery cascade — not the section list itself (R17: cross-link, never re-embed).

## Canonical scaffold

[`../templates/spec.md`](../templates/spec.md) is the single source of truth for the spec structure. The template's frontmatter enumerates the seven canonical sections + auxiliary sections; do not duplicate that list here. Read the template directly before authoring.

The template is consumed by:

| Consumer | Role |
|----------|------|
| `flow-next-capture` | synthesizes a spec from conversation context |
| `flow-next-interview` | refines a spec via Q&A (`--scope=business|technical|both`) |
| `flow-next-plan` | breaks a spec into tasks |
| `CLAUDE.md` | "Creating a spec" guide cross-links the template rather than embedding |

## 4-tier discovery cascade

When a skill needs the spec template, it walks four locations in order (first match wins):

1. `<repo_root>/SPEC.md` — your customized scaffold (uppercase preferred)
2. `<repo_root>/spec.md` — lowercase honored when uppercase absent
3. `.flow/templates/spec.md` — project-local copy from `/flow-next:setup`
4. `${PLUGIN_ROOT}/templates/spec.md` — bundled (canonical source of truth)

Case-insensitive FS handling (macOS APFS, Windows NTFS) and the bash walker that implements it live in [`../references/spec-template-discovery.md`](../references/spec-template-discovery.md). Copy + customize tier 1 to override the scaffold for your project.

## Acceptance criteria — R-ID rules

R-IDs are numbered acceptance criteria written as `**R1:** ...`, `**R2:** ...` in plain markdown prose under the `## Acceptance Criteria` section (the canonical section name; the scaffold heading is the authoritative source).

```markdown
## Acceptance Criteria
- **R1:** OAuth login works for Google provider
- **R2:** Session persists across page reloads
- **R3:** Logout clears session tokens
```

Task specs reference them via frontmatter when relevant:

```yaml
---
satisfies: [R1, R3]
---
```

Rules:

- Plain markdown prose, not YAML — keeps specs human-editable.
- **Renumber-forbidden** after the first review cycle. Deletions leave gaps (`R1, R3, R5` stays that way); new criteria take the next unused number.
- **Append-only across passes.** A `--scope=technical` pass cannot rewrite or renumber R-IDs added by an earlier `--scope=business` pass; it appends new criteria with the next unused number.
- Plan skill writes R-IDs on creation; plan-sync preserves them through drift updates.
- Impl-review and spec-completion review emit a per-R-ID coverage table (met / partial / not-addressed / deferred).
- Any unaddressed R-ID flips verdict to `NEEDS_WORK`; receipt carries an `unaddressed: ["R2", "R5"]` array so the fix loop has targeted work.

## Confidence anchors (0 / 25 / 50 / 75 / 100)

Reviewers score every finding on exactly five discrete values:

| Anchor | Meaning |
|--------|---------|
| 100 | Verifiable from code alone, zero interpretation. |
| 75 | Full execution path traced — input → branch → wrong output. |
| 50 | Depends on conditions visible but not fully confirmable. |
| 25 | Requires runtime conditions with no direct evidence. |
| 0 | Speculative. |

**Suppression gate:** after dedup, findings below 75 are dropped. Exception: P0 findings at 50+ survive. Reviews report `suppressed_count` by anchor; receipt optionally carries it as `{"50": 3, "25": 7, "0": 2}`.

## Introduced vs pre-existing

Each finding is classified:

- `introduced: true` — caused by this branch's diff.
- `pre_existing: true` — broken on the base branch.

Verdict gate considers only `introduced` findings. Pre-existing issues surface in a separate non-blocking "Pre-existing issues" section. Receipt carries `introduced_count` + `pre_existing_count` so Ralph stops fighting bugs it didn't introduce.

## Protected artifacts

Review prompts carry a hardcoded never-flag list — findings recommending deletion or gitignore of these paths are discarded during synthesis:

- `.flow/*` (specs, tasks, memory, state)
- `.flow/bin/*` (bundled flowctl)
- `.flow/memory/*` (learnings store)
- `docs/plans/*`, `docs/solutions/*` (when the project uses them)
- `scripts/ralph/*` (Ralph harness)

Prevents cross-model reviewers unfamiliar with flow-next conventions from proposing destructive cleanups.

## Trivial-diff skip

`flowctl triage-skip --base <ref>` runs a deterministic whitelist (lockfile-only / docs-only / release-chore / generated-file-only) and returns `VERDICT=SHIP` without invoking the configured backend. Receipt is written with `mode: triage_skip`, `source: deterministic`, and a one-line reason.

```bash
flowctl triage-skip --base main
# VERDICT=SHIP
# reason=lockfile-only (bun.lock)
# source=deterministic
```

Optional LLM layer (gpt-5-mini / claude-haiku-4.5) for ambiguous diffs is gated behind `FLOW_TRIAGE_LLM=1`. On by default in Ralph mode; opt-out via `--no-triage` or `FLOW_RALPH_NO_TRIAGE=1`.

## Receipt schema (additive only)

All review receipts may carry these optional fields; existing consumers that read by key ignore unknowns:

```json
{
  "mode": "codex",
  "verdict": "NEEDS_WORK",
  "unaddressed": ["R2", "R5"],
  "suppressed_count": {"50": 3, "25": 7, "0": 2},
  "introduced_count": 2,
  "pre_existing_count": 4
}
```

## See also

- [`../templates/spec.md`](../templates/spec.md) — the canonical scaffold (section list, scope-owner annotations, flat-vs-substructured Decision Context).
- [`../../../GLOSSARY.md`](../../../GLOSSARY.md) — definitions for *Spec*, *Task*, *R-ID*, *Frozen-at-handover*.
- [`../skills/flow-next-interview/SKILL.md`](../skills/flow-next-interview/SKILL.md) — 4-tier discovery cascade walker.
- [`flowctl.md`](flowctl.md) — `flowctl spec create / set-plan / export-cognitive-aid` reference.
