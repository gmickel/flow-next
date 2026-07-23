## Conversation Evidence

> user (turn 1): "the command -> skill pattern came from when skills didn't get progressively loaded into context a while back."
> user (turn 1): "Since then codex/claude etc all merged commands and skills to be the same thing I think (research this)"
> user (turn 1): "perhaps the fix would be to drop the commands and just use skills that are user-invocable going forward?"
> user (turn 2): "users should use type '/flow-next:' to start the autocomplete?"
> user (turn 2): "capture a full spec for this, be sure that we get all surfaces, ie. where skills call other skills, help text that appears (next steps), documentation pass etc."
> user (turn 2): "The doc pass is not only the removal of the commands and lines that say 'n commands in flow-next' but also being sure to document how to invoke properly etc."
> user (turn 2): "you will drive and smoke test each TUI before deleting as part of the spec as you suggested, we don't want breakage."
> user (turn 2): "this is a simplification though and probably the right direction, especially given that the main invocation is usually through natural language anyhow."
> user (turn 3): "also test cursor"
> user (turn 3): "no, don't need compat, it's cleanly autocompleted and that was just a side effect"
> user (turn 3): "in general ahead of capturing test everything in all harnesses so we have a spec that is already fully proven"
> user (turn 4): "also need to see what really happens if we rename a skill to just 'plan', does it resolve to ...:plan everywhere and not try to complete with the built-in '/plan' of the harnesses"
> user (turn 4): "also droid is now logged in"
> user (turn 4): "also doesnt seem like argument hints work now on grok et al now anyhow, so maybe that bit isn't a blocker"
> user (turn 5): "test it, we need a variant that works for all, so far the folder thing seems the most promising"
> user (turn 6): "Cursor: already observed as '/flow-next-plan' you sure about that, i thought it just used folder name and that was an artifact from the real flow-next install? test it more"
> user (turn 7): "codex shouldn't be an issue surely as we can rewrite everything as we want"
> user (turn 7): "test the 2 remaining things so we have a fully featured spec"
> user (turn 7): "then we decide whether to go with flow-next:plan in claude and make a cursor folder and point the cursor meta file to there if droid and grok are the same as claude"

## Goal & Context
<!-- scope: business -->

**Status: deferred on 2026-07-23.** Retain the current command-to-skill architecture and revisit this spec when host APIs converge enough to provide clean, collision-safe selectors without host-specific installation contracts. The Grok discovery issue is addressed through documentation: type `/flow-next:` to autocomplete the current command surface. [user]

Flow-Next currently represents most public workflows twice: a full skill and a thin command shim that forwards the invocation into that skill. The split originated before skills were progressively disclosed and directly invocable. [paraphrase]

Current host documentation confirms that Claude Code and Factory have converged commands into skills, while Codex, Cursor, and Grok expose skill-native discovery or invocation surfaces. The shared schema has converged; the user-interface contract has not. [paraphrase]

Move toward one canonical, user-invocable skill per public workflow, with natural language remaining the normal entry point and an explicit selector remaining available for deterministic invocation. [user]

Do not treat “skill-native” as proof of one universal command spelling. Exact live probes on 2026-07-23 disproved that assumption: Claude derives the final segment from frontmatter inside a plugin namespace, Grok derives the visible non-colliding selector from the skill folder, Droid flattens the frontmatter name, Cursor derives its flat selector from the skill folder, and Codex can use generated native-plugin and standalone mirrors. [paraphrase]

The migration therefore has two ordered outcomes: first, resolve and prove host-specific discovery, naming, collision, nested-call, and upgrade behavior; second, delete command shims only when every required host has a usable, documented skill-only path. [paraphrase]

The current Grok documentation correction is independent and immediate: with the existing command architecture, users type `/flow-next:` to open Flow-Next command autocomplete. [user]

## Strategy Alignment

- One canonical skill per workflow strengthens Flow-Next's skill-driven architecture and removes a historical duplication layer. [paraphrase] [strategy:Cross-platform parity]
- Executed TUI evidence before deletion follows the project's evidence-over-existence posture. [user] [strategy:Cross-platform parity]
- Host-specific invocation documentation preserves first-class behavior across Claude Code, Codex, Factory Droid, Cursor, and Grok rather than forcing one host's syntax onto the others. [paraphrase] [strategy:Cross-platform parity]

## Strategy Conflicts

- The target simplification conflicts with a universal `/flow-next:<verb>` promise: current Cursor and Droid builds do not provide that namespace for skill-only fixtures. The implementation must resolve this conflict or retain the minimum proven host adapter; it must not delete shims and call the result parity. [paraphrase]

## Architecture & Data Models
<!-- scope: technical -->

### Verified current inventory

- The canonical plugin contains 23 command shims and 28 skills. [paraphrase]
- Twenty-two public workflows have both a command shim and a full skill; the uninstall workflow is command-only. [paraphrase]
- Twenty-two public workflow skills currently declare `user-invocable: false` to avoid duplicate Claude menu entries. [paraphrase]
- Six phrase-triggered or helper skills currently omit that field, so host defaults—not an explicit Flow-Next policy—determine whether they appear in menus. [paraphrase]
- Twenty of the 23 command shims carry argument hints, while none of the canonical skills currently carries one; those useful hints must be evaluated and migrated into the owning skills. [paraphrase]
- The Codex installer creates a separate prompt surface from command shims, while the Cursor manifest and installer explicitly register and count commands. [paraphrase]
- Existing tests and release documentation encode the 23-command architecture and its flattened command layout. [paraphrase]

### Target model

- One canonical skill owns each public workflow's instructions, metadata, arguments, examples, safety policy, and nested workflow calls. [paraphrase]
- Public workflows are explicitly user-invocable; helper and phrase-triggered workflows receive an explicit visibility and model-invocation policy rather than inheriting host defaults. [inferred]
- The command-only uninstall workflow becomes a safety-gated skill before the command tree can reach zero. [inferred]
- Canonical command shims reach zero only after all deletion gates pass. Host-generated adapters are permitted only when a host cannot expose a safe skill-only selector, and must be minimal, generated, tested, and documented as host adapters rather than compatibility aliases. [inferred]
- `/flow-next-plan` is not retained as a compatibility alias. [user]
- Fresh installs and upgraded installs converge to the same owned inventory without stale prompts, commands, or duplicate registrations. [inferred]

### Migration sequence

This sequence is intentionally dormant until a revisit trigger fires:

1. Revalidate the frozen 2026-07-23 probe matrix against then-current host versions and published standards. [paraphrase]
2. Inventory every public workflow, helper workflow, caller/callee edge, generated surface, installer, test, help string, next-step string, documentation page, count claim, and downstream maintainer surface. [user]
3. Choose a standards-conforming architecture that preserves clean selectors without adding new installation contracts for Claude, Droid, or Grok. [paraphrase]
4. Implement skill metadata, naming, safety, argument, and nested-call changes while command shims still coexist. [inferred]
5. Smoke every public workflow in every required TUI, including fresh-install and upgrade-install cases. [user]
6. Delete command sources and installer/manifest registrations only after every required row passes. [user]
7. Reinstall the production plugin on every host and repeat the final skill-only matrix. [paraphrase]

## API Contracts
<!-- scope: technical -->

### Proven host baseline

| Host and tested build | Exact `plan` skill result | Argument hint | Nested/helper result | Migration consequence |
|---|---|---|---|---|
| Claude Code 2.1.218 | `/plan` remains the built-in; plugin skill appears and executes as `/flow-next-plan-probe:plan` | Rendered after selection | Passed | Plugin-qualified `/flow-next:plan` is viable. [paraphrase] |
| Grok 0.2.111 | `/plan` remains the built-in; colliding plugin skill appears and executes as `/flow-next-plan-probe:plan` | Rendered after selection | Passed | `plan` is namespaced because it collides; every other verb still needs an exact probe. [paraphrase] |
| Codex 0.145.0 | `$` selector inserts `$flow-next-plan-probe:plan`; slash is not the skill contract | Not rendered | Original exact-name fixture loaded the main skill but missed its helper | Generated native-plugin and standalone mirrors require separate proof; see the completed follow-up below. [paraphrase] |
| Factory Droid 0.178.0 | Skill appears and executes as flat `/plan`; no plugin namespace | Not rendered | Direct helper was inconsistent; natural-language main/helper passed | Universal `/flow-next:plan` is disproven; flat-name collision policy required. [paraphrase] |
| Cursor CLI 2026.07.20 | Raw `/plan` collides with built-in Plan; normal keyboard selection entered built-in mode | Not rendered | Not safely reachable through the colliding selector | Hard blocker to deleting the plan command shim. [paraphrase] |
| Cursor editor 2026.07.20 | Built-in Plan is first; raw skill is a second `/plan`; no plugin-qualified form | Not rendered | Main skill loaded when explicitly clicked; helper probe did not | Hard blocker to a safe, universal explicit selector. [paraphrase] |

All versioned observations above come from an isolated plugin whose public skill directory and skill name were exactly `plan`, contained no commands, preserved quoted arguments, and emitted unique execution markers. [paraphrase]

### Maintainer manual verification

