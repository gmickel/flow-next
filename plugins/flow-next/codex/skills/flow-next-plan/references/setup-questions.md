# Plan setup questions

Load this reference only when the SKILL.md setup gate fired — `REVIEW_BACKEND`
is `ASK` (not configured) and the run is not autonomous. Configured backends and
`AUTONOMOUS=1` never reach this file.

**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

Ask the setup questions below as plain text — never via the `plain-text numbered prompt` tool.

**RepoPrompt eligibility** (compute once, before any question below):

```bash
# Prefer RepoPrompt CE; retain Classic only as the final compatibility rung.
if command -v rpce-cli >/dev/null 2>&1 \
  || [ -x "$HOME/RepoPrompt/repoprompt_ce_cli" ] \
  || [ -x "$HOME/Library/Application Support/RepoPrompt CE/repoprompt_ce_cli" ] \
  || command -v rp-cli >/dev/null 2>&1; then
  RP_ELIGIBLE=1
else
  RP_ELIGIBLE=0
fi
```

Eligibility governs *review-backend proposals only* — an explicit `--review=rp` argument (parsed in SKILL.md) is always honored and errors at runtime if no supported RepoPrompt CLI resolves.

When `RP_ELIGIBLE=1`:

```
Quick setup before planning:

1. **Plan depth** — How detailed?
   a) Short — problem, acceptance, key context only
   b) Standard (default) — + approach, risks, test notes
   c) Deep — + phases, alternatives, rollout plan

2. **Review** — Run Carmack-level review after?
   a) Codex CLI
   b) RepoPrompt
   c) Export for external LLM
   d) None (configure later)

(Reply: "1a 2d", or just tell me naturally)
```

When `RP_ELIGIBLE=0` (not macOS, no supported RepoPrompt CLI): drop the RepoPrompt review option:

```
Quick setup before planning:

1. **Plan depth** — How detailed?
   a) Short — problem, acceptance, key context only
   b) Standard (default) — + approach, risks, test notes
   c) Deep — + phases, alternatives, rollout plan

2. **Review** — Run Carmack-level review after?
   a) Codex CLI
   b) Export for external LLM
   c) None (configure later)

(Reply: "1a 2c", or just tell me naturally)
```

Wait for response. Parse naturally — user may reply terse ("1a 2b") or ramble via voice.

**Defaults when empty/ambiguous:**
- Depth = `standard` (balanced detail)
- Research = `repo-scout`
- Review = configured backend if set, else `none`
