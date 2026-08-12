# Human-first visual digest skill + structural sketches in make-pr

## Goal & Context

flow-next has two visual registers and nothing between them. At one extreme: raw spec/task markdown - after `/flow-next:plan` a reviewer faces the spec plus N task files (500+ lines for a 7-task spec) and must reconstruct the structure in their head by serial reading. At the other: the opt-in HTML render lenses (`artifacts.html.enabled`) - full instrument-panel documents with mastheads, dials, and DAG hover wires, heavyweight to generate and consume. The middle register is missing: a fast, compact, markdown-only visual restatement that renders natively in the terminal, in chat, and on every forge, with zero machinery.

This spec adds that register in two moves:

1. A new skill `/flow-next:visual` - point it at a spec, a task, a diff range, or the current conversation topic and it restates the thing visually in compact markdown using a small fixed shape vocabulary (call trees, shallow file trees, diff-fenced structural sketches, type/signature sketches, pseudocode, tiny tables; mermaid only as a last resort). Primary use case: the post-plan review moment - one screen where the structure IS the output, so the human scans the shape, spots the wrong thing, and drills into only that task file instead of reading everything to discover whether anything is wrong.
2. make-pr's `## Structural changes` section learns the diff-fenced structural sketch as an alternate emission shape alongside mermaid - carrying the same signal with zero silent-rendering-failure risk when mermaid caps would collapse diagrams or triggers fire marginally.

The insight the whole spec rests on: everything renders through plain fenced code blocks that every host already handles natively. ```diff fences get red/green coloring for free in the Claude Code terminal, GitHub, Codex, and Cursor; ```text call trees are monospace everywhere; ```ts signatures get syntax highlighting for free. The richest-looking output is the cheapest one. There is no rendering machinery to build - the entire implementable substance is prose: the shape vocabulary, the selection rule, and the discipline lines.

Target persona: the maintainer (or any team lead) at a review gate - post-plan approval, mid-conversation "too much text, show me", pre-review diff orientation. Also the on-ramp for people who find agent prose walls unreadable.

## Shape vocabulary (the output contract)

The skill's core is this fixed vocabulary. Each shape has one job; the skill picks the SMALLEST view that makes the key point clear, places each visual next to the short text it supports, and uses one or a few shapes - never all. Skip preamble; prose stays brief and load-bearing (the visual supplements, never replaces, a one-or-two-sentence plain statement).

**1. Pseudocode** - logic or an algorithm:

```text
on(save)
  if content is unchanged
    return cached result
  write new content
  return fresh result
```

**2. Call tree** (indented text) - runtime control flow, orchestration, backend-shaped problems:

```text
submitForm
  createSession
    persistPrompt
    launchAgent
  navigateToSession
```

**3. Component tree** - UI structure, keeping ONLY the state hooks and module boundaries that matter:

```tsx
<SessionPage> (apps/example/src/routes/session.tsx)
  useSessionEvents()
  <SessionToolbar>
    <RunSkillButton> (packages/ui)
```

**4. Shallow file tree** - "where does this live" / scoping a refactor; one line of responsibility per entry:

```text
src/
|-- commands/       # parses user actions
|-- sessions/       # owns session state
`-- transport/      # sends API requests
```

**5. Diff-fenced structural sketch** - the standout shape: diff syntax applied to a SHAPE (call tree, file tree, component tree, pseudocode), used when the point is what changes and the surrounding shape already exists. Match the diff shape to the topic.

For a file-layout change:

```diff
 src/
 |-- commands/
+|   `-- digest.ts        # expands the slash command
 |-- sessions/
-`-- transport.ts
+`-- transport/
+    |-- client.ts
+    `-- stream.ts
```

For a call-tree change:

```diff
 submitForm
   createSession
     persistPrompt
+    expandSkillMention
     launchAgent
-  navigateToSession
+  navigateToSession
+    subscribeToEvents
```

For a state/control-flow change:

```diff
 on(save)
-  write content
+  if content is unchanged
+    return cached result
+  write new content
+  invalidate cache
```

**6. Types and signatures** - the shape of code before any of it exists (the thing plan prose buries):

```ts
interface Item {
  id: ItemId
  parentId: ItemId | null
}

resolveTarget(items: Item[], cursor: Cursor) -> ItemId | null
```

**7. Compact table** - short enumerable facts only (R-ID coverage, per-task file ownership); explanations live in surrounding prose, never in cells.

**8. Mermaid** - LAST resort, only when interaction/sequence genuinely needs it (renders graphically on forges, degrades to source in terminals). When emitted, the existing make-pr mermaid rules apply (reserved words, quoting, caps).