- Cursor editor manual verification on 2026-07-23 showed built-in **Plan** first, followed by the fake `plan` skill and its `plan-helper`; searching `/probe` found those two fake skills through their descriptions. The separately listed `flow-next-plan`, `flow-next-plan-review`, `flow-next-work`, and related names came from the normal Flow-Next installation, not aliases generated for the fake skill. No plugin-qualified escape hatch for the fake `plan` skill was observed. [paraphrase]
- Droid manual verification on 2026-07-23, with normal Flow-Next disabled only inside the fixture project, showed one `/plan` entry identified as the fake custom skill and no built-in Plan entry. This confirms flat `/skill-name` discovery in the tested Droid build. [paraphrase]

### Claude folder-versus-frontmatter probe

An isolated Claude Code 2.1.218 TUI probe on 2026-07-23 tested three command-free plugins with unique execution markers:

| Skill folder | Frontmatter `name` | Claude selector |
|---|---|---|
| `flow-next-plan` | `plan` | `/flow-next-folder-short:plan` |
| `flow-next-plan` | `flow-next-plan` | `/flow-next-folder-match:flow-next-plan` |
| `plan` | `flow-next-plan` | `/flow-next-folder-prefixed:flow-next-plan` |

Claude therefore derives the plugin-qualified selector's final segment from frontmatter `name`, not the skill folder. Applied to the production plugin, folder `flow-next-plan` plus `name: plan` would expose `/flow-next:plan`; it would not become `/flow-next:flow-next-plan`. Matching prefixed folder and frontmatter names would produce the double-prefixed form. [paraphrase]

This initially created a plausible single-tree compatibility seam: keep globally unique `flow-next-<verb>` folders for flat hosts while using bare `<verb>` frontmatter names for Claude's namespace. The published Agent Skills specification also requires `name` to match the parent directory, so this would have been a deliberate standards exception even if every host accepted it. [paraphrase]

### Grok and Droid folder-versus-frontmatter follow-up

The exact `flow-next-plan` folder plus `name: plan` candidate was installed in Grok 0.2.111 and Factory Droid 0.178.0 on 2026-07-23:

- `grok inspect` registered the candidate internally as skill `plan` owned by plugin `flow-next-folder-short`, but authenticated TUI autocomplete exposed `/flow-next-plan` with the fixture's unique description. Selecting it rendered `<probe-value>`; executing `/flow-next-plan grok-mismatch` returned `FOLDER_PREFIXED_NAME_SHORT_OK arguments=[grok-mismatch]`. Grok therefore uses the folder for the visible non-colliding selector even though inspection reports the frontmatter name. [paraphrase]
- Droid autocomplete exposed exactly `/plan` with the candidate's unique description. It did not expose `/flow-next-plan` or `/flow-next-folder-short:plan`. Executing `/plan droid-probe` activated the correct `plan` skill and returned `FOLDER_PREFIXED_NAME_SHORT_OK`, proving frontmatter `name` wins and the unique folder is discarded from the selector. Typing `/flow-next-folder-short:plan` produced no matching autocomplete entry; the subsequent plain prompt caused model-driven activation of `plan`, not qualified direct selection. [paraphrase]
- Droid's activation banner retained `droid-probe`, but the skill received an empty `$ARGUMENTS` value. Argument forwarding therefore remains a separate deletion blocker even though rendered hints are only informational. [paraphrase]

The mismatched folder/name candidate is rejected as a universal solution: it gives Claude `/flow-next:plan`, Grok and Cursor `/flow-next-plan`, but Droid `/plan` with broken argument forwarding. It also violates the published Agent Skills requirement that the frontmatter name match the parent directory. Grok and Droid therefore do **not** behave like Claude for this fixture, and a Cursor-only mirror cannot solve the matrix. [paraphrase]

The standards-conforming candidate was then installed in the same Droid and Grok builds:

- Droid autocomplete exposed `/flow-next-plan`, activated the exact `flow-next-plan` skill, returned `FOLDER_MATCH_OK`, and preserved `match-arg` through `$ARGUMENTS`. This proves the matched prefixed name is both collision-safe and argument-correct in Droid 0.178.0. [paraphrase]
- Grok was reauthenticated, then launched with an isolated temporary home whose discovered plugin surface contained only the matched candidate. Grok 0.2.111 autocomplete exposed flat `/flow-next-plan` with the unique `FOLDER_MATCH_PROBE` description; executing `/flow-next-plan grok-arg` returned `FOLDER_MATCH_OK arguments=[grok-arg]`. This proves the non-colliding matched candidate is flat, collision-safe, and argument-preserving in Grok. [paraphrase]
- Cursor CLI 2026.07.20 loaded only the temporary matched candidate through `--plugin-dir`. Autocomplete exposed `/flow-next-plan` with the unique `FOLDER_MATCH_PROBE` description; direct invocation returned `FOLDER_MATCH_OK arguments=[cursor-arg]`. This removes the ambiguity from the earlier editor screenshot, where `/flow-next-plan` could have come from the normal Flow-Next installation. [paraphrase]
- Cursor editor 2026.07.20 was then restarted against the maintainer's normal authenticated profile after the real Flow-Next plugin and the earlier probe were moved out of `~/.cursor/plugins/local`; the matched candidate was the only active local plugin. Autocomplete exposed one `/flow-next-plan` row with the unique `FOLDER_MATCH_PROBE` description, and `/flow-next-plan gui-arg` returned `FOLDER_MATCH_OK arguments=[gui-arg]`. This proves the Cursor editor result comes from the candidate itself, not the real Flow-Next install, and preserves arguments. Claude's isolated probe proves the same matched candidate appears as `/flow-next:flow-next-plan`. [user]

