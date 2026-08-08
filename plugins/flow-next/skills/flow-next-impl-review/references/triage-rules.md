# Trivial-diff triage — rules, receipt shape, LLM judge (fn-29.6)

Read this only when a triage result needs explaining or auditing (a SKIP you
want to justify, a misclassification you suspect, or an LLM-judge run). The
executable pre-check lives inline in [../SKILL.md](../SKILL.md) Step 0.5 — a
normal review just runs it and reads the exit code.

**Default behavior:** deterministic whitelist only (no LLM call). Ambiguous
diffs default to REVIEW. Opt-in to LLM judge with `FLOW_TRIAGE_LLM=1`.

**Opt-out:**
- `--no-triage` argument on the skill
- `FLOW_RALPH_NO_TRIAGE=1` env var (Ralph runs)

**Receipt shape on SKIP:**

```json
{
  "type": "impl_review",
  "id": "fn-29.6",
  "mode": "triage_skip",
  "base": "main",
  "verdict": "SHIP",
  "reason": "lockfile-only (bun.lock)",
  "source": "deterministic",
  "changed_file_count": 1,
  "timestamp": "2026-04-24T10:00:00Z"
}
```

Ralph reads `verdict` — `SHIP` satisfies the gate regardless of `mode`. No
Ralph-script changes required.

**Triage rules (deterministic layer):**

| Shape | Action |
|-------|--------|
| Any code file (`.py`, `.ts`, `.go`, `.sh`, ...) present | REVIEW (AC9) |
| Any `.flow/specs/*.md` / `.flow/specs/*.json` / `.flow/tasks/*.md` / legacy `.flow/epics/*.json` | REVIEW |
| All files are lockfiles (`package-lock.json`, `bun.lock`, ...) | SKIP |
| All files are docs (`.md`, `.mdx`, `.txt`, `.rst`, `.adoc`) | SKIP |
| All files are under generated paths (`codex/`, `vendor/`, `node_modules/`, ...) | SKIP |
| Release-chore: `plugin.json` / `package.json` / `Cargo.toml` / `pyproject.toml` + optional `CHANGELOG.md` | SKIP |
| Lockfile + manifest combo | SKIP |
| Anything else | REVIEW (conservative fallthrough) |

When `FLOW_TRIAGE_LLM=1`, ambiguous diffs get a one-shot fast-model call
(`gpt-5.6-luna` @high for codex backend, `claude-haiku-4.5` @low for copilot backend).
Malformed LLM output falls through to REVIEW.