Whole-block rule: show a complete block (not a diff) when most of it is new, when omitted context would hide ownership or order, or when the reader needs a copyable target shape.

## Digest modes (what the skill renders per target)

**Spec digest (post-plan, the primary mode).** Input: `$FLOWCTL show <spec-id> --json`, the spec markdown, and every task file. Output, in order, on one screen:

1. **Thesis** - 1-2 sentences: what ships and why.
2. **Task tree** - indented text tree showing dependency order and parallel groups, one line per task (id, short title, the one thing it produces).
3. **Planned file-layout diff** - shallow tree, `+`/`~` per file or dir, one-line responsibility, owning task id annotated - so the reviewer sees WHERE the change lands and which task owns it.
4. **Shape sketch** - new/changed types, signatures, config keys, or command surfaces the tasks will create (shape 6), when the plan implies any.
5. **R-ID coverage line** - compact table or one-liner: `R1 -> t1 · R2 -> t2,t3 · R5 -> UNCOVERED`; uncovered/undeclared jump out instead of requiring cross-referencing.
6. **Boundaries** - IS / IS-NOT pair, one line each side.

**Spec digest (pre-plan).** Same minus task tree/coverage: thesis, proposed shape, edge-case cards as one-liners, boundaries.

**Task digest.** One task: what it produces (shape sketch or file diff), its position in the dep tree, acceptance restated as 1-3 predicates.

**Diff digest.** Input: a git range (defaults to merge-base with the default branch when invoked on a branch). Output: file-layout diff with one-line responsibilities, plus a call-tree or component-tree sketch of the load-bearing structural change. For orienting a review before reading the actual diff.

**Ad-hoc restate.** No flow id given: restate the current conversation topic (or the text the user points at) using the vocabulary. This is the "too much text - show me" mode and the natural-language entry point.

## Edge Cases & Constraints

- **Grounding (hallucination guardrails).** Every path in a file tree comes from the task files, the spec, or `git diff --stat` - never invented. Every edge in a call tree traces to real code the skill read or a real task dependency. No "for clarity" embellishment nodes. When in doubt: fewer nodes, more honest. Spec-digest coverage lines come from `show --json` task `satisfies` arrays, not re-narrated prose.
- **Cross-platform.** Output is pure markdown - works identically on all five hosts with zero sync-codex transforms beyond the standard mirror copy. The skill references no Claude-builtin tools (no subagents, no AskUserQuestion needed - single-context, read-only-plus-respond). Bash blocks use the standard `$FLOWCTL` preamble (`${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl` with the `.flow/bin/flowctl` fallback).
- **Read-only.** The skill never writes files, never mutates flow state, never commits. Output goes to chat. (A user may ask to save the digest; ordinary Write consent flow covers that - no special casing.)
- **Missing state degrades gracefully.** No tasks yet -> pre-plan digest. No spec -> diff or ad-hoc mode. Not a git repo / no flow install -> ad-hoc mode still works (the vocabulary needs no flowctl).
- **Token cost.** The skill is small (target: SKILL.md + one workflow file, same order of magnitude as the vocabulary above). Closer offers in capture/plan/interview are ONE line each - a suggested next command, never auto-run.
- **Command-surface pin.** `test_command_shim_flatten.EXPECTED_COMMANDS` pins the exact shim set - the new `visual` shim must be added there deliberately or the suite fails.
- **make-pr guardrails carry over.** Diff-fenced sketches in `## Structural changes` obey the same hallucination rules as mermaid (nodes/paths from `diff_summary.files[]` / `cross_module_changes[]` only) and the same prose-precedes-visual rule (R13). The pr_cognitive_aid v1 schema, its validator, and its deterministic renderer are untouched.

## Acceptance Criteria