The matched `flow-next-<verb>` folder/name form is therefore the proven one-tree candidate: one standards-conforming tree; collision-safe, argument-preserving `/flow-next-plan` selectors in Cursor CLI, Cursor editor, Droid, and authenticated Grok; and redundant—but deterministic—`/flow-next:flow-next-plan` on Claude. Its remaining question is a product choice about Claude UX, not naming feasibility. [paraphrase]

### Codex generated-surface follow-up

Codex 0.145.0 was tested through both production-relevant generated shapes on 2026-07-23:

| Codex install shape | Generated skill folders and names | Selector | Direct arguments | Representative nested activation |
|---|---|---|---|---|
| Native plugin named `flow-next` | standards-conforming bare `plan` and `helper` | `$flow-next:plan` | `native-arg` preserved | `plan` loaded `helper`; helper received `parent-arguments=native-arg` |
| Global standalone skills | standards-conforming `flow-next-plan` and `flow-next-helper` | `$flow-next-plan` | `global-arg` preserved | `flow-next-plan` loaded `flow-next-helper`; helper received `parent-arguments=global-arg` |

The native-plugin probe returned `CODEX_NATIVE_PLAN_OK arguments=[native-arg] helper=[CODEX_NATIVE_HELPER_OK arguments=[parent-arguments=native-arg]]`. The global probe returned `CODEX_GLOBAL_PLAN_OK arguments=[global-arg] helper=[CODEX_GLOBAL_HELPER_OK arguments=[parent-arguments=global-arg]]`. [paraphrase]

Codex is therefore not an architecture blocker. `scripts/sync-codex.sh` can generate bare, plugin-namespaced skills for the native plugin and prefixed standalone skills for the global installer. Both generated shapes preserve arguments and representative nested calls. The final migration still must run the full public-workflow and caller graph, but the naming and nested-activation mechanism is proven. [user]

### Proven selector derivation

| Host | Plugin namespace in explicit selector | Visible selector source | Mismatched `flow-next-plan` folder + `name: plan` | Matched folder/name `flow-next-plan` |
|---|---|---|---|---|
| Claude Code | Yes | frontmatter `name` | `/flow-next:plan` | `/flow-next:flow-next-plan` |
| Grok | Collision-dependent, not a stable package contract | folder for the non-colliding candidate | `/flow-next-plan` | `/flow-next-plan` |
| Factory Droid | No | frontmatter `name` | `/plan`; argument forwarding failed | `/flow-next-plan`; arguments preserved |
| Cursor CLI/editor | No | folder | `/flow-next-plan` | `/flow-next-plan`; arguments preserved |
| Codex native plugin | Yes, with `$` | generated folder/name inside plugin | Not needed | Generated bare `plan` gives `$flow-next:plan` |
| Codex global installer | No, with `$` | generated standalone folder/name | Not needed | Generated `flow-next-plan` gives `$flow-next-plan` |

There is no single standards-conforming folder/name pair that yields both clean `/flow-next:plan` on Claude and collision-safe `/flow-next-plan` on every flat host. The production architecture must either accept Claude's redundant selector or generate separate standards-conforming trees. [paraphrase]

### External standards and host-tracker evidence

- The published Agent Skills specification defines a flat skill `name`, permits only lowercase letters, digits, and hyphens, and requires the name to match the parent directory. It does not define package/plugin namespaces, collision resolution, or a portable invocation spelling. Namespace proposals exist in agentskills/agentskills issues 109 and 312, but the published specification still has no namespace contract. [paraphrase]
- Claude Code officially merged custom commands into skills and gives plugin skills a `plugin-name:skill-name` namespace. A canonical skill named `plan` inside the `flow-next` plugin can therefore expose `/flow-next:plan` without colliding with standalone or built-in names. [paraphrase]
- Codex officially treats skills as the replacement for custom prompts/commands, uses `$` for explicit skill selection, and namespace-qualifies plugin-contributed skills. This supports `$flow-next:plan` for the native-plugin path but does not make the global one-line installer plugin-namespaced. [paraphrase]
- Cursor staff confirmed duplicate skill-name resolution as a bug on 2026-06-03. The documented workaround is to make skill folders globally unique because the `/` autocomplete key comes from the folder name. A follow-up in the same thread records that Cursor strips plugin prefixes, and the latest thread activity on 2026-07-10 still requests `plugin:skill` support. Cursor release notes through 3.11 do not announce a namespace or collision fix. [paraphrase]
- Factory's official skills documentation says custom slash commands have been merged into skills, direct invocation is flat `/skill-name`, and `name` defaults to the directory name. Its plugin documentation defines a plugin identifier but does not apply that identifier as a skill namespace. A 2026-07-23 sweep of every public Factory issue matching `skill` found standards support (#550), Claude-plugin compatibility discussion (#637), legacy command discovery (#638), slash-argument corruption (#1000), and discovery-root documentation (#1204), but no issue defining skill-name collision resolution or a plugin namespace. Release notes through 2026-07-21 likewise contain no namespace fix. This absence is supporting context, not proof of future behavior. [paraphrase]

Evidence:

- Agent Skills specification: https://agentskills.io/specification
- Agent Skills namespace discussions: https://github.com/agentskills/agentskills/issues/109 and https://github.com/agentskills/agentskills/issues/312
- Claude Code skills and plugins: https://code.claude.com/docs/en/slash-commands and https://code.claude.com/docs/en/plugins
- Codex skills: https://learn.chatgpt.com/docs/build-skills
- Cursor collision report: https://forum.cursor.com/t/workspace-skill-resolution-issue-with-identical-skill-names/162287
- Cursor changelog: https://cursor.com/changelog
- Factory skills, plugins, and release notes: https://docs.factory.ai/cli/configuration/skills, https://docs.factory.ai/cli/configuration/plugins, and https://docs.factory.ai/changelog/release-notes
- Factory issue-board sweep: https://github.com/Factory-AI/factory/issues/550, https://github.com/Factory-AI/factory/issues/637, https://github.com/Factory-AI/factory/issues/638, https://github.com/Factory-AI/factory/issues/1000, and https://github.com/Factory-AI/factory/issues/1204

### Required public invocation contract

- Natural-language invocation remains the primary portable contract for ordinary workflows on every first-class host. [user]
- Each host receives one tested deterministic explicit selector for every public workflow; documentation presents a per-host matrix rather than claiming universal slash syntax. [paraphrase]
- Claude Code's target is the plugin-qualified colon form. [paraphrase]
- Codex's target is the plugin-qualified `$` skill form. [paraphrase]
- Codex's native-plugin path and global one-line installer are separate contracts: the global installer must retain collision-safe Flow-Next-prefixed skill identifiers or move to native plugin installation, and must retire exact-owned stale prompts and old skill directories during upgrades. [paraphrase]
- Grok's mismatched and matched prefixed-folder candidates are both proven as flat `/flow-next-plan`, with argument forwarding and a rendered hint. The remaining public verbs still require the final matrix because exact bare `plan` collision handling differed from the non-colliding prefixed folder. [paraphrase]
- Droid's collision-safe policy is a matched prefixed folder and frontmatter name, yielding flat `/flow-next-<verb>` with argument forwarding. `/flow-next:<verb>` is not documented for Droid. [paraphrase]
- Cursor CLI and editor now expose the matched candidate deterministically as `/flow-next-plan`; every public verb, upgrade state, nested caller, and help surface must pass before their command shims can be deleted. [paraphrase]
- `/flow-next-plan` is not retained as an additional compatibility alias beside another working selector. On a flat, non-namespaced host, a generated skill named `flow-next-plan` may instead be that host's sole canonical deterministic selector when the live matrix proves it collision-safe; it must not coexist with a generated bare `/plan` for the same workflow. [paraphrase]
- Cursor's currently documented workaround makes a unique generated skill name a viable Cursor-specific candidate. Factory testing disproved the mismatched-folder variant as a universal implementation: Droid keys the selector from frontmatter `name`, not the unique folder. [paraphrase]
- The current Cursor manifest can redirect its `skills` component to a separate generated directory such as `./cursor-skills/`; a second marketplace manifest is not required. Codex already has generated surfaces. A clean-namespaced Claude architecture therefore requires additional standards-conforming prefixed surfaces for Cursor **and Droid**; Grok can consume the mismatched canonical folder for its visible selector but doing so would still make the canonical tree nonconforming. A standards-first design should not depend on that accident. [paraphrase]

