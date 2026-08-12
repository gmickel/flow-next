---
name: flow-next-visual
description: "Restate a spec, a task, a diff, or the current topic visually as a compact markdown digest. Use when asked to 'show me', 'explain this visually', 'restate that', 'digest the plan', 'walk me through the spec', 'walk me through the tasks', 'walk me through the diff', or when the output is too much text and a shape would land faster. Triggers on /flow-next:visual with an optional spec id, task id, git range, or free-form topic."
user-invocable: false
allowed-tools: Read, Bash, Grep, Glob
---

# Visual — human-first markdown digest

Restate one thing visually, in compact markdown, on one screen. The structure IS the output: the reader scans the shape, spots the wrong thing, and drills into only that file instead of reading everything to find out whether anything is wrong.

**Output contract:** compact markdown visuals rendered in chat — fenced text/diff/code blocks and tiny tables. Never images, never HTML files, never a written artifact. Everything here renders natively in the terminal, in chat, and on every forge: ```diff fences color for free, ```text is monospace everywhere, ```ts gets highlighting for free. There is no rendering machinery — the shapes below are the whole product.

**Read-only.** This skill reads state and responds. It never writes files, never mutates flow state, never commits, never runs a workflow. (If the user asks to save a digest, that is an ordinary Write with ordinary consent — not a mode of this skill.)

Rich HTML render lenses are a different register and stay where they are (`artifacts.html.enabled`); this skill never produces or replaces them.

## Preamble

flowctl is bundled with the plugin (not on PATH). Define once; subsequent blocks use `$FLOWCTL`:

```bash
FLOWCTL="${CODEX_HOME:-$HOME/.codex}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

## Input

Arguments: `$ARGUMENTS` — optional. One of:

- **Spec id** (`fn-189-human-first-visual-digest-skill`) → spec digest
- **Task id** (`fn-189-human-first-visual-digest-skill.1`) → task digest
- **Git range** (`main..HEAD`, `abc123..def456`, or the bare word `diff`) → diff digest
- **Nothing, or free-form text** → ad-hoc restate of the current topic (or of the text pointed at)

## Digest modes

### Spec digest (post-plan) — the primary mode

Read `$FLOWCTL show <spec-id> --json`, the spec markdown (`$FLOWCTL cat <spec-id>`), and every task file (`$FLOWCTL cat <task-id>`). Emit these six elements, in order, on one screen:

1. **Thesis** — 1-2 sentences: what ships and why.
2. **Task tree** — indented text tree in dependency order, parallel groups adjacent; one line per task: id, short title, the one thing it produces.
3. **Planned file-layout diff** — shallow tree with `+` (new) / `~` (changed) per file or dir, one-line responsibility, owning task id annotated, so the reviewer sees where the change lands and who owns it.
4. **Shape sketch** — the new/changed types, signatures, config keys, or command surfaces the tasks will create (shape 6), when the plan implies any. Skip when it implies none.
5. **R-ID coverage line** — one compact line or tiny table from the tasks' declared `satisfies` arrays, which live in each task file's frontmatter (`$FLOWCTL cat <task-id>`), not in `show --json`: `R1 -> t1 · R2 -> t2,t3 · R5 -> UNCOVERED`. Uncovered and undeclared jump out instead of needing cross-referencing.
6. **Boundaries** — IS / IS-NOT, one line each side.

### Spec digest (pre-plan)

No tasks yet: thesis, proposed shape, edge cases as one-liners, boundaries. No task tree, no coverage line — there is nothing to derive them from, and inventing them is the failure mode this mode exists to avoid.

### Task digest

One task: what it produces (shape sketch or file-layout diff), its position in the dependency tree, and its acceptance restated as 1-3 predicates.

### Diff digest

Input is a git range; on a branch with no range given, default to the merge base with the default branch (`git merge-base origin/HEAD HEAD` or the repo's default branch). Emit a file-layout diff with one-line responsibilities from `git diff --stat`, plus a call-tree or component-tree sketch of the load-bearing structural change. For orienting a reader before they read the real diff. Empty range: say so in one line and stop — never fabricate a sketch.

### Ad-hoc restate

No flow id: restate the current conversation topic, or the text the user points at, using the vocabulary. This is the "too much text — show me" mode and the natural-language entry point. Needs no flowctl and no git.

## Grounding (hallucination guardrails)

- Every path in a file tree comes from a task file, the spec, or `git diff --stat` — never invented.
- Every edge in a call tree traces to real code read in this session or to a real task dependency.
- Coverage lines come from the tasks' declared `satisfies` frontmatter (read with `$FLOWCTL cat <task-id>`) checked against the spec's R-IDs, not from re-narrated prose.
- No embellishment nodes "for clarity". When in doubt: **fewer nodes, more honest.**
- Nothing readable → say what was unreadable in one line, digest what is readable. A digest that quietly invents the missing half is worse than a short one.

## Degradation

- No tasks yet → pre-plan spec digest.
- No spec (or the id resolves to nothing) → diff digest if a range applies, else ad-hoc restate.
- No flowctl, no flow install, or not a git repo → ad-hoc restate, with a one-line notice of what was unavailable. The vocabulary needs neither.

## Shape vocabulary

Pick the **smallest** view that makes the key point clear. Place each visual **next to the short text it supports** — the visual supplements a one-or-two-sentence plain statement, never replaces it. Use **one or a few** shapes, never all of them. Skip preamble; prose stays brief and load-bearing.

**1. Pseudocode** — logic or an algorithm:

```text
on(message)
  if seen(message.id)
    drop
  enqueue(message)
  schedule flush
```

**2. Call tree** (indented text) — runtime control flow, orchestration, backend-shaped problems:

```text
startMission
  resolveFleet
    claimSeat
    openSession
  streamEvents
```

**3. Component tree** — UI structure, keeping ONLY the state hooks and module boundaries that matter:

```tsx
<MissionBoard> (apps/cockpit/src/routes/mission.tsx)
  useFleetEvents()
  <SeatGrid>
    <SeatCard> (packages/ui)
```

**4. Shallow file tree** — "where does this live" / scoping a refactor; one line of responsibility per entry:

```text
src/
|-- ingest/        # tails source feeds
|-- index/         # owns the search index
`-- query/         # answers searches
```

**5. Diff-fenced structural sketch** — the standout shape: diff syntax applied to a SHAPE (call tree, file tree, component tree, pseudocode), used when the point is what changes and the surrounding shape already exists. Match the diff shape to the topic.

File-layout change:

```diff
 src/
 |-- ingest/
+|   `-- dedupe.ts        # drops repeated events
 |-- index/
-`-- query.ts
+`-- query/
+    |-- parser.ts
+    `-- ranker.ts
```

Component-tree change:

```diff
 <MissionBoard>
   useFleetEvents()
   <SeatGrid>
+    <SeatFilter />
   <EventFeed>
+    <RetryBanner />
```

Call-tree change:

```diff
 startMission
   resolveFleet
     claimSeat
+    verifyAuth
     openSession
-  streamEvents
+  streamEvents
+    replayBacklog
```

State/control-flow change:

```diff
 on(message)
-  enqueue(message)
+  if seen(message.id)
+    drop
+  enqueue(message)
+  schedule flush
```

**6. Types and signatures** — the shape of code before any of it exists (the thing plan prose buries):

```ts
interface Seat {
  id: SeatId
  missionId: MissionId | null
}

assignSeat(seats: Seat[], policy: Policy) -> SeatId | null
```

**7. Compact table** — short enumerable facts only (R-ID coverage, per-task file ownership). Explanations live in the surrounding prose, never in cells.

**8. Mermaid — LAST resort.** Only when interaction or sequence genuinely needs it (renders graphically on forges, degrades to source in terminals); when warranted, sequence and state diagrams are the two forms that earn their keep. A text shape that carries the same point wins every time. When emitted, the existing make-pr mermaid rules apply (reserved words, quoting, caps) — see [../flow-next-make-pr/mermaid-rules.md](../flow-next-make-pr/mermaid-rules.md).

**Whole-block rule.** Show a complete block instead of a diff when most of it is new, when omitted context would hide ownership or order, or when the reader needs a copyable target shape.

**Trimming rule.** Within the chosen shape, keep ONLY the calls, files, props, states, and boundaries needed to answer the current question — everything else is left out, even when true.

## Forbidden

- Writing any file, mutating flow state, committing, or running another workflow.
- Emitting images or HTML — chat markdown only.
- Inventing a path, an edge, or a coverage claim that no read state supports.
- Emitting mermaid when a text shape would have carried the point.
- Using every shape because they exist — one or a few, chosen for the question.
- Padding with preamble, restating the spec in prose, or exceeding one screen.
