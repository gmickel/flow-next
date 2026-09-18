# capture: the resolved spec template decides which sections are written

## Conversation Evidence

> user (turn 1): "i think there are simple answers to both of these issues correct? ... simply adding a line of instructions to their CLAUDE.md/AGENTS.md to modify the behavior?"
> user (turn 2): "i often prompt it to not write a converstation evidence block when calling capture, surely the instruction file could do the same?"
> user (turn 3): "nothing should be testing against the spec contents that are 'optional' and could be adapted via the custom SPEC.md file a user uses, surely?"
> user (turn 4): "i do however not want any new config options of length etc, instruction file overrides are fine"
> user (turn 5): "spec A can contain the docs commit too from 447"
> user (turn 5): "why can't this just be more agentic, bundled defaults etc, but more like, see which sections are in the custom SPEC.md if exists bla bla / working state and all that sounds like machinery"
> user (turn 6): "isn't it only write the sections specified in the resolved template to be more future proof and if not already there, follow additional instructions in the resolved template for user-specific tweaks bla bla"
> user (turn 7): "go ahead, post both then capture the spec and then work on it and test it in isolation before doing a PR, all in host, no delegation, but paralleze as stateed in the work skill"

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 0% [user], 60% [paraphrase], 40% [inferred] -->

A team that customizes the spec scaffold with its own `SPEC.md` controls every section of a captured spec except the ones capture adds by itself. Capture resolves the template through the discovery cascade and then prepends `## Conversation Evidence` and appends `## Requirement coverage` outside it. Issue #443 reports the result: 15 to 20 lines of raw prompt text at the top of every spec, no supported way to drop them, and a hand deletion that a rewrite undoes.

No tool reads the evidence block. flowctl never parses the heading, plan, work and make-pr never read it, and refine preserves auxiliary sections without recreating a missing one. The block exists for one purpose, which is letting a reviewer look up the quote behind a `[user]` tag.

The project's own design principles settle the fix. "The artifact is the contract" makes the template file the authority on spec shape, and capture working around it is the defect. "Remember the bitter lesson" rules out compensating machinery, so the rule is one general sentence the host agent follows by reading the template, with no config key and no parsing branch.

Issue #447 asks whether a consumer repo can control artifact weight. The prose side is already open through project instruction files, and nothing in flow-next says so. This spec adds that statement to the prose contract. The PR walkthrough's compact/full threshold stays as it is.

Reporter of both issues: @flecamos.

## Architecture & Data Models
<!-- scope: technical -->

The change is skill prose and documentation. flowctl is untouched.

- **Capture's template step.** Today it walks the resolved template and then adds two sections of its own. After the change the resolved template is the only source of the section list. Capture writes the sections the template names, in the template's order, and follows any instructions the template carries. It adds no section the template leaves out.
- **Naming a section.** The bundled template names its seven canonical sections as headings and its auxiliary sections in its frontmatter list. Either form counts as the template naming a section. The host agent reads the file and judges; there is no parser and no fallback branch.
- **Triggers are unchanged.** The template decides whether a section may appear. The existing trigger decides whether it does: populated strategy content, a glossary mismatch, fog the conversation left open, a planned route for requirement coverage.
- **Evidence collection is unchanged.** Capture still extracts the user's verbatim turns first and still checks every `[user]` tag against them before the write. Only the question of whether those quotes land in the spec file moves to the template.

## Edge Cases & Constraints
<!-- scope: technical -->