- R1: Canonical skill exists at `plugins/flow-next/skills/flow-next-visual/SKILL.md` with frontmatter `name`, `description`, `allowed-tools`; the description is trigger-rich so natural language invokes it without the slash command ("show me", "explain this visually", "restate that", "digest the plan", "too much text", "walk me through the spec/tasks/diff") and names the four targets (spec, task, diff, current topic); it states the output is compact markdown visuals rendered in chat (not images or HTML files). Command shim at `plugins/flow-next/commands/visual.md` with bare colon-free `name: visual` + non-empty description. Errors: no error surface beyond graceful degradation (missing state -> nearest viable mode, stated in prose).
- R2: The skill embeds the full shape vocabulary (all 8 shapes with one concrete example each), the smallest-view selection rule, the visual-next-to-its-text rule, the one-or-a-few-never-all rule, the whole-block rule, and mermaid-as-last-resort. Errors: none (prose contract).
- R3: All five digest modes render as specified (spec post-plan with the 6 ordered elements, spec pre-plan, task, diff, ad-hoc), grounded per the guardrails (paths/edges/coverage from real state, never invented). Errors: unreadable/absent flowctl -> ad-hoc mode with one-line notice; empty diff range -> say so, no fabricated sketch.
- R4: capture, plan, and interview closers each gain exactly one suggested-next-step line offering the digest at their read-back moment (capture: after spec write-back; plan: after task creation; interview: after final write); phrased as an offer, never auto-run. Errors: none (prose contract).
- R5: make-pr `## Structural changes` may emit a diff-fenced structural sketch (file-tree or call-tree shape) as an alternate/complement to mermaid when the collapse-to-one rule would fire or a trigger fires marginally; documented in `mermaid-rules.md` (or a sibling section it links); same guardrails and prose-precedes-visual rule; pr_cognitive_aid schema/validator/renderer untouched. Errors: none beyond existing Phase 3 rules.
- R6: sync-codex integration: `generate_openai_yaml` call added (utility amber `#F59E0B`, explicit `allow_implicit_invocation: false`), skill name in `REQUIRED_OPENAI_YAML_SKILLS`, `./scripts/sync-codex.sh` run twice with zero errors and an idempotent second run; mirror committed. Errors: sync validation failure blocks the change.
- R7: Listing surfaces updated in the same change: root `README.md` commands table, `CLAUDE.md` flow-next command surfaces, guide routing table (`flow-next-guide/SKILL.md` gains the starting state "output too dense / need to review a plan or diff at a glance"), `EXPECTED_COMMANDS` in `test_command_shim_flatten.py`, CHANGELOG entry under `## Unreleased` (user-outcome-first). Errors: none.
- R8: Conduct checklist at `agent_docs/conduct/visual.md` (4-6 falsifiable transcript-checkable behaviors, e.g. "digest fits one screen", "every path in the file tree exists in a task file or diff", "no mermaid emitted when a text shape sufficed", "prose sentence precedes every visual") plus an index row in `conduct/README.md`; never referenced from the skill's own files. Errors: none.
- R9: Prose-contract test (new focused file, e.g. `test_visual_skill.py`): pins the command shim bare name, the skill description's natural-language trigger phrases, presence of all 8 vocabulary shapes in the skill (content), the three closer offer lines in capture/plan/interview (content + reachability), and the make-pr sketch clause (content). Location pinned only where load-bearing per the prose-contract heuristic. Errors: none.

## Boundaries

- NOT a replacement for the HTML render lenses - they stay as the opt-in rich surface for business review; this spec does not touch `references/html-artifacts.md` or either lens.
- NO changes to the pr_cognitive_aid v1 schema, validator, or deterministic renderer - the make-pr change lives entirely on the host-judgment side where mermaid already lives.
- NO new flowctl plumbing - all reads exist (`show --json`, task files, git). Pure skill per the architecture split rule.
- NO auto-run anywhere: closers offer, the user invokes.
- NO writes from the skill itself; chat output only.
- NO version bump in implementation commits (batched release policy); docs-site (flow-next.dev) walk happens at release, not here.
- Naming: `visual` is the settled command name; not up for revision during implementation.

## Decision Context

Markdown over HTML was the founding call: the existing artifact mode is "pretty heavy" (user's words) and the review gap needs "max speed and efficiency while being maximally useful to a human, markdown seems good for that". The fenced-block insight closed the debate - diff/text/ts fences render richly on every host with zero machinery, so the middle register costs nothing to render and nothing to port. Invoke-plus-offer came from the same review: "it can be invoked and proposed as one of the next steps after capture/plan/interview, right now we have a gap there". Natural-language invocation is an explicit requirement: "the description will allow it to be invoked through natural language". The post-plan pain drove the primary mode: "the other gap is having to look through the spec and 7 tasks after plan". make-pr keeps its existing mermaid pipeline because it demonstrably works; the sketch shapes join as a complement precisely where mermaid is weakest (silent rendering failure, cap-forced collapse) - "we're well covered on the make-pr side of things, although there may be some interesting techniques we could also apply there". Rejected: a deterministic renderer in flowctl (this is per-item judgment, the definition of skill work); auto-running the digest after plan (token cost imposed on every run); HTML output modes in the skill (duplicates the lens system).

## Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_visual_skill test_command_shim_flatten -q
./scripts/sync-codex.sh && ./scripts/sync-codex.sh   # twice - idempotency
```
