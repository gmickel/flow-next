# Review question (gated reference)

> Read from workflow.md Step 6d only when `CURRENT_BACKEND` is empty.

**Review question** (include if CURRENT_BACKEND is empty):

**Four options, not seven.** Each menu below is a catalog; the question carries four of its options, in the menu's order: Host, None, and the first two CLI options whose `HAVE_*` is 1 (when fewer than two are detected, fill from the undetected ones in menu order; on `PLATFORM=codex`, take Codex CLI last, since it is the writer's family). A backend left off the menu is set with `flowctl config set review.backend <name>`, which Step 8's summary names.

**When `PLATFORM=cursor`** — lead with `host` (Recommended); keep every existing backend selectable; label the Cursor CLI option as circular/secondary from inside Cursor:
```json
{
  "header": "Review",
  "question": "Which review backend? Plans and implementations get reviewed before they land. From inside Cursor, prefer a host-native fresh-context subagent pinned cross-family via AGENTS.md model-routing (no second CLI). External CLIs remain available. Each review round is a serial pass the pipeline waits on - usually the largest wall-clock item in a run. Guide: https://flow-next.dev/guides/review-workflow/",
  "options": [
    {"label": "Host (Recommended)", "description": "Fresh-context host-native subagent; name a cross-family model on the `reviewer` tier of the AGENTS.md routing block (setup writes that block commented out; the slugs are yours to fill in). No external CLI. Preferred from inside Cursor."},
    {"label": "Codex CLI", "description": "OpenAI's codex CLI, reviews on its top reasoning tier (GPT family). Cross-platform, simple setup. <detected if HAVE_CODEX=1, (not detected) if HAVE_CODEX=0>"},
    {"label": "Copilot CLI", "description": "Routes to Claude- or GPT-family reviewers via your GitHub Copilot plan. Requires gh copilot auth. <detected if HAVE_COPILOT=1, (not detected) if HAVE_COPILOT=0>"},
    {"label": "Cursor CLI (secondary — circular from inside Cursor)", "description": "Runs the external cursor-agent CLI. Circular when already inside Cursor — prefer Host. Still selectable for multi-family reach via the cursor-agent model menu. <detected if HAVE_CURSOR=1, (not detected) if HAVE_CURSOR=0>"},
    {"label": "Claude Code CLI", "description": "Runs claude -p headless, read-only, on a Claude-family reviewer. Cross-platform; needs the claude CLI on PATH. Same-family when Claude Code is the writer - the receipt records it; prefer Codex or Host there when family independence matters. <detected if HAVE_CLAUDE=1, (not detected) if HAVE_CLAUDE=0>"},
    {"label": "None", "description": "No review gates. Fastest runs; tests/lint still gate and work still audits large or risky diffs in-host, but nothing checks R-ID coverage at spec completion - fits diffs you read yourself. Set later: flowctl config set review.backend <name>, or per-run via --review"}
  ],
  "multiSelect": false
}
```

**When `PLATFORM=grok`** — offer `host` with the fail-closed cross-family caveat (this host reaches only one model family natively) plus every external backend; when `HAVE_CODEX=1` mark Codex Recommended (true cross-family vs a Grok writer):
```json
{
  "header": "Review",
  "question": "Which review backend? Plans and implementations get reviewed before they land. This host reaches only one model family natively — host-native review fails closed unless the writer is from another family; cross-family review comes via bridge backends (codex/cursor/copilot/claude). Each review round is a serial pass the pipeline waits on - usually the largest wall-clock item in a run. Guide: https://flow-next.dev/guides/review-workflow/",
  "options": [
    {"label": "Host", "description": "Fresh-context host-native subagent; name the model on the `reviewer` tier of the AGENTS.md routing block (setup writes it commented out; you fill in the slug). Fail-closed: this host is single-native-family — native host review refuses same-family self-review (interactive → ask; autonomous → NEEDS_HUMAN) unless the writer is non-Grok. Cross-family via bridges."},
    {"label": "Codex CLI", "description": "OpenAI's codex CLI, reviews on its top reasoning tier (GPT family). Cross-platform, simple setup. <detected if HAVE_CODEX=1, (not detected) if HAVE_CODEX=0>"},
    {"label": "Copilot CLI", "description": "Routes to Claude- or GPT-family reviewers via your GitHub Copilot plan. Requires gh copilot auth. <detected if HAVE_COPILOT=1, (not detected) if HAVE_COPILOT=0>"},
    {"label": "Cursor CLI", "description": "Runs cursor-agent with a multi-family model menu (pick the family that did not write the diff). Billed to your Cursor subscription. <detected if HAVE_CURSOR=1, (not detected) if HAVE_CURSOR=0>"},
    {"label": "Claude Code CLI", "description": "Runs claude -p headless, read-only, on a Claude-family reviewer. Cross-platform; needs the claude CLI on PATH. Same-family when Claude Code is the writer - the receipt records it; prefer Codex or Host there when family independence matters. <detected if HAVE_CLAUDE=1, (not detected) if HAVE_CLAUDE=0>"},
    {"label": "None", "description": "No review gates. Fastest runs; tests/lint still gate and work still audits large or risky diffs in-host, but nothing checks R-ID coverage at spec completion - fits diffs you read yourself. Set later: flowctl config set review.backend <name>, or per-run via --review"}
  ],
  "multiSelect": false
}
```

