# Interactive setup questions (gated reference)

> **Loaded only when SKILL.md's setup step routes here** — an interactive run
> (`AUTONOMOUS=0`) whose arguments carried no branch (and, when `REVIEW_BACKEND`
> is `ASK`, no review) option. An autonomous run never reads this file: it asks
> nothing and applies the autonomous defaults in SKILL.md.

Ask ONE of the two blocks below, then wait for the response. Parse naturally —
user may reply terse or ramble via voice.

## REVIEW_BACKEND is rp, codex, copilot, cursor, host, or none (already configured)

Only ask the branch question. Show override hint:

```
Quick setup: Where to work?
a) Current branch b) New branch c) Isolated worktree

(Reply: "a", "current", or just tell me)
(Tip: --review=rp|codex|copilot|cursor|host|export|none overrides configured backend)
```

## REVIEW_BACKEND is ASK (not configured)

Ask both branch AND review questions:

```
Quick setup before starting:

1. **Branch** — Where to work?
 a) Current branch
 b) New branch
 c) Isolated worktree

2. **Review** — Run Carmack-level review after?
 a) Codex CLI
 b) RepoPrompt
 c) Export for external LLM
 d) None (configure later with --review flag)

(Reply: "1a 2a", "current branch, codex", or just tell me naturally)
```

## Defaults when empty/ambiguous

- Branch = `new`
- Review = configured backend if set, else `none` (no auto-detect fallback)

**Do NOT read files or write code until user responds.**
