# Model-pin refresh ceremony

This reference is reached only when `MODELS_ASK=1`. Follow every subsection in
order. The host agent probes, judges, proposes, and stamps; flowctl only stores
and schema-validates. Never spawn a second LLM to rank models. Never block setup
on a probe failure.

## A. Probe installed CLIs

Use the `HAVE_*` values from workflow Step 6a. All probes are foreground,
short-timeout, and skipped when the matching CLI is absent. A failed or timed
out probe means unknown for this installation, never setup failure.
Skip each probe when its CLI is absent.

```bash
CURRENT_MODELS=$("${PLUGIN_ROOT}/scripts/flowctl" config get models --raw --json 2>/dev/null || echo '{"value":null}')
CURRENT_VERIFIED_AT=$("${PLUGIN_ROOT}/scripts/flowctl" config get models.verifiedAt --raw --json 2>/dev/null | jq -r 'if .value == null then "" else (.value | tostring) end')

if [[ "$HAVE_CURSOR" == "1" ]]; then
  CURSOR_MODELS=$(cursor-agent --list-models 2>/dev/null | head -200 || true)
fi
if [[ "$HAVE_COPILOT" == "1" ]]; then
  COPILOT_MODELS=$(copilot -p "/model" 2>/dev/null | head -100 || true)
fi
```

When `HAVE_CODEX=1`, run a short foreground `codex accept-probe` against each
candidate model id the agent is considering. Try one candidate at a time with a tight timeout;
`requires a newer version of Codex` / model-not-found rejects it, a clean reply
accepts it. Example shape:

```bash
timeout 20 codex exec -m gpt-5.6-sol --skip-git-repo-check "reply: ok" </dev/null
```

Record accepted candidates into `CODEX_ACCEPTED`. Optionally capture CLI
versions into a free-form `models.verifiedWith` note.

## B. Scan failure feedback

Scan recent receipts under `.flow/review-receipts/` plus receipt paths already
known. A non-null receipt `model` that differs from the corresponding current
pin (`models.roles.review.<backend>`, else the registry baseline) proves a
fallback-ladder activation. Prefer a pin receipts actually ran successfully;
prefer replacing a pin that repeatedly laddered away. Missing receipts or empty
model fields are no signal.

## C. Judge the role map

Use host knowledge, optional current primary-source lookup for brand-new tier
names, probe ground truth, and receipt feedback. Only propose pins for a backend
whose CLI is present or which already has an on-disk pin.

| Role | Intent | Seed direction (agent re-ranks) |
|---|---|---|
| `fastJudge` | fast/cheap triage | codex: luna-class; copilot: haiku-class; cursor: composer / luna-low |
| `review` | strongest acceptable review gate | codex: sol:medium; never mini/nano or a weak silent-ship default |
| `delegate` | value-tier implementer | codex: terra-class; feeds `work.delegateModel` only when that leaf is unset |
| `scoutFast` | cheap codex-mirror scout | luna-class |
| `scoutIntelligent` | judgment codex-mirror scout | stronger 5.6-family tier |

Backends are `codex`, `copilot`, and `cursor`. Pin shape is `model` or
`model:effort`; Cursor bakes effort into the model id, so prefer a bare model.
Do not invent roles.

## D. Propose

Diff the judged map against on-disk `models.roles`. Before asking, print every
`current -> proposed (one-line reason)` row. If the map is unchanged, say so and
lean on `Stamp verifiedAt only`.

Ask via `AskUserQuestion` (the Codex mirror uses its numbered-prompt rewrite):

```json
{
  "header": "Model pins",
  "question": "Refresh models.roles pins from today's probe? (flowctl stores; you pick. Re-run setup anytime to refresh again.)",
  "options": [
    {"label": "Accept proposed map (Recommended)", "description": "Write the judged pins via flowctl config set and stamp models.verifiedAt today"},
    {"label": "Stamp verifiedAt only", "description": "Keep every current pin; only refresh models.verifiedAt to today"},
    {"label": "Skip", "description": "Write nothing; leave models.roles and models.verifiedAt untouched"}
  ],
  "multiSelect": false
}
```

Stop the current tool sequence for the answer. Do not place an ask and its
answer-consuming writes in one shell fence.

## E. Write accepted pins

Only an accepted write path mutates config:

```bash
"${PLUGIN_ROOT}/scripts/flowctl" config set models.roles.<role>.<backend> "<pin>" --json
"${PLUGIN_ROOT}/scripts/flowctl" config set models.verifiedAt "$(date -u +%Y-%m-%d)" --json
```

For `Stamp verifiedAt only`, run only the second command. An optional accepted
write may also set `models.verifiedWith`. `Skip` writes nothing and sets
`MODELS_CEREMONY="skipped"`.

After a write, read back `models.verifiedAt` plus one changed pin with
`config get --raw --json`; expose failed persistence. Set `MODELS_CEREMONY` to
`written`, `stamped`, or `skipped`.

## F. Optional routing-table refresh

Offer (not force) a routing-table refresh.
After `written` or `stamped`, offer via `AskUserQuestion`:

- `Refresh routing table` — re-enter Step 7's Model Routing scaffold pipeline,
  or perform a focused edit of an existing
  `<!-- flow-next:model-routing:start -->` block when the scaffold question was
  not offered. Never silently overwrite customization; preserve the same
  Keep/Overwrite discipline.
- `Leave routing table` — recommended when the user did not ask for it.

Do not offer this after a skipped pin write.