**When `PLATFORM` is neither `cursor` nor `grok`** (Claude Code / Droid / Codex / OpenCode — unchanged; Cursor and Grok each use their dedicated menu above; OpenCode uses this default Host + None menu):
```json
{
  "header": "Review",
  "question": "Which review backend? Plans and implementations get reviewed before they land; a review backend is a second AI CLI - ideally a DIFFERENT model family than the one writing the code, for uncorrelated blind spots. Each review round is a serial pass the pipeline waits on - usually the largest wall-clock item in a run - so pick the gate you will actually keep. Each CLI needs its own install/subscription. Guide: https://flow-next.dev/guides/review-workflow/",
  "options": [
    {"label": "Codex CLI", "description": "OpenAI's codex CLI, reviews on its top reasoning tier (GPT family). Cross-platform, simple setup. <detected if HAVE_CODEX=1, (not detected) if HAVE_CODEX=0>"},
    {"label": "Copilot CLI", "description": "Routes to Claude- or GPT-family reviewers via your GitHub Copilot plan. Requires gh copilot auth. <detected if HAVE_COPILOT=1, (not detected) if HAVE_COPILOT=0>"},
    {"label": "Cursor CLI", "description": "Runs cursor-agent with a multi-family model menu (pick the family that did not write the diff). Billed to your Cursor subscription. <detected if HAVE_CURSOR=1, (not detected) if HAVE_CURSOR=0>"},
    {"label": "Claude Code CLI", "description": "Runs claude -p headless, read-only, on a Claude-family reviewer. Cross-platform; needs the claude CLI on PATH. Same-family when Claude Code is the writer - the receipt records it; prefer Codex or Host there when family independence matters. <detected if HAVE_CLAUDE=1, (not detected) if HAVE_CLAUDE=0>"},
    {"label": "Host", "description": "Host-native fresh-context subagent - no second CLI to install. Name a cross-family model on the `reviewer` tier of the routing block (setup writes it commented out; you fill in the slug). Keeps every review gate at the lowest setup cost."},
    {"label": "None", "description": "No review gates. Fastest runs; tests/lint still gate and work still audits large or risky diffs in-host, but nothing checks R-ID coverage at spec completion - fits diffs you read yourself. Set later: flowctl config set review.backend <name>, or per-run via --review"}
  ],
  "multiSelect": false
}
```

When `HAVE_CODEX=1` AND `PLATFORM` is NOT `codex` AND `PLATFORM` is NOT `cursor`, append ` (Recommended - cross-family default)` to the `Codex CLI` label: the recommended multi-model pipeline reviews cross-family FROM THE WRITER, and on a Claude Code / Droid / Grok host codex review is a different family than the session writer - so this question carries the ceremony's `review.backend codex` offer while the key is unset. On `PLATFORM=cursor` do NOT add the Codex Recommended label — `Host (Recommended)` already leads. On a Codex host (`PLATFORM=codex`) do NOT add the label: the writer is GPT-family (the session model, or an `implementer` tier pointing at the same family), so codex review would be SAME-family - prefer a detected non-GPT backend there (claude, or copilot / cursor with a Claude-family model) and leave the options unannotated when none is detected. When `review.backend` is ALREADY set to something else, this question is skipped (existing config is never silently overwritten) - the user changes it later with `flowctl config set review.backend <name>`, surfaced in 6c's current-config notice.

Stored value is a bare backend name by default (`host` / `codex` / `copilot` / `cursor` / `claude` / `none`). Power users can also write a full spec like `codex:<model>:high`, `copilot:<model>:xhigh`, `cursor:<model>` (cursor takes a model only — no `:effort`), or `claude:<model>:<effort>` via `flowctl config set review.backend <spec>` after setup — the review commands accept both forms. Backend `host` is bare only (no `host:<model>` — the model is named on the `reviewer` tier of the AGENTS.md routing block).
