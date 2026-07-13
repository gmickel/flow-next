# Classification (Phase 0.5)

Prime's first phase: classify what KIND of project this is before anything downstream runs. The classification block parameterizes everything after it - which per-shape playbook applies, the N/A denominators (via the whitelist in [pillars.md](pillars.md)), the report shape, and the operability-ladder ceiling.

Classification is **deterministic and host-inline** (no judgment scout, no new mode): the raw signals come from the `flowctl prime classify --json` emitter (schema pinned below; the emitter itself lands in a later task); the skill layers the Axis-5 shape reasoning, the per-axis confidence, the bounded clarification (Phase 0.6), and playbook selection on top. Every probe is bounded and capped - `git ls-files` counts, `find -maxdepth`, config-presence globs, ONE sampled ambiguity grep, `scc`/`tokei` when present (never `cloc`, never exhaustive reads).

**Classification is heuristic.** The block always prints its evidence and its confidence. A low-confidence or uninferable call is routed to the Phase 0.6 clarification (the R15 protocol) rather than guessed; autonomous / `--report-only` runs state the assumption inline and list it under "Unresolved questions" instead of blocking. Misclassification must degrade gracefully - a monorepo misread as a single repo still gets a correct base report; only the playbook block is off.

Thresholds throughout are **research-anchored starting opinions**, collected in the tunable table near the end. Tune them with portfolio data here, never in flowctl code.

---

## The five axes

### Axis 1 - lifecycle: `greenfield | hybrid | brownfield`

Multi-signal, never one heuristic; borderline cases land in **hybrid** ("young but real").

- **Greenfield** = (`git rev-list --count HEAD` < ~25 commits AND no tags AND no CI config) OR (tracked files < ~30 with no domain source beyond a recognizable generator scaffold - `create-next-app`, `cargo new`, `uv init`, `dotnet new` fingerprints).
- **Corroborators** (raise/lower confidence, never decide alone): repo age (`git log --reverse` first-commit date), single contributor (`git shortlog -sn`), no lockfile.
- **Brownfield** = the default once commit history, tags, CI, or real domain source are present.
- **Hybrid** = signals disagree (e.g. a scaffold with 40 commits, or a young repo that already has CI + a lockfile). Hybrid keeps the full scorecard but flags the young-but-real caveat.

Greenfield selects the bootstrap-plan report shape (scorecard suppressed - see playbooks.md); the N/A whitelist's greenfield row governs recorded-deferral N/A.

### Axis 2 - topology: TWO INDEPENDENT BITS, not an enum

A single XOR verdict silently drops constellation guidance for a monorepo that is ALSO a constellation member (eval: a turbo monorepo that is also a `dociq-*` constellation member). Emit two independent bits.

**Bit 1 - monorepo** = workspace / build-graph config present:
`pnpm-workspace.yaml`, `package.json` `"workspaces"`, `nx.json`, `turbo.json`, `WORKSPACE` / `MODULE.bazel`, `go.work`, a Cargo workspace, `.groupproj` (Delphi), or multi-module Maven/Gradle - OR many **CROSS-REFERENCED** manifests under one root. A bare manifest count is NOT enough: a spike + a scaffold + a docs-site subdir produced a false monorepo in eval. Spikes, scaffolds, and site subdirs are downweighted; they are noted as subprojects, not top-level members.

**Bit 2 - constellation-member**, three confidence tiers:

- **(a) LIKELY:** sibling dirs with `.git` (`ls ../*/.git`), shared org in remotes, shared naming prefix (`acme-api`, `acme-web`).
  **Workspace-parent dampener (load-bearing, eval-proven):** a parent holding many git dirs (>~20) is a developer WORKSPACE, not a home base - shared-org there is meaningless (3 of 5 real eval repos false-positived without this). Inside a workspace parent, only a prefix-family cluster (>=2 named siblings) or a tier-(c) reference raises LIKELY, and it ALWAYS routes to the Phase 0.6 clarification, never auto-confirms. Prefix matches can include scratch / test repos, so they are LIKELY-tier input only.