- **Default behavior is byte-stable.** The bundled template names every section capture writes today, so a repo with no custom template sees no change.
- **A custom template copied from the bundled file** keeps the auxiliary list and sees no change.
- **A custom template written from scratch** has no auxiliary list. Its captured specs carry no auxiliary sections. This is a behavior change for those repos and the changelog says so.
- **Spec with no evidence block, corrected in chat.** Capture rechecks tags against the conversation it can still see and never recreates the section. After a context compaction the earlier evidence is gone, and capture retags from what remains.
- **Split proposals.** Per-spec evidence slices are written only when the template names the section.
- **A test pins the `Conversation Evidence` token** in capture's `[user]` source-tag row. Reworded skill text keeps the token.
- **Skill text ships to several hosts.** The Codex mirror is regenerated from the canonical files, never hand-edited.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** Capture writes only the sections the resolved spec template names, in the template's order, follows instructions the template carries, and adds no section the template leaves out; existing triggers still decide whether a permitted section appears. Errors: no custom template resolves to the bundled file and output matches today's; a template that names no auxiliary sections yields a spec with none, which is not an error. `[paraphrase]`
- **R2:** With a template that omits `Conversation Evidence`, capture still collects the verbatim user evidence and still runs the `[user]` findability check before the write, retagging what it cannot find. Chat corrections and split proposals on a spec without the block recheck against the conversation and never recreate the section. Errors: evidence lost to compaction means capture retags from what is visible; no error surface beyond that. `[paraphrase]`
- **R3:** Capture's evidence-extraction rule says how to record an `AskUserQuestion` selection: the chosen option label verbatim, marked as a selection, with no agent gloss. Errors: no error surface beyond R2. `[inferred]`
- **R4:** The bundled template's customization note and the spec-scaffold guide state that leaving a section out of the custom template removes it from captured specs, that no tool reads the evidence block, that a from-scratch template yields no auxiliary sections, and which features degrade when a parsed section is removed. Errors: no error surface. `[inferred]`
- **R5:** The prose contract states that project instruction files layer on top of it, that structural contracts of the emitting surface still win, and that it sets no length rule on purpose. Errors: no error surface. `[paraphrase]`
- **R6:** The Codex mirror is regenerated, the full test suite passes with the pinned `Conversation Evidence` token intact, and the changelog credits @flecamos and records the behavior change for from-scratch custom templates. Errors: a failing pinned-content test is fixed by keeping the pinned token, never by deleting the pin. `[inferred]`
- **R7:** Before the PR opens, an isolated capture run proves both directions: against the bundled template the spec carries `## Conversation Evidence`, and against a custom template that omits it the spec does not, with `[user]` tags still checked. Errors: a run that cannot be isolated from live `.flow/` state is not evidence. `[paraphrase]`

## Boundaries
<!-- scope: business -->

- No new config keys: no `capture.evidence`, no prose overlay path, no length or weight settings. Project instruction files are the override mechanism. `[paraphrase]`
- No change to the PR walkthrough's compact/full threshold, no make-pr flag for the render form, and no edit to the make-pr skill. `[paraphrase]`
- No flowctl change. `[inferred]`
- No change to how refine, plan, work or make-pr treat spec sections. `[inferred]`

## Decision Context
<!-- scope: both -->

**Why the template decides, and not a config key.** The reporter proposed a `capture.evidence` key with `keep`, `verify-then-drop` and `off`. A key adds a branch that every host mirror carries, and it duplicates a control the user already owns, which is the `SPEC.md` they customized. Omitting the section from that file gives `verify-then-drop` with the source-tag guarantee intact.

**Why a general rule, and not a special case for one section.** An earlier draft made only the evidence block conditional, with frontmatter parsing and a "bundled defaults" fallback for templates without frontmatter. That is machinery around one section. The general rule covers the evidence block and requirement coverage and any section capture gains later, in one sentence the host agent applies by reading the file.

**Requirement coverage is safe under the rule.** Plan authors that section itself, and flowctl reads it only when the spec has one, so capture's placeholder is not load-bearing.

**Why the threshold stays closed (#447).** The make-pr agent owns judgment and composes a validated JSON artifact; flowctl renders it deterministically, and the PR body, the HTML lens and downstream tools all project from that one artifact. A per-repo form switch would bring back the discretionary path the introducing spec ruled out. The full form also renders mostly collapsed on GitHub, which softens the word count the reporter measured.

**Rejected:** an interim-only answer of "add a line to your instruction file". It works, and the reply to #443 offers it until this ships, but it works by going against the skill text, which makes it a workaround.
