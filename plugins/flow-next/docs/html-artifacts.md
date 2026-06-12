# HTML Artifacts — Optional Render Lenses for Specs & PRs

Opt-in HTML artifact mode (2.0.0+). When activated, the lifecycle skills (capture, plan, make-pr) also emit beautifully rendered, self-contained HTML pages — **render lenses** — alongside their markdown output: a spec visualizer for business/plan review and a PR review instrument for diff review. Markdown (and tracker-sync) stays 100% the source of truth; every artifact is regenerable and never parsed back as state. OFF by default — markdown-only users see zero new steps, zero token overhead, zero behavior change.

---

## Table of Contents

- [Activation](#activation)
- [The disclosure reference](#the-disclosure-reference)
- [Artifact layout](#artifact-layout)
- [Spec lens](#spec-lens)
- [PR lens](#pr-lens)
- [Viewing artifacts (the GitHub limitation)](#viewing-artifacts-the-github-limitation)
- [Commit or gitignore](#commit-or-gitignore)
- [Conversational regeneration](#conversational-regeneration)
- [Lavish integration (optional)](#lavish-integration-optional)
- [Autonomous discipline](#autonomous-discipline)

---

## Activation

One config key, written by the `/flow-next:setup` ceremony or set directly:

```bash
flowctl config get artifacts.html.enabled --json    # default: false
flowctl config set artifacts.html.enabled true
flowctl config set artifacts.html.enabled false     # turn off again
```

With the mode **off or unset**, participating skills load no reference file, write no artifacts, open no Lavish sessions, and add no output — the single config read is the only addition. The heavy disclosure file incurs zero token cost when off.

`/flow-next:setup` asks once (only when the key is unset): enable or not, then — on yes — commit-vs-gitignore for `.flow/artifacts/` and the optional `lavish-axi` install offer (never auto-installed). See the [config table in `flowctl.md`](flowctl.md#config) for the key reference.

flowctl only stores the knob. Generation is agentic: the host agent reads the disclosure reference and writes the HTML — there is no deterministic Python renderer and no new slash command.

## The disclosure reference

One shared file carries ALL design and generation rules: [`../references/html-artifacts.md`](../references/html-artifacts.md). Participating skills load it only when the mode is active (progressive disclosure). It owns:

- the hard rules (render-lens-never-record, self-contained single file, fixed paths, idempotent link line, staleness stamp, print CSS, deterministic JS)
- the anti-slop design contract (warm-black instrument-panel house style — own palette and local-only font stacks, no CDN fonts, no purple gradients)
- per-lens content guidance (spec lens §4, PR lens §5), DAG rendering discipline (§6), the Lavish flow (§7), and the pre-publish checklist (§8) including the self-containment grep

Never duplicate its rules elsewhere — skills cross-link it and follow it top to bottom.

**Self-contained or nothing:** inline CSS/JS, zero external requests (fonts included). The artifact must open identically from `file://`, inside Lavish, in a CI archive, and printed.

## Artifact layout

```
.flow/artifacts/<spec-id>/
├── spec.html    # spec lens — written by capture (§5.10) and plan (Step 8.5)
└── pr.html      # PR lens — written by make-pr (Phase 1.5)
```

Paths are **fixed and deterministic** — never timestamped, never suffixed. Lavish keys annotation sessions on the absolute file path; a moving path orphans the annotation queue. Regeneration always overwrites the same file.

Every artifact footer carries the sentence "Render lens, not record.", the source path, and a **staleness stamp** (spec `updated_at` + repo commit for the spec lens; head sha vs base for the PR lens) so a reader can tell when the lens lags the markdown.

## Spec lens

**One generation pathway, state-dependent rendering** — what renders depends on what state exists, not on a config axis:

| Lifecycle touchpoint | Hook | What renders |
|---|---|---|
| `/flow-next:capture` (fresh spec) | capture workflow §5.10, last in Phase 5 | Spec-only view: thesis, acceptance criteria with source-tag provenance chips, architecture panel, edge cases, boundaries, decision context — the business-review surface |
| `/flow-next:plan` (tasks now exist) | plan Step 8.5 — runs only **after** the Step 8 refinement loop exits (never mid-edit; late task mutations regenerate before final output) | Same file, same path, regenerated with the plan layer: task dependency DAG with critical path, R-ID → task coverage matrix, plan dials |

After writing, the skill updates the spec markdown's artifact link line — a single line carrying the `<!-- flow-next:artifact-link -->` marker, **replaced in place** on every regeneration (inserted once after the H1 if absent; repeated runs never duplicate it). The link target is repo-relative (resolves on every ref, survives branch deletion) — never a branch-pinned blob URL.

Generation failure is non-fatal everywhere: skip the link line, one stderr note, never block the capture/plan — the markdown is already on disk and is the record.

## PR lens

`/flow-next:make-pr` Phase 1.5 (between the export-payload gather and body rendering) generates `pr.html` — a **read-only review instrument**: masthead + dials, sticky review-progress bar, the 90-second read, a churn map grouped by review intent, the R-ID → evidence table, a where-to-look checklist, and a risk register.

- **Diff-derived, never commit messages.** Inputs are the `flowctl spec export-cognitive-aid` payload plus the real diff stat; commit subjects/bodies are not lens input.
- **R-ID verification — warn-in-artifact, never block.** Payload-vs-diff mismatches (claimed evidence outside the diff range, uncovered R-IDs, evidence touching no diff files) render as visibly flagged rows (red R-ID cell + `mismatch` chip + reason). A mismatch never blocks PR creation and is never silently dropped.
- **Narrow commit.** When the artifact file is tracked, it lands in exactly one pathspec-confined commit — `chore(flow): pr artifact <spec-id>`, the artifact file only, never `git add -A` — before the PR body captures `HEAD_SHA`, so the SHA-pinned blob link in the body resolves once the branch pushes. Byte-identical regeneration makes no empty commit.
- **Failure-guarded git.** Every git step is guarded (`LENS_OK` flag): a hook rejection or stage failure degrades to no-body-line + one stderr note; the PR is still created.
- **`--dry-run` writes nothing.** No artifact, no commit, no body line — the dry-run no-state-change promise holds.
- **Ralph stdout contract untouched.** Under Ralph the stdout stays exactly `PR_URL=<url>`; all artifact messaging routes to stderr.
- **No annotate loop, ever** — interactive and autonomous alike. Review conversation belongs to the code host; make-pr never opens a Lavish session and never polls.

## Viewing artifacts (the GitHub limitation)

GitHub renders committed `.html` files as raw source and rejects `.html` attachments on PRs — it will not display the artifact as a page. The skills therefore link with **local-open guidance**:

```bash
open .flow/artifacts/<spec-id>/spec.html        # macOS; xdg-open on Linux
```

The PR body links the committed artifact as a SHA-pinned blob URL with the note "GitHub renders committed HTML as source — open locally in a browser". Optionally, a third-party raw-preview service (e.g. raw.githack.com) can render a committed blob URL directly in the browser — useful for remote reviewers, but third-party and entirely optional; flow-next never embeds such links in generated output. Don't over-engineer hosting: the artifacts are local-first by design.

## Commit or gitignore

Artifacts are **committed by default** — that is what makes the make-pr blob links resolve for remote reviewers. The setup ceremony offers the alternative:

| Choice | Trade-off |
|---|---|
| **Commit** (default) | PR body carries a resolvable SHA-pinned blob link; reviewers can fetch and open locally; artifacts ride normal code review. Cost: regenerable HTML in history. |
| **Gitignore** (`artifacts/` appended below the auto-managed footer in `.flow/.gitignore`) | Clean history; local-open guidance only — make-pr skips blob links entirely. |

The skills probe ignore status before choosing a link (`git check-ignore --no-index -q` against the exact artifact file — catching `*.html` and exact-path rules, not just the directory; `--no-index` so an artifact committed before the ignore rule still honors it) and **never emit a blob link that 404s**.

## Conversational regeneration

There is no regeneration slash command. Auto-regen rides the lifecycle touchpoints (capture, plan, make-pr); everything else is conversational — ask the host agent:

> "regenerate the artifact for fn-12"

after hand edits, an interview pass, or drained Lavish annotations. The agent reloads the disclosure reference, re-reads the spec + flowctl state, regenerates at the same fixed path, and re-runs the pre-publish checklist.

## Lavish integration (optional)

`lavish-axi` (npm) is an optional companion: it serves an artifact in a browser session where humans annotate; annotations flow back to the agent as edits of the **markdown source of truth**, then the lens regenerates. It is detected on PATH (`command -v lavish-axi`) and **never required** — same discipline as clawpatch/`/flow-next:map`: absent means a plain static artifact, zero mention of Lavish, never an error, never an auto-install.

```bash
npm i -g lavish-axi          # or zero-setup per run: npx lavish-axi <artifact.html>
lavish-axi .flow/artifacts/<spec-id>/spec.html
```

How it actually works (verified against the real architecture — not the upstream README's per-workspace wording):

- **Global state, not per-workspace.** Annotations queue in the global `~/.lavish-axi/state.json`. There is no per-repo state file.
- **Pull-only, session-spanning.** The agent side drains the queue via the `lavish-axi poll` CLI — nothing is pushed into the agent. Feedback survives agent death: annotate tonight, any later agent session drains the queue tomorrow.
- **Idle-stop is invisible.** The local server idle-stops after ~30 minutes. The artifact still renders as a plain static page (self-containment guarantees it); re-running `lavish-axi <file>` resumes the session.
- **Sessions key on the absolute artifact path** — the reason artifact paths are fixed. **Worktree caveat (documented, accepted):** different worktrees mean different absolute paths, which means *separate* Lavish sessions — annotations made against one worktree's artifact do not appear in another's.
- **Apply loop.** Each drained annotation maps to an edit of the spec/task markdown (never the HTML), then the lens regenerates at the same path.
- **Scope:** the annotate loop applies to **spec artifacts only**. The PR lens never enters it — a PR artifact derives from an immutable diff and GitHub already owns review comments.

## Autonomous discipline

Pilot, Ralph, and other autonomous contexts **generate only**: they may write artifacts at the same lifecycle touchpoints but **never open a Lavish session and never poll** — an autonomous loop never blocks on a human. At most a one-line stderr note that a session has pending prompts. The guards are mechanical (in the skill snippets, gated on the non-interactive marker family — `FLOW_AUTONOMOUS`, `FLOW_RALPH`, `REVIEW_RECEIPT_PATH`, autofix mode), not prose-only. Ralph's `PR_URL=` stdout contract and all receipts are untouched by artifact generation. See [`ralph.md`](ralph.md#html-render-lenses-generate-only--never-poll).