- **(b) CONFIRMED:** a parent-level `CLAUDE.md` / `AGENTS.md` or manifest (`repos.yaml`, `mani.yaml`, `.meta`, `*.repos`, `workspace.toml`, `default.xml`, `.code-workspace`), a parent `docker-compose` / `justfile` / `mise.toml`, or a `_plans/` dir - AND the parent is NOT a workspace parent.
- **(c) ASK:** in-repo external references - a compose `build: ../other-service` or same-org images, a CI checkout of a second repository, OpenAPI / proto client generation pointing at another repo's spec, a `go.mod` `replace` / pnpm `link:` / `pip -e ../` outside the repo, env vars referencing ports of services this repo does not define, AND **textual cross-repo path references in the agent file / README**. Both real constellations in eval were referenced in prose ("see ~/work/transcribe/docs/RELEASING.md (the app repo)") while the pattern probes returned empty; prose references also sharpen the Phase 0.6 question (never ask what a probe already answered).

### Axis 3 - size / legibility band: `small (<100K) | medium (100-400K) | large (400K-2M) | huge (>2M LOC or >20K files)`

The banded LOC is the bounded file-estimate over the EXCLUDED, deduped blob list, so the number honors the exclusions below (and content-hash dedup) exactly. `scc` (seconds even at 15M LoC) / `tokei`, when present, run only as whole-checkout **corroboration** (emitted under `loc_corroboration`) - they count the whole tree and can't see the per-file/blob exclusions, so they never set the band. Never `cloc` (8-20x slower), never exhaustive reads.

**Exclusions applied BEFORE counting** (each hit a real repo in eval):

