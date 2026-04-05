Add `agents/openai.yaml` metadata files to key skills for Codex app and IDE UI display.

## Background

Codex skills support an optional `agents/openai.yaml` file that controls:
- `interface.display_name` — user-facing name in Codex UI
- `interface.short_description` — user-facing description
- `interface.brand_color` — hex color for UI theming
- `interface.default_prompt` — suggested prompts when invoking
- `policy.allow_implicit_invocation` — whether Codex can auto-trigger the skill

## Skills to add openai.yaml to

These files go in the **codex/skills/** directory (not the canonical skills/ — they're Codex-specific metadata).

### Workflow skills (explicit invocation only)

**codex/skills/flow-next-plan/agents/openai.yaml:**
```yaml
interface:
  display_name: "Flow Plan"
  short_description: "Create structured build plans from feature requests"
  brand_color: "#3B82F6"
  default_prompt: "Plan out this feature: "
policy:
  allow_implicit_invocation: false
```

**codex/skills/flow-next-work/agents/openai.yaml:**
```yaml
interface:
  display_name: "Flow Work"
  short_description: "Execute planned tasks with worker subagents"
  brand_color: "#3B82F6"
  default_prompt: "Work on: "
policy:
  allow_implicit_invocation: false
```

**codex/skills/flow-next-interview/agents/openai.yaml:**
```yaml
interface:
  display_name: "Flow Interview"
  short_description: "Deep Q&A to refine specs and requirements"
  brand_color: "#3B82F6"
policy:
  allow_implicit_invocation: false
```

**codex/skills/flow-next-setup/agents/openai.yaml:**
```yaml
interface:
  display_name: "Flow Setup"
  short_description: "Initialize flow-next in current project"
  brand_color: "#3B82F6"
policy:
  allow_implicit_invocation: false
```

### Review skills (explicit invocation only)

**codex/skills/flow-next-impl-review/agents/openai.yaml:**
```yaml
interface:
  display_name: "Flow Implementation Review"
  short_description: "Carmack-level code review via RepoPrompt"
  brand_color: "#EF4444"
policy:
  allow_implicit_invocation: false
```

**codex/skills/flow-next-plan-review/agents/openai.yaml:**
```yaml
interface:
  display_name: "Flow Plan Review"
  short_description: "Carmack-level plan review via RepoPrompt"
  brand_color: "#EF4444"
policy:
  allow_implicit_invocation: false
```

**codex/skills/flow-next-epic-review/agents/openai.yaml:**
```yaml
interface:
  display_name: "Flow Epic Review"
  short_description: "Verify epic implementation matches spec"
  brand_color: "#EF4444"
policy:
  allow_implicit_invocation: false
```

### Utility skills (allow implicit invocation)

**codex/skills/flow-next/agents/openai.yaml:**
```yaml
interface:
  display_name: "Flow Tasks"
  short_description: "Manage .flow/ tasks and epics"
  brand_color: "#3B82F6"
policy:
  allow_implicit_invocation: true
```

**codex/skills/flow-next-prime/agents/openai.yaml:**
```yaml
interface:
  display_name: "Flow Prime"
  short_description: "Comprehensive codebase assessment for agent readiness"
  brand_color: "#F59E0B"
policy:
  allow_implicit_invocation: false
```

## Implementation notes
- These YAML files should be created by `sync-codex.sh` as part of the skill generation, OR created manually in this task and then maintained separately.
- Recommendation: add a `generate_openai_yaml()` function to sync-codex.sh that creates these during codex/ generation. This keeps everything in one build step.
- If adding to sync-codex.sh, update the script in this task.

## Acceptance criteria
- [ ] Key skills in codex/skills/ have agents/openai.yaml files
- [ ] All YAML files are valid
- [ ] Workflow/review skills have `allow_implicit_invocation: false`
- [ ] Utility skills have `allow_implicit_invocation: true`
- [ ] Brand colors are consistent (#3B82F6 for workflow, #EF4444 for review, #F59E0B for prime)
