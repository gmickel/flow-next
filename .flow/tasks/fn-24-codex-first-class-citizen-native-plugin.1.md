Create the Codex plugin manifest and marketplace entry so flow-next is discoverable by Codex's native plugin system and the codex-plugin-scanner.

## Files to create

### plugins/flow-next/.codex-plugin/plugin.json

Codex plugin manifest. Must follow the Codex plugin.json schema:
- `name`: "flow-next" (same as Claude Code plugin name — unchanged)
- `version`: must match current version in .claude-plugin/plugin.json (0.26.1)
- `description`: same core description, mention Codex compatibility
- `author`: Gordon Mickel (gordon@mickel.tech, https://mickel.tech)
- `homepage`: https://mickel.tech/apps/flow-next
- `repository`: https://github.com/gmickel/gmickel-claude-marketplace
- `license`: "MIT"
- `keywords`: ["workflow", "planning", "execution", "automation", "ai"]
- `skills`: "./codex/skills/" (points to pre-patched Codex skills, created in task 2)
- `interface` object:
  - `displayName`: "Flow-Next"
  - `shortDescription`: "Plan-first workflow with subagent execution"
  - `longDescription`: description of what flow-next does, mention .flow/ tracking, worker subagents, Ralph mode, review gates
  - `developerName`: "Gordon Mickel"
  - `category`: "Productivity"
  - `capabilities`: ["Read", "Write"]
  - `websiteURL`: "https://mickel.tech/apps/flow-next"
  - `brandColor`: "#3B82F6"

### .agents/plugins/marketplace.json

Codex marketplace at repo root:
```json
{
  "name": "flow-next-marketplace",
  "interface": {
    "displayName": "Flow-Next Plugins"
  },
  "plugins": [
    {
      "name": "flow-next",
      "source": {
        "source": "local",
        "path": "./plugins/flow-next"
      },
      "policy": {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL"
      },
      "category": "Productivity"
    }
  ]
}
```

## Validation
- Verify JSON is valid: `jq . plugins/flow-next/.codex-plugin/plugin.json`
- Verify marketplace JSON: `jq . .agents/plugins/marketplace.json`
- If codex-plugin-scanner available: `pipx run codex-plugin-scanner lint plugins/flow-next`

## Notes
- Do NOT modify any existing .claude-plugin/ files
- The skills path points to `./codex/skills/` which will be populated in task 2-3
- Create the `.codex-plugin/` directory alongside the existing `.claude-plugin/`
- Create the `.agents/plugins/` directory at repo root

## Acceptance criteria
- [ ] `plugins/flow-next/.codex-plugin/plugin.json` exists and is valid JSON
- [ ] `.agents/plugins/marketplace.json` exists and is valid JSON
- [ ] Plugin version matches Claude Code version (0.26.1)
- [ ] Plugin name is "flow-next" in both manifests
- [ ] No changes to existing .claude-plugin/ files