### Argument and help contract

- Positional identifiers, options, blank invocation, and quoted multi-word values reach the owning workflow unchanged. [inferred]
- Each public skill contains its actionable description, supported arguments, examples, and safety notes; no useful metadata remains stranded in a deleted shim. [inferred]
- Rendered argument hints are best-effort host enhancement, not a deletion gate. Their observed behavior is documented per host. [user]
- Hosts without rendered hints must still expose a useful description and documentation examples. [inferred]
- Help output, setup output, next-step footers, recovery text, autonomous-loop instructions, generated prompts, and cross-skill handoffs emit the correct host-specific selector. [user]

### Cross-skill contract

- Every direct skill call is treated as a graph edge that must resolve after renaming or generation; filename replacement alone is insufficient. [user]
- The graph sweep includes orchestration flows, planning/review/work flows, QA driving, PR lifecycle flows, tracker lifecycle touchpoints, setup/uninstall, and helper skills. [paraphrase]
- Canonical caller syntax and every generated host representation must resolve a real installed callee. [inferred]
- Representative nested chains must execute on each host; a host that supports main-skill loading but not nested skill invocation is not migration-ready. [paraphrase]

## Edge Cases & Constraints
<!-- scope: technical -->

- Built-in collisions are a correctness issue, not cosmetic menu duplication: Cursor's `/plan` selected built-in Plan mode during the live CLI probe. [paraphrase]
- Grok's namespacing is collision-sensitive: an exact bare `plan` fixture was qualified, while a `flow-next-plan` folder with frontmatter `name: plan` was exposed flat as `/flow-next-plan`. Inspection and visible selector can report different identities. [paraphrase]
- `user-invocable: false` is not a portable visibility control: Cursor displayed a hidden helper in the live editor probe. [paraphrase]
- Skill names may be derived from plugin namespace, directory name, frontmatter name, or generated metadata differently by each host. No production mapping is accepted from documentation inference alone. [paraphrase]
- The Agent Skills standard currently leaves package identity, namespacing, and collision resolution to clients. Standards convergence therefore cannot be used as the deletion gate; only each host's executed selector behavior can. [paraphrase]
- Coexisting command and skill artifacts can change precedence. Every coexistence probe needs unique markers proving which artifact actually executed. [inferred]
- Deleted source files can survive in installed destinations. Upgrade tests must prove stale owned artifacts are retired, not merely absent from fresh installs. [inferred]
- Renaming canonical skill directories can leave both old and new Codex global skill directories installed, so cleanup covers stale command prompts and stale skill directories. [paraphrase]
- Cleanup never deletes or moves a same-named user-authored prompt or skill unless exact Flow-Next ownership is proven; recoverable retirement is preferred. [inferred]
- The uninstall skill must remain explicit-user-only wherever the host supports that safety control. [inferred]
- The community OpenCode port is out of repository scope; compatibility impact is documented and handed off rather than claimed as automatically migrated. [inferred]
- No version manifest changes are part of implementation; changes and documentation stage under Unreleased for a later batched release. [inferred]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** The implementation publishes an evidence-backed current/target inventory mapping every command shim to its owning skill, identifying command-only workflows, helper workflows, visibility policy, and generated host surfaces. [paraphrase]
- **R2:** The final architecture has one canonical implementation per public workflow, with explicit public-versus-helper invocation policy and no duplicated workflow instructions between a command and a skill. [paraphrase]
- **R3:** No command source, command manifest registration, or command installer path is deleted until the dated production-candidate matrix passes on Claude Code, Grok, Codex CLI/Desktop, Factory Droid, Cursor CLI, and Cursor editor. [user]
- **R4:** The matrix records host version, install mode, fresh-versus-upgrade state, skill folder, frontmatter name, discovery prefix, displayed name, description, hint behavior, selected artifact marker, blank invocation, positional and quoted arguments, natural-language invocation, nested invocation, collision behavior, and evidence location for every public workflow. It explicitly tests the `flow-next-<verb>` folder plus bare `<verb>` name candidate. [paraphrase]
- **R5:** High-risk names that overlap host built-ins—at minimum `plan`, review-related names, setup/configuration names, and help-like names—receive explicit collision tests rather than representative-only coverage. [inferred]
- **R6:** Cursor CLI and editor each have a deterministic, documented way to invoke the Flow-Next planning skill without accidentally entering built-in Plan mode before the planning command shim is removed. If no such path exists, deletion stops. [paraphrase]
- **R7:** Droid uses standards-conforming, matched `flow-next-<verb>` folders and names, or another equally collision-safe executed adapter, before any affected command shim is removed; the implementation does not falsely document `/flow-next:<verb>` or rely on a mismatched folder being retained. [paraphrase]
- **R8:** Grok is tested verb-by-verb for skill-only naming because its exact `plan` result and generic non-colliding result used different namespace behavior; the current command-era documentation continues to teach `/flow-next:` autocomplete. [paraphrase]
- **R9:** Codex retains plugin-qualified `$flow-next:<verb>` discovery and execution for the native plugin and collision-safe `$flow-next-<verb>` standalone identifiers for the global installer. The proven generators are extended across every public workflow and nested call, and upgrades retire exact-owned stale prompts and old skill directories safely before prompt shims are retired. [paraphrase]
- **R10:** `/flow-next-plan` is not shipped or documented as an additional compatibility alias. If a flat host requires that exact unique name, it is generated and documented as the sole host-native skill identifier for planning, with no duplicate bare `/plan`; the dated live matrix must justify the mapping. [paraphrase]
- **R11:** Rendered argument hints are not required for migration approval, but descriptions, argument examples, safety notes, and argument forwarding are complete and tested; documentation states the observed hint behavior per host. [user]
- **R12:** The command-only uninstall workflow becomes a tested, safety-gated skill preserving keep/remove choices, confirmation, cancellation, partial failure reporting, and user-data protection before its command is removed. [inferred]
- **R13:** A complete caller/callee sweep updates and tests orchestration chains, QA driving, review flows, tracker touchpoints, setup/uninstall flows, helper calls, generated host rewrites, permission declarations, and every prose handoff that names another workflow. [user]
- **R14:** All user-visible help, next-step footers, recovery messages, setup snippets, installer output, autonomous-loop instructions, examples, and generated prompts use the correct per-host selector after migration. [user]
- **R15:** Documentation across the repository, public documentation site, personal product page, changelogs, maintainer vault, and any discovered downstream narrative surface removes obsolete command counts and command-era architecture claims, replaces them with tested invocation guidance, and explains natural-language versus deterministic explicit invocation. [user]
- **R16:** Contributor and architecture documentation defines the skill-only addition process, public/helper classification, argument metadata, safety controls, host generation, collision review, nested-call review, and mandatory TUI smoke bar. [inferred]
- **R17:** Fresh-install and upgrade-install tests converge to the same skill-owned inventory on every host. Stale Flow-Next-owned prompts or command artifacts are retired recoverably, while same-named user-authored artifacts remain untouched. [inferred]
- **R18:** Command-era tests and fixtures are replaced with regression coverage for skill registration, name mapping, visibility, collision behavior, generated mirrors, stale-artifact cleanup, count drift, arguments, and nested calls. [inferred]
- **R19:** The final gate runs the canonical-to-Codex generation twice to prove idempotency, focused host/installer suites, the full repository suite, public-docs build, clean-install smokes, upgrade smokes, and the complete production TUI matrix after deletion. [inferred]
- **R20:** Any required-host failure, unavailable deterministic selector, ambiguous built-in collision, or failed nested invocation blocks deletion and produces a scoped follow-up decision; it is never waived through documentation wording. [user]
- **R21:** The OpenCode community-port impact is documented and handed off without claiming that its invocation surface changed automatically. [inferred]
- **R22:** Implementation and documentation changes land under Unreleased without changing version manifests; release numbering remains a later batched decision. [inferred]

