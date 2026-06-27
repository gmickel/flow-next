---
satisfies: [R9]
---

## Description

The **full documentation sweep across all four surfaces** (this changes the pipeline) + Codex mirror regen + version bump. Per CLAUDE.md doc-update discipline + `agent_docs/releasing.md`. **The QA framing everywhere: augments — never replaces — staging/CI/manual QA; reduces human work agentically; surfaces problems to humans.**

**Size:** L  *(broad sweep: repo docs + Codex mirror + version + 3 external repos + site build + diagram regen)*
**Files:** repo docs + `CHANGELOG.md` (`## Unreleased`) + flow-next.dev + AI×SDLC guide + GF microsite — **version bump DEFERRED to the batched release (no `bump.sh` here)**

## Approach

- **Codex mirror:** edits to pilot `workflow.md`/`SKILL.md` + qa `workflow.md` ⇒ run `scripts/sync-codex.sh`, **smoke the mirror** (memory: mirror-regen exposes latent canonical gaps; don't wait for review).
- **Repo (`/Users/gordon/work/flow-next`):** `flow-next-qa/SKILL.md` (L3 + "fills that gap" para → optional-stage + augments-not-replaces); pilot `SKILL.md`/`workflow.md` (stage set already edited in .2 — confirm docs match); `docs/ralph.md` (the pipeline para ~L200 + the qa-receipt note ~L427 + quality-gates header — add the optional QA stage between work and make-pr); `docs/README.md` (L37 QA row + L136/L145 diagram/callout); `README.md` (same diagram/callout); `docs/flowctl.md` (`pipeline.qa` config row — confirm from .2); **`CHANGELOG.md`** top entry.
- **flow-next.dev (`~/work/flow-next.dev`):** `src/content/docs/skills/qa.mdx` (L44/L48 → optional pipeline stage; **sharpen augments-not-replaces / surfaces-to-humans**); `skills/pilot.mdx` (L24/L25 classify+dispatch, L36 verdict stages → add `qa`; L109 "stops at draft PR" note); `autonomous/overview.mdx` (~L121 pipeline → add optional QA stage); `releases/changelog.mdx` (new entry under the unreleased/next section); **leave `FLOW_NEXT_VERSION` / `package.json` untouched — version bump deferred**. QA already in BOTH navbars — **no nav surgery**. Gate: `pnpm build`.
- **AI×SDLC guide (`~/work/AI-x-SDLC-Starter-Kit`):** `guides/flow-next.md` ("## The pipeline" ~L47 → add optional QA stage to the idea→merged-PR spine); `guides/phased-rollout.md` (~L263/L328 + L86 QA-tracks note); `guides/ai-readiness.md` (~L263 dogfood-QA); `guides/production-grade.md` (test/eval section); `guides/metrics.md` (~L303 coverage-delta). Apply augments-not-replaces framing. (Page list non-exhaustive — scan for other touched framing.)
- **GF microsite (`~/work/code-factory-package`):** `spec/04-pipeline.md` (add optional QA stage between BUILD and REVIEW; update `spec/diagrams/pipeline.mmd` + regenerate `pipeline.svg`); `spec/06-rid-coverage.md:20`, `spec/07-install-access.md:89`, `spec/08-autonomy.md:15` (→ "optional QA pipeline stage" framing).
- **Version bump — DEFERRED (batched release, per CLAUDE.md):** do NOT run `scripts/bump.sh` or touch manifests / badges / `FLOW_NEXT_VERSION`. Stage the change as a `## Unreleased` CHANGELOG entry (repo + docs-site); the bump across all surfaces happens later at the batched release. (`sync-codex.sh` is still run above — that is not a version bump.)

## Investigation targets
**Required:**
- `agent_docs/releasing.md`, `scripts/bump.sh`, `scripts/sync-codex.sh`
- `plugins/flow-next/docs/ralph.md` (~L200,L427), `docs/README.md` (L37,L136), `README.md`, `CHANGELOG.md`
- `~/work/flow-next.dev/src/content/docs/skills/qa.mdx`, `skills/pilot.mdx`, `autonomous/overview.mdx`, `src/lib/site.ts`
- `~/work/AI-x-SDLC-Starter-Kit/guides/{flow-next,phased-rollout,ai-readiness,production-grade,metrics}.md`
- `~/work/code-factory-package/spec/{04-pipeline,06-rid-coverage,07-install-access,08-autonomy}.md` + `spec/diagrams/pipeline.mmd`

## Acceptance
- [ ] `scripts/sync-codex.sh` clean + mirror smoked after pilot/qa edits.
- [ ] Repo docs updated (qa SKILL, pilot docs, `docs/ralph.md`, `docs/README.md`, `README.md`, `docs/flowctl.md` `pipeline.qa` row) + `CHANGELOG.md` top entry.
- [ ] flow-next.dev: qa.mdx (augments-not-replaces / surfaces-to-humans framing), pilot.mdx (qa stage), autonomous/overview.mdx (pipeline), changelog (unreleased section); `FLOW_NEXT_VERSION` / `package.json` left as-is (bump deferred); `pnpm build` green; no nav surgery.
- [ ] AI×SDLC guide: flow-next.md pipeline section + the QA pages (phased-rollout/ai-readiness/production-grade/metrics) carry the optional-stage + augments-not-replaces framing.
- [ ] GF microsite: `04-pipeline.md` + diagram regenerated; 06/07/08 framing updated.
- [ ] **NO version bump in this task** — staged under `## Unreleased` (repo + docs-site); `scripts/bump.sh` + manifests deferred to the batched release (per CLAUDE.md).

## Done summary
Documentation sweep for the optional QA pipeline stage (fn-72) across all four surfaces + Codex mirror regen. Repo: qa SKILL.md (optional-stage + augments-never-replaces framing), docs/ralph.md / docs/README.md / README.md (optional `qa` stage threaded into the pilot pipeline `plan → … → qa → make-pr`), CHANGELOG.md `## Unreleased` fn-72 entry; Codex mirror regenerated (sync-codex.sh, validation clean) for the .1/.2 canonical edits. flow-next.dev: qa.mdx (sharpened augments/surfaces-to-humans framing) + pilot.mdx + autonomous/overview.mdx + strategy/pipeline.mdx (optional QA node in both Mermaid diagrams) + changelog Unreleased entry; pnpm build green; NO version bump. AI×SDLC guide: flow-next.md pipeline spine + 4 QA pages (phased-rollout/ai-readiness/production-grade/metrics) carry the augments-not-replaces framing. GF microsite: 04-pipeline.md + pipeline.mmd/.svg regenerated + 06/07/08 framing; dist HTMLs re-rendered. NO version bump anywhere; external repos committed but NOT pushed (held for the batch).
## Evidence
- Commits: 3540744e7a6b56b6bc2905d2139fa7fc7d5c3f12, cdd15002dea2cbe3eb488ac465788aaea4ea4955
- Tests: python3 -m unittest test_pipeline_qa_config test_qa_receipt test_qa_smoke test_qa_tracker_event (39 passed), scripts/sync-codex.sh (validation clean, mirror byte-stable), cd ~/work/flow-next.dev && pnpm build (green, 64 pages), mmdc + bun scripts/render gf|shd|shopfully|flooid (GF microsite re-rendered)
- PRs: