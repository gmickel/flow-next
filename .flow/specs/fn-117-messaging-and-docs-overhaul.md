# fn-117 Messaging and docs overhaul: verification-first positioning across GitHub, flow-next.dev, guide, mickel.tech, vault

> Authored 2026-07-19 from a 6-audit research pass (flow-next.dev site audit, GitHub docs audit, competitive/positioning web research, mickel.tech + AI x SDLC audit, dynamic-usage recipe inventory, vault messaging-assets audit). Maintainer-priority: highest of the week - directly drives adoption and the maintainer's coaching work. NOT planned into tasks yet; maintainer critique of this plan comes first.

## Goal & Context

flow-next's product substance has outrun its story. The audits found one repeated pattern across every property: mechanism-rich, claim-poor. The sites explain HOW accuracy happens but never lead with THAT it happens; the enterprise/worldwide reality is invisible (zero adopter signals anywhere); and the single most damaging misreading from real coaching - "flow-next is a rigid conveyor: interview, spec, implement, done" - is confirmed by three independent field teams while the counter-doctrine (rails not prohibition, primitives are composable) exists fully articulated in the vault and NOWHERE in shipped copy. Meanwhile the competitive ground is wide open: every SDD competitor (spec-kit, BMAD, Kiro, Tessl) messages PLANNING; none messages PROOF. "Bias towards verification" is an unclaimed term with a ready-made intellectual lineage (Wei's verifier's law, Karpathy's generation-verification loop + autonomy slider, Vogels' "verification debt", Sonar's "verification gap" 96%/48% stat, Willison's "code proven to work").

This spec overhauls the messaging and docs across all five properties around one coherent architecture, with MORE documentation than usual including reasoning, and a full design makeover of flow-next.dev.

## The messaging architecture (foundation - every workstream consumes this)

### Claim hierarchy (in order; each claim is proof-backed, never adjective-backed)