## Boundaries
<!-- scope: business -->

- No redesign of workflow semantics, task/spec schemas, review policy, or `flowctl` behavior beyond plumbing required to register, generate, invoke, and retire the surfaces in scope. [paraphrase]
- No universal `/flow-next:<verb>` claim unless every named host actually proves it. [paraphrase]
- No additional `/flow-next-plan` compatibility alias. A host may use that spelling only as its sole generated, collision-safe skill identifier. [paraphrase]
- No command deletion before live TUI proof. [user]
- No universal argument-hint promise. [user]
- No mutation of user-authored prompts, skills, project data, specs, or tasks during stale-artifact cleanup. [inferred]
- No direct implementation changes to the out-of-repository OpenCode port. [inferred]
- No release or version bump in this spec. [inferred]
- The already-made Grok command-autocomplete documentation correction is not blocked on this migration. [paraphrase]

## Decision Context
<!-- scope: both — conditionally substructured -->

### Motivation
<!-- scope: business -->

One progressively disclosed skill per workflow is simpler to understand, maintain, and invoke through natural language than a skill plus a pass-through command created for an older host model. [paraphrase]

The simplification is only valuable if explicit invocation remains safe. The exact `plan` probe exposed a real collision that would route Cursor users into the wrong built-in workflow, so live host behavior—not schema convergence—sets the deletion boundary. [paraphrase]

### Implementation Tradeoffs
<!-- scope: technical -->