- Tool-managed dirs: `.flow/`, `.claude/`, `.codex/`, `.agents/`, `.cursor/`, `.factory/`, `.windsurf/`, `.opencode/`, `.pi/`. Flow-next's own bundled `flowctl.py` alone produced a phantom "Python 42%" stack and +40% LOC on a pure-TS repo - prime polluting its own classification is the most embarrassing possible failure.
- Vendored / generated globs.
- Test / eval fixture corpora.
- Agent-workflow state (`plans/`, `history/`).
- Content-hash duplicate files (a dual-copy file was 57% of one repo's counted LOC and flipped its band) - detected via git blob IDs from `git ls-files -s`, no content reads.
- Dirs a tracked script deletes-and-regenerates.
- Tracked legacy snapshots (an `original-implementation/` dir the repo's own agent file marks off-limits).

The same exclusion list feeds the largest-files pathology inventory (FH2 / LEG4) - prime must never report its own tooling as the repo's top pathology.

**Legibility sub-signals:** top-level dir count; entrypoint-glob hits (`main.*`, `index.*`, `cmd/*/main.go`, `*.dpr`, framework markers); packages-vs-instruction-files ratio; tracked generated / vendored code (`vendor/`, `dist/`, `*_pb2.py`, `.dcu`); a root instruction file >~300 lines with zero nested files; ONE bounded grep-ambiguity probe (2-3 core domain identifiers - hundreds of hits predicts wrong-file / wrong-symbol thrash).

**Empirical anchors that make the band actionable:** agent pass rates collapse above ~100K LOC (RepoMod-Bench); code-intelligence tooling is net NEGATIVE below ~400K LOC and strongly positive from 400K-2M (Sourcegraph CodeScaleBench, 1,281 runs). Recommendations MUST tier accordingly - recommending heavy LSP / index tooling on a small repo is itself a prime failure (see the size-tiering rule in Edge Cases and R12).

### Axis 4 - stack(s): MANIFEST-GATED, LOC-histogram corroborated

Detection is gated on a manifest per [stacks.md](stacks.md) (`package.json`, `pyproject.toml`, `pom.xml` / `build.gradle`, `*.sln` / `*.csproj` + TargetFramework era, `composer.json`, `go.mod`, `Gemfile`, `CMakeLists`, `*.dproj` / `*.dpr`, `*.vbp`, `*.pks` / `*.pkb`, `*.cbl`). A post-exclusion LOC-weighted extension histogram is CORROBORATION only: a stack with no manifest and no meaningful LOC share never appears.

The histogram vocabulary derives from the detected manifests + extensions, NEVER a fixed list - a fixed six-stack list made Ruby invisible while phantom Python ranked second in eval. Subproject manifests (a site subdir, a spike) are noted as subprojects, not top-level stacks. The polyglot count feeds the legibility verdict.

### Axis 5 - delivery shape(s): MULTI-VALUED

`web service/app | CLI | library/SDK | plugin/prose-product | desktop | docs site | data/ML | IaC`. One repo can carry several (a real eval repo is CLI + daemon + web UI + desktop shell). This axis is the single root cause of most misfires, so it is multi-valued and skill-judged.

**Ordering rule (resolution 9):** shape detection runs from markers / manifests FIRST, THEN denominators are recomputed ONCE under the winning shape(s) - no iteration.

Detection markers (heuristic, confidence-marked, Phase-0.6-askable): manifest `bin` / `exports` fields; framework markers; serve / health code; `.desktop` / electron / tauri / electrobun markers; skills / prose ratios. The emitter emits these markers RAW; the skill derives the shape values.

Shape gates (what the shape controls):

- **(a) LOC denominator policy** - prose counts as source for plugin/prose and docs-site shapes (a plugin repo measured "Python 92%" while its actual product was 146K lines of markdown the histogram ignored).
- **(b) operability-ladder CEILING** - library / plugin / prose ceiling = tier 2, reported "2/2 at ceiling" (never "2 of 3"), move-up suppressed, cheapest move goes SIDEWAYS into observable / drivable. Desktop shape's honest tier evidence is the repo's own packaged-runtime smoke, not a boot probe.
- **(c) which AO/DR rows apply** - CLI-shaped repos grade on the agent-first-CLI row (`--json`, exit codes) as the primary drivability surface (the N/A whitelist swaps the DR web rows for DR6).
- **(d) playbook selection.**

---

## Per-axis confidence

Confidence is a **separate field on every axis** (`high | medium | low`), NEVER punctuation in the verdict enum. It combines signal agreement (do the probes point the same way?) with the emitter's completeness diagnostics for that collector (partial / sampled / capped data can never yield high confidence - resolution 21b). A `low` on any axis that changes a playbook or a verdict routes to Phase 0.6; a `low` that changes nothing is printed but not asked.

---

## Assessment scope (orthogonal field)

`assessment_scope` = `repository | workspace-member | constellation-home-base`. It is ORTHOGONAL to the two topology bits because a non-git parent home base is neither bit. It carries its own evidence + confidence, appears in the emitter JSON and the `--classify-only` block, and routes playbook selection:

- **repository** - a normal standalone checkout.
- **workspace-member** - cwd is below the git toplevel (a package inside a monorepo); classified against the ROOT topology, reported as "assessing workspace member `<pkg>` of `<root>`", never silently standalone.
- **constellation-home-base** - prime is running in a parent dir that is not itself a project repo; selects the constellation-layer assessment (R10) instead of erroring on "no manifest found".

---

## Thresholds (tunable)

Research-anchored starting opinions. Tune here with portfolio data, never in flowctl code.

| Threshold | Value | Axis / use |
|---|---|---|
| Greenfield commit count | < ~25 | Axis 1 |
| Greenfield tracked-file count | < ~30 | Axis 1 |
| Size band boundaries | 100K / 400K / 2M LOC | Axis 3 |
| Huge file-count boundary | > 20K files | Axis 3 |
| Code-intelligence net-negative floor | < 400K LOC | Axis 3 / R12 |
| Workspace-parent git-dir count (dampener) | > ~20 git dirs | Axis 2 bit 2 (a) |
| Prefix-family cluster | >= 2 named siblings | Axis 2 bit 2 (a) |
| Instruction-file review-trigger band | ~200 lines (nested), ~300 (review) | legibility / DC2 |
| Undeclared-env "stale template" | > ~30% of reads | DE1 |
| Cross-repo change rate for consolidation | ~30-50% of features | constellation scale ladder |
| Repos for a release-ordering registry | 20+ | constellation scale ladder |

---

## Edge-case ladder (resolution 8)

- **Unborn HEAD** (no commits) - lifecycle = greenfield, evidence "no commits"; never error on the empty `git rev-list`.
- **Non-git dir** - run constellation-home-base detection FIRST (manifest + sibling checkouts); if it is not a home base, exit cleanly with a clear message, never a stack trace.
- **Git-worktree siblings** - a sibling whose `.git` gitdir resolves to the SAME repo is a worktree, not a constellation sibling; exclude it from constellation signals (a worktree-sibling fixture guards this in R19).
- **cwd below the git toplevel** - detect the workspace-member scope, report "assessing workspace member `<pkg>` of `<root>`", classify against the root topology, never silently treat the package as standalone.
- **Timeouts** - use the harness timeout parameter or a portable background + kill pattern; NEVER bare `timeout(1)` (absent on stock macOS).
- **POSIX character classes** everywhere in the probe patterns (portability across BSD / GNU tooling).

---

## Emitter contract: `flowctl prime classify --json`

The deterministic layer of Phase 0.5 ships as a pure-stdlib flowctl emitter (bounded, no LLM, no judgment). This file PINS the contract; the implementation lands in the flowctl task (dual-copy `plugins/flow-next/scripts/flowctl.py` and `.flow/bin/flowctl.py`, byte-identical, parity-tested). The skill invokes the emitter and layers judgment (Axis-5 shape values, final per-axis confidence, the Phase 0.6 asks, playbook selection) on the result.

**Transport:** JSON on **stdout**; progress + diagnostics on **stderr**. **Redaction (hard contract):** emitted evidence NEVER contains secret values or complete sensitive config lines - **key names only** (a fixture asserts this).

**Schema (fixed field order):**

```json
{
  "schema_version": 1,
  "assessment_scope": {
    "value": "repository | workspace-member | constellation-home-base",
    "confidence": "high | medium | low",
    "evidence": ["<string>", "..."]
  },
  "axes": {
    "lifecycle": {
      "value": "greenfield | hybrid | brownfield",
      "confidence": "high | medium | low",
      "signals": {
        "commit_count": 0,
        "tags": 0,
        "ci_config": false,
        "tracked_files": 0,
        "generator_scaffold": "create-next-app | cargo | uv | dotnet | null",
        "first_commit_days": 0,
        "single_contributor": false,
        "lockfile": false
      },
      "evidence": ["<string>", "..."]
    },
    "topology": {
      "monorepo": {
        "value": false,
        "confidence": "high | medium | low",
        "signals": { "workspace_config": [], "cross_referenced_manifests": 0, "downweighted_subprojects": [] },
        "evidence": ["<string>", "..."]
      },
      "constellation_member": {
        "value": false,
        "tier": "a | b | c | none",
        "confidence": "high | medium | low",
        "workspace_parent": false,
        "signals": { "sibling_git_dirs": 0, "shared_org": false, "prefix_family": [], "in_repo_external_refs": [], "prose_cross_repo_refs": [] },
        "evidence": ["<string>", "..."]
      }
    },
    "size": {
      "band": "small | medium | large | huge",
      "confidence": "high | medium | low",
      "loc": 0,
      "files": 0,
      "tool": "file-estimate",
      "exclusions_applied": ["tool-managed", "vendored", "fixtures", "agent-state", "hash-duplicate", "regenerated", "legacy-snapshot"],
      "loc_corroboration": { "tool": "scc | tokei", "loc_wholetree": 0 },
      "legibility": {
        "top_level_dirs": 0,
        "entrypoints": [],
        "generated_vendored_tracked": [],
        "instruction_file_lines": 0,
        "ambiguity_probe_hits": 0
      },
      "evidence": ["<string>", "..."]
    },
    "stacks": [
      {
        "name": "<stack>",
        "manifest": "<path>",
        "loc_share": 0.0,
        "subproject": false,
        "confidence": "high | medium | low",
        "evidence": ["<string>", "..."]
      }
    ]
  },
  "shape_markers": {
    "bin_exports": [],
    "framework_markers": [],
    "serve_health_code": [],
    "desktop_markers": [],
    "prose_ratio": 0.0
  },
  "collectors": [
    {
      "name": "<collector>",
      "status": "ok | error",
      "complete": true,
      "sampled": false,
      "truncated": false,
      "cap_hit": false,
      "errors": [],
      "tool": "<tool used>",
      "operations": 0
    }
  ]
}
```

Notes on the split:
- The emitter emits axes 1-4 with deterministic values + a mechanical confidence, plus RAW `shape_markers` (Axis 5 is NOT resolved by the emitter - the skill reasons over the markers).
- `collectors[]` carries the per-collector completeness diagnostics (resolution 21b). The judgment layer MUST downgrade confidence and use NOT ASSESSED when `complete` is false / `sampled` / `truncated` / `cap_hit` - partial data never yields high confidence.
- The emitter ALSO carries the deterministic substance-grep outputs consumed by Phase 2/3 (its `emitter`-owned rows in the criterion-to-score map in [pillars.md](pillars.md)); this file pins only the classification portion of that payload. Two substance-payload contracts worth pinning here because the judgment layer depends on them:
  - `substance.secrets_gate` splits ENFORCED invocations from config-only presence: `tools_found` + `locations` carry only scanner invocations found in enforcement surfaces (pre-commit config, package.json, CI files); scanner config/baseline files (`.gitleaks.toml`, `.secrets.baseline`) land in `configs_found` (`{tool, path}` entries) as EVIDENCE-ONLY - FH4 must never grade config presence alone as an enforced gate.
  - `substance.ci_gate` trigger detection routes by CI system: GitHub workflows are parsed for `on:` push/pull_request forms; `.gitlab-ci.yml` counts as push-gated by default, `bitbucket-pipelines.yml` counts when its `pipelines:` config has a `default:`/`branches:` section, and `azure-pipelines.yml` counts unless `trigger: none` (these systems run on push by default - the GitHub `on:` grammar is never forced on them).

---

## `--classify-only` block

`--classify-only` wraps the emitter plus the judgment layer, prints the classification block, and EXITS in seconds (the portfolio-triage entry point for 100+ repos - the R2 cheapness contract). It **never asks** (it is the cheap sweep); instead of the Phase 0.6 clarification it prints confidence plus a "would ask" list.

Fixed field order, one line per axis, each carrying `value + confidence + evidence-count`:

```
assessment_scope: repository (high, 3 evidence)
lifecycle:        brownfield (high, 4 evidence)
topology:         monorepo=yes (high, 2 evidence) | constellation-member=tier-c (low, 1 evidence)
size:             medium ~180K LOC / 2.1K files via scc (high, 5 evidence)
stacks:           TS/JS (0.71), Python (0.18 subproject) (high, 3 evidence)
shape:            web-service, CLI (medium, 2 evidence)
would-ask:        [constellation] sibling repos elsewhere? (tier-c prose ref: README ~/work/other)
```

The interactive block is the same lines PLUS the printed evidence items under each axis and, when a low-confidence or uninferable fact changes a playbook or verdict, the Phase 0.6 clarification (R15) rather than the "would ask" list.