1. **PRIMARY: Planned work ships with extremely high accuracy.** What gets planned gets implemented - with spec/plan adherence, evidence-backed completion, cross-model reviews at every handover, and drift prevention (re-anchoring, R-IDs frozen at handover, convergence ratchet). Far beyond default harness usage or ai-slop skill packs. Candidate hero shapes: "Agents generate. flow-next proves." / current tagline retained as secondary ("AI coding agents that ship like engineers - not slot machines").
2. **Bias towards verification** - COIN AND OWN THE TERM. The harness verifies its own work: receipts on every stage, evidence JSON required by `flowctl done`, QA forbidden from PASS-by-reading-source, land's evidence-over-narration, gate receipts keyed to commits. Cite the lineage (Wei / Karpathy / Vogels / Sonar / Willison) once, in the why-page, so the term inherits their authority. Back with the Sonar stat pair: 96% of developers do not fully trust AI code; only 48% verify it. flow-next operationalizes the missing half.
3. **The pipeline is a menu, not a rail** (the flexibility doctrine - the top coaching failure fixed). Opinionated rails for newcomers, fully composable primitives for experts: skip stages, reorder, prompt INTO any stage, one-shot chain the whole pipeline, parallelize across worktrees, route models per step - and both routes keep the SAME execution, evidence, and review contracts. Canonical field lines (vault, now shipped): "The default stages are rails, not a prohibition on exploration." / "The spec is the ratchet and handover object... not the permission to explore." / "Use the smallest sufficient workflow." Powered by the verified 40-recipe inventory (research annex below). CORRECTION (maintainer, 2026-07-19): task-level parallelism WITHIN one spec IS supported and marketable - multiple sessions/actors each run `/flow-next:work <task-id>` on disjoint tasks of the same spec (teams.md "Parallel work from one spec", atomic flock claims + assignee collision checks make it race-safe; plan-time file-overlap minimization is the design guidance). The research flag applies only to the narrower claim "one work invocation fans out parallel workers internally" - that does not exist. The remaining 4 aspirational patterns stay banned from marketing (tracker-driven agent spawning; pilot invoking capture/interview/merge; GitHub-# tracker-first; export-context in autonomous loops).
4. **One dial from interactive to fully autonomous** - same pipeline, same gates. Karpathy's autonomy slider made concrete: interactive skills -> per-skill mode:autonomous -> /loop pilot ticks -> backlog mode -> land -> Ralph ("Ralph with a seatbelt" vs the viral open-loop pattern). Gates fire identically at every rung.
5. **Multi-harness orchestration: your process outlives your agent.** Same workflow on Claude Code, Codex, Droid, Cursor; cross-model review by construction ("uncorrelated blind spots" - single-vendor tools cannot copy this); per-step model routing by parameter or by sentence ("parameters set the floor, prompting steers above it" - docs/orchestration.md L11-20 is already the doctrine; surface it at the front doors).
6. **Field-hardened worldwide, enterprise-grade ways of working.** Anonymized field evidence (a CAD software vendor, a proptech platform, an education-sector group, a construction-software portco...): 2-3h discovery interviews producing 8-11 structured specs; PM-side verdicts ("clear efficiency gain, edge cases caught they'd have missed"); same-day field-report-to-release arcs (2.9.0, 2.10.0); GHE/Windows/GitLab/Jira environments. Plus linkable OSS proof: Claire Novotny's substantive adoption quote (#111), awesome-list feature (#96), 662 stars, 3-OS CI. Enterprise vocabulary: audit trail, evidence, approval gates, human-in-the-loop, traceability - receipts ARE the audit-trail story (Gartner 2026 MQ scores audit-trail quality + approval-checkpoint granularity; 75% of leaders rank auditability top-3; DORA: AI amplifies the system around it - flow-next IS that system).

### Supporting frames

- Capability claims stated on our own terms - NO named-competitor comparison table (maintainer decision 2026-07-19). The construction-unique capabilities (receipts/evidence, cross-model review, live-app QA verdicts, 4-tracker projection, guarded autonomy ladder, multi-harness, self-improving memory, in-repo zero-dep uninstall) are claimed directly; the competitive intelligence (spec-kit has no review step; Kiro single-family + 5x spec-mode pricing; BMAD persona theater; conductors = parallelism without a quality spine) stays INTERNAL (vault Strategy & Positioning) to sharpen our copy, never published as a table.
- Story beats (vault Release Timeline, largely unshipped): "the eval that said no" (fn-83 - built, then killed by its own evidence); "the review gate audited itself" (2.10.0 fix converged through its own machinery in 2 ratcheted cycles); "field report to release, same day"; "same guarantees, instant plumbing" (fn-101/2.19.1); "the factory improves via the factory".
- The 2026 decision meme insertion: "solo -> OpenSpec, team -> Spec Kit, enterprise -> BMAD" has no verification-shaped slot; ours: "when the code has to ship - and you have to prove it did."

### Hard boundaries (binding on all workstreams)

- NO PSVI / Velocity Index vocabulary anywhere public (patent-pending, vault-private). "Measurement methodology / KPIs" framing only.
- NO client names; anonymize to sector descriptors. Verify anonymization survives cross-referencing (issue links that name companies stay as-is - already public - but prose never connects them to coaching stories).
- NO fabricated or unlinked testimonials; every quote links to a public source. RESOLVED SOURCE (maintainer): the original testimonials with correct handles + x.com status URLs exist in mickel.tech git history - commit d7a4024 ("feat(flow-next): add testimonials...") holds the full array (verified: Claire Novotny, @clairernovotny, "I've found it generating production-quality code. Far far better than any of the other tools I've tried so far." https://x.com/clairernovotny/status/1886200988044026046). The current live page MANGLED the links/usernames. Task: extract the full original array from d7a4024 (+ any later testimonial commits), verify each URL resolves, fix the links on mickel.tech, and reuse the verified set for README + flow-next.dev.
- NO marketing of the 5 flagged-aspirational recipes (task-parallel workers in one spec; tracker-driven agent spawning; pilot invoking capture/interview/merge; GitHub-# tracker-first; export-context in autonomous loops).
- Model names in docs prose become role labels (per orchestration.md's own volatility rule); concrete ids only in clearly-dated examples. (31 stale gpt-5.5/5.4 hits across docs today; fn-115's role map lands later and makes this durable.)
- Preserve verbatim the copy that already works: "Why this exists" README narrative, the seven pillars, why-flow-next.mdx, orchestration.md.

## Workstream A: GitHub repo front door

1. Custom social preview image (1280x640: tagline + pipeline; every share currently renders a default card).
2. Above-the-fold hero: animated terminal capture (asciinema to gif/svg, <5MB) of plan -> work -> impl-review SHIP -> make-pr ending on a real receipt; move the plan screenshot up. Hero proof-artifact, not adjectives.
3. New README section "The pipeline is a menu" (~15 lines): skip/one-shot/reorder/prompt-into/parallelize/route-models examples lifted from the recipe inventory; directly answers filed issues #28 and #91.
4. Testimonials rebuilt with linked, named quotes from TWO pools: (a) the recovered X testimonials from mickel.tech history d7a4024 (correct handles + status URLs - all public tweets, use verbatim with links, no outreach needed); (b) GitHub-native quotes - Novotny #111 (substantive), Patrick Michalina #5, possibilities #95, raydocs #4, Rytis-J #54, awesome-list feature #96 with badge.
5. Enterprise/adopters strip: "Field-hardened in enterprise environments" (GHE, Windows/cp1252 CAD, GitLab/Jira shops, issue-linked) + 3-line "For teams" teaser (six handover objects, Spec-as-PR, tracker projection) pointing at teams.md + flow-next.dev.
6. Proof badges: stars, CI (3-OS matrix is an enterprise signal), dynamic latest-release, awesome-mentioned; demote author/twitter badges to footer.
7. Community profile: enable Discussions (Q&A + Show-and-tell), disable empty Wiki, add CODE_OF_CONDUCT.md.
8. Quick-start de-friction: move the re-run-setup block below the happy path; Grok paragraph to platforms.md; collapse per-stage sections into details blocks.
9. Consistency sweep: 18-vs-22 command counts, 20-vs-21 agents, marketplace URL mismatch, model-id role labels; add a cognitive-aid PR body screenshot (R-ID coverage + Review plan) and CI-gate one-liner.
10. docs/ tree: teams.md count fix + backend examples to role labels; prime index row de-jargoned; orchestration.md untouched (it is the gold standard).

## Workstream B: flow-next.dev (content + full design makeover)

### B1 quick wins (mechanical)
Stale model refs (index.astro L329/345, skills/work.mdx L80/120 - fixes the terra contradiction, subagents pages, review pages); kill 1.13.0/1.14.0 badges; replace @ben testimonial; fix duplicated Acceptance Criteria heading in specs/schema.mdx; add pilot/land to when-to-use overnight section; de-dupe Ralph nav; skills index page (26-skill grid x pipeline stage).

### B2 new pages (both navbars + changelog per site rules)
1. **"Menu, not a rail"** - the flexibility doctrine page (claim 3 verbatim frames + the recipe categories); absorbs core-concepts "Tunable baseline"; linked from hero.
2. **Cookbook** - new nav group; ~40 recipes from the verified inventory, organized by the nine categories (skip/lighten, prompt-into, one-shot chains, evidence-first, model routing, parallelize, autonomy dial, integration tricks, team patterns); each recipe = scenario + exact invocation + why the gates still hold.
3. **Verification spine** - names the philosophy as one system (receipts, evidence JSON, QA live-app verdicts, gate receipts, evidence-over-narration, no-self-grading) + the lineage citations + Sonar stat; promoted to a landing pillar.
4. **Field notes / adopters** - anonymized enterprise evidence + linkable OSS proof; honest asymmetry included (PM relief vs senior-dev friction - credibility through honesty).
5. **FAQ / comparison** - the construction-win table + real coaching objections as FAQ seeds (spec-becomes-the-app sizing fear, perpetual-spec-library misconception, guardrails-vs-security-controls taxonomy, "do I need all of this? no - smallest sufficient workflow").
6. **First 30 minutes** - narrative first-spec tutorial with real output.
7. **Troubleshooting** (port from repo docs).
8. Full glossary page (from GLOSSARY.md).

### B3 skill-page content pass
Tips box + one worked example (real invocation + output excerpt) + relevant cookbook cross-links for the ~21 bare skill pages; template: when-to-use / how-it-works stays, plus "Tips" and "Dynamic usage" sections.

### B4 design makeover (frontend-design discipline at implementation)
Keep the strong foundation (Fraunces/IBM Plex identity, ink-teal + cream paper, custom rail) and close the custom-landing vs stock-docs gap: docs-body visual rhythm (cards, code-tabs, recipe cards, receipt-styled callouts - make "receipt" a visual motif), hero rework around the claim hierarchy with a proof-artifact (live receipt/verdict render), refreshed mockup content, testimonial capsules to case-study capsules, agent-legible docs (llms.txt, copy-paste command blocks - ~half of docs traffic is now agents), landing sections for verification spine + menu-not-rail + field notes. Decide single-theme commitment vs light theme deliberately. pnpm build is the gate; every nav change hits BOTH sources.

## Workstream C: mickel.tech flow-next page

1. Facts sweep of app/apps/flow-next/page.tsx: 2.19.1+, 29 skills, 4 review backends (add Cursor), 4 trackers (add GitLab/Jira), GPT-5.6 family, terra delegate default; JSON-LD version fix.
2. Hero + FAQ reframe around the claim hierarchy; cut changelog-style version tags; shorten pasted-release-note FAQ answers (JSON-LD quality).
3. Rebuild the Prime section to the 2.13.0 classification/verdict model.
4. Add flexibility/orchestration section (menu framing + model-per-step, pointing at flow-next.dev).
5. Fix lib/releases.ts (v0.38.1/wrong repo/wrong logo - update to current or link the docs-site changelog).
6. Credibility strip + cross-links to /sdlc and /expert (the page currently never connects to the consulting funnel).
7. Delete-or-wire flow-next-schematic.tsx (currently dead code). Site conventions: Next 16 App Router, copy in const arrays, EN/DE parity where applicable, biome gate.

## Workstream D: AI x SDLC Starter Kit

1. Expand guides/flow-next.md "Reproducible floor, tunable ceiling" into the full menu-not-rail treatment with concrete patterns (cross-link model-routing.md which already covers the routing half).
2. Regenerate resources/assets/code-factory-onboarding.html from source (narrative pinned at 2.4.0; coordinate with ~/work/code-factory-package).
3. Fix guides/plugins.md L165 retired-marketplace reference.
4. Add substantive flow-next treatments to team-enterprise.md (enterprise ways-of-working premise), code-review-tools.md (backend pluggability + receipts), factory-and-multi-agent.md (pilot/land/Ralph mapped onto its ladder).
5. Light multi-harness beef-up of flow-next.md install/platforms section.

## Workstream E: vault walk (after shipping)

Must: Messaging Library full rewrite (new claim hierarchy, flexibility pillar, refreshed numbers 29/22/2.19.1+/4+4, post-2.0 quote stock, field testimonials); Strategy & Positioning (tracks refresh, Oz/Warp + Wayfinder rows, flexibility in approach); Project Overview (version header 2.5.3 to current, tenets); Source Material Index re-stamp. Should: Vocabulary dedupe (doubled backlog-mode blocks) + 2.10-2.19 terms; Skills Catalog 28-to-29; Teams & Adoption mark flexibility doctrine as shipped; Signals closure entry; clear stale UNRELEASED markers (Tracker Sync fn-89, Lifecycle fn-93/86); Autonomy 2.17-2.19; Release Timeline arc extension.

## Workstream F: release-guidance update (private CLAUDE.md)

Update the maintainer's private ~/.claude/CLAUDE.md "Flow-Next downstream properties" section so future agents walk the downstream chain with NARRATIVE discipline, not just mechanics. Additions: (1) the claim hierarchy as the standing messaging frame every downstream update applies (which claim does this release strengthen? lead with that); (2) the story-beat habit (each release gets one beat in the docs-site changelog + vault Release Timeline, in the established voice - "the eval that said no" register); (3) the hard boundaries (no PSVI, no client names, linked-testimonials-only, role labels over volatile model ids); (4) the per-property tone map (GitHub = skeptical staff engineer; flow-next.dev = practitioner + agent-legible; guide = methodology coach; mickel.tech = client/employer; vault = internal candid); (5) pointer to the messaging architecture's canonical home (vault Messaging Library post-rewrite). Keep the existing mechanical chain (repo docs -> flow-next.dev -> microsite + guide -> vault) intact; this layers the WHY/HOW-IT-SOUNDS on top.

## Sequencing and review gates

1. **Phase 0 (this spec, done):** research + this plan. GATE: maintainer critique of the messaging architecture - the claim hierarchy and hero-line direction need ratification before any copy ships.
2. **Phase 1:** messaging architecture doc finalized + GitHub workstream A (fast, highest adoption leverage) + flow-next.dev B1 quick wins.
3. **Phase 2:** flow-next.dev B2 new pages + B4 design makeover (the big lift; frontend-design skill; screenshot/gif assets produced here feed A2).
4. **Phase 3:** B3 skill-page pass (mechanical once the template exists) + C mickel.tech + D guide.
5. **Phase 4:** E vault walk + Signals closure + memory.
Task breakdown at /flow-next:plan time follows these phases; A and B1 are parallel-safe; B4 blocks A2's hero asset only if the asset is shared.

## Boundaries / non-goals

- No product-behavior changes ride this spec (the fn-110..115 optimization series is separate and concurrent; coordinate CHANGELOG only).
- No paid placements, no launch-post writing (a launch thread can be a follow-up; this spec makes the properties worth linking).
- No new testimonial fabrication or consent-skipping; outreach for quote permission is a task, not an assumption.
- PSVI and client-name boundaries are absolute (see hard boundaries).
- German localization of new mickel.tech copy only where the page already has DE parity.

## Quick commands

```bash
cd ~/work/flow-next.dev && pnpm build                        # docs-site gate (MDX + mermaid render)
cd ~/work/mickel.tech && bun x biome check && bun run build  # microsite gate
grep -ri "PSVI\|Velocity Index" ~/work/flow-next.dev/src ~/work/mickel.tech/app/apps/flow-next README.md plugins/flow-next/docs/  # boundary gate: MUST be empty
```

## Acceptance Criteria

- **R1:** Every property front door leads with the accuracy claim: hero direction "Agents generate. flow-next proves." applied on README + flow-next.dev landing + mickel.tech hero; the claim hierarchy (6 claims, in order) is traceable on each property.
- **R2:** The flexibility doctrine ships everywhere: flow-next.dev "Menu, not a rail" page + Cookbook nav group with >= 35 verified recipes (9 categories, each recipe = scenario + exact invocation + why gates hold), README "The pipeline is a menu" section, guide menu-not-rail treatment. Zero marketing of the 4 banned aspirational patterns; task-parallelism marketed per Decision 7 (both live forms).
- **R3:** Verification spine shipped: named page on flow-next.dev + landing pillar; lineage (Wei/Karpathy/Vogels/Sonar/Willison) cited exactly once sitewide; Sonar 96/48 stat present with source link.
- **R4:** Enterprise proof shipped anonymized-bold: field-notes page + README adopters strip + mickel.tech credibility strip; the boundary grep (Quick commands) is empty; no client names connected to coaching stories anywhere.
- **R5:** Zero unlinked testimonials on any property: the d7a4024 X set recovered with URLs verified resolving + the GitHub pool (Novotny #111 lead); mickel.tech mangled links fixed.
- **R6:** GitHub front door complete: social-preview asset produced (1280x640; upload is a documented manual step), above-the-fold hero visual, proof badges (stars/CI/release/awesome), Discussions enabled + CODE_OF_CONDUCT + Wiki off, quick-start de-frictioned, consistency sweep done (command/agent counts, marketplace URL, model role labels).
- **R7:** flow-next.dev structural gate: all B1 quick wins fixed; every new page present in BOTH nav sources; llms.txt served; `pnpm build` green.
- **R8:** All ~21 bare skill pages gain Tips + Dynamic usage sections + one worked example each, cross-linked to cookbook recipes.
- **R9:** Design makeover landed: single theme, landing reworked around the claim hierarchy with a proof-artifact hero, docs-body rhythm components (cards/code-tabs/recipe cards/receipt-motif callouts) used by the new pages, refreshed mockups (no stale model ids or 1.x badges).
- **R10:** mickel.tech current: facts sweep (2.19.1+, 29 skills, 4 backends, 4 trackers, GPT-5.6 family), Prime section rebuilt to 2.13.0 model, lib/releases.ts fixed, /sdlc + /expert cross-links added, biome + build green.
- **R11:** Guide updated: flow-next.md menu-not-rail treatment, code-factory-onboarding.html regenerated from source, plugins.md marketplace ref fixed, substantive additions to team-enterprise.md + code-review-tools.md + factory-and-multi-agent.md.
- **R12:** Private CLAUDE.md "Flow-Next downstream properties" gains the narrative layer (claim-hierarchy frame, story-beat habit, boundaries, per-property tone map, canonical-home pointer) with mechanics intact.
- **R13:** Vault walk complete: Messaging Library rewritten around the new architecture; Strategy & Positioning, Project Overview, Source Material Index refreshed; stale UNRELEASED markers cleared; Signals closure entry appended.

## Early proof point

Task fn-117.1 validates the foundation: the d7a4024 testimonial set recovers with resolving URLs and the boundary discipline (PSVI/client-name greps) can be mechanically gated. If recovery fails, the proof strategy for R5 reverts to GitHub-pool-only before any property copy ships.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1  | claim hierarchy on every front door | fn-117.2, fn-117.4, fn-117.7 | - |
| R2  | flexibility doctrine everywhere | fn-117.2, fn-117.5, fn-117.8 | - |
| R3  | verification spine | fn-117.4, fn-117.6 | - |
| R4  | enterprise proof, anonymized-bold | fn-117.2, fn-117.6, fn-117.7 | - |
| R5  | linked testimonials only | fn-117.1, fn-117.2, fn-117.4, fn-117.7 | - |
| R6  | GitHub front door | fn-117.2 | - |
| R7  | flow-next.dev structural gate | fn-117.3, fn-117.4, fn-117.5, fn-117.6 | - |
| R8  | skill-page pass | fn-117.6 | - |
| R9  | design makeover | fn-117.4 | - |
| R10 | mickel.tech | fn-117.7 | - |
| R11 | guide | fn-117.8 | - |
| R12 | private release guidance | fn-117.1 | - |
| R13 | vault walk | fn-117.9 | - |

## Research annex (pointers)

The six full audit reports live in the session transcript (2026-07-19); load-bearing extracts are inlined above. Key artifacts to reuse at implementation time: the 40-recipe verified inventory with file:line citations (recipes agent), the linkable-testimonial list with URLs (github agent), the per-page flow-next.dev gap table (site agent), the vault quote harvest (vault agent), the competitor table + verifiability lineage citations (competitive agent), the mickel.tech staleness table (properties agent).

## Decisions (maintainer critique round 1, 2026-07-19 - all six open questions resolved)

1. Hero line: "Agents generate. flow-next proves." APPROVED as primary direction.
2. NO comparison table - capability claims on our own terms; competitive intel stays internal.
3. Single theme (dark-ink/cream identity), but beautify EVERYTHING - the makeover polishes the whole surface within the one theme.
4. Testimonials: no outreach needed - the tweets exist publicly; recover correct links/handles from mickel.tech git history (d7a4024) and fix the mangled live page.
5. Enterprise proof: anonymized, BOLD statements (no company names, no logo hunting).
6. Launch post/thread: separate follow-up, not this spec.
7. Task-level parallelism within one spec: reclassified SUPPORTED - TWO live forms: (a) multi-session/multi-actor (teams.md pattern, atomic claims), and (b) single-session prompted dispatch ("run .2 and .3 in parallel - disjoint files"): the host batches multiple worker Task calls in one message; the maintainer has used this routinely. History check (both plugin generations) confirms the skill prose never sanctioned form (b) - it works as prompted orchestration over the primitives. Cookbook markets both honestly (form (b) as "prompt into the step"); follow-up spec fn-118 makes form (b) an explicit sanctioned contract in the work skill (--parallel flag / prompt trigger, disjoint-Files guard, per-worker contracts unchanged, plan-sync once per batch).
8. Workstream F added: private CLAUDE.md release guidance gains the narrative layer.