- **Chosen now:** defer the skill-only migration. Retain the command shims, their clean `/flow-next:<verb>` Claude/Droid/Grok contract, and the current generated Codex/Cursor surfaces. The internal simplification does not justify redundant Claude selectors, standards violations, or new host-specific installation contracts. [user]
- **Long-term direction:** one canonical skill implementation per workflow remains desirable if host APIs converge enough to expose clean, collision-safe selectors from the existing installation paths. Any resumed implementation remains fail-closed on collisions, arguments, nested calls, and upgrade behavior. [paraphrase]
- **Rejected:** assume commands and skills share one universal namespace because their schemas converged. The exact matrix disproved it. [paraphrase]
- **Rejected:** retain `/flow-next-plan` as a second compatibility alias merely because it appeared as a side effect. [user]
- **Rejected:** use `flow-next-<verb>` folders with bare `<verb>` frontmatter names as one universal tree. Claude yields `/flow-next:<verb>`, Grok and Cursor yield `/flow-next-<verb>`, but Droid discards the unique folder, exposes `/<verb>`, and failed argument forwarding; the mismatch also violates the published Agent Skills specification. [paraphrase]
- **Not chosen — one standards-conforming tree:** matching folder/name `flow-next-<verb>` produces collision-safe `/flow-next-<verb>` in Cursor, Droid, and Grok, but degrades the primary Claude surface to `/flow-next:flow-next-<verb>`. [paraphrase]
- **Unavailable under current distribution — standards-conforming host trees:** Cursor's existing manifest and Codex's generator can select generated skill trees, but Claude, Droid, and Grok currently consume the same physical Claude plugin tree. Factory's manifest documents convention-root `skills/`, not a configurable skills path; Grok exposes no separate Flow-Next rewrite/install phase. Clean host-specific trees would therefore require new Droid/Grok packaging or installation contracts, defeating the intended simplification. [paraphrase]
- **Rejected — standards exception plus Droid adapter:** unique `flow-next-<verb>` folders with bare frontmatter names produce good Claude/Grok/Cursor selectors, but violate the Agent Skills folder/name rule and still require a new Droid adapter. [paraphrase]
- **Proven, no longer a decision:** Codex can be rewritten independently. Native bare skills yield `$flow-next:<verb>` and global prefixed skills yield `$flow-next-<verb>`; direct arguments and representative nested activation passed on both surfaces. [user]
- **Qualified by host evidence:** Cursor currently strips plugin namespaces and officially recommends globally unique skill-folder names. Droid also requires a globally unique matching frontmatter name. A generated `flow-next-plan` skill is therefore the intentional flat-host identifier, not a compatibility alias. [paraphrase]
- **Rejected:** make argument-hint parity a blocker. Hints vary today; correct invocation, useful descriptions, and preserved arguments are the portable contract. [user]
- **Rejected:** delete command shims before Cursor/Droid/Codex nested behavior is solved. That would trade internal simplicity for user-visible breakage. [user]
- **Fallback if a host cannot expose a safe skill-only selector:** retain or generate the minimum host-specific adapter for only that host, document the exception, and keep the canonical workflow implementation in the skill. This is an explicit product decision, not silent compatibility scaffolding. [inferred]

### Revisit triggers

Resume architecture work only when at least one material capability changes:

- Claude, Droid, and Grok all support stable plugin-qualified skill selectors that avoid built-in and third-party collisions. [inferred]
- Droid and Grok support a manifest-selected skills root or another host-specific generated surface through the existing installation flow. [inferred]
- The Agent Skills specification publishes a package namespace and clients converge on it. [inferred]
- Claude Code removes or materially deprecates command shims, making retention more costly than the cross-host migration. [inferred]
- A new single-tree, standards-conforming candidate is demonstrated in all required TUIs with clean selectors and preserved arguments. [inferred]

On revisit, repeat the live matrix; do not treat the 2026-07-23 results as current host behavior. [paraphrase]

## Requirement coverage

| Requirement | Planned task |
|---|---|
| R1–R2 | Inventory and target architecture. [inferred] |
| R3–R5 | Production smoke harness and collision corpus. [inferred] |
| R6–R10 | Host-specific naming and invocation design. [inferred] |
| R11–R12 | Arguments, help metadata, and uninstall migration. [inferred] |
| R13–R14 | Caller graph and user-visible text migration. [inferred] |
| R15–R16 | Repository, public-site, vault, and contributor documentation. [inferred] |
| R17–R18 | Installer cleanup and regression suites. [inferred] |
| R19–R20 | Final deletion gate and fail-closed host matrix. [inferred] |
| R21–R22 | Community-port handoff and release discipline. [inferred] |
