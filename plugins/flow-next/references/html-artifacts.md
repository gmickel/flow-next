# HTML artifacts — house style + generation rules

Shared disclosure reference for flow-next's optional HTML artifact mode. Loaded by
participating skills (capture, plan, make-pr) ONLY when `flowctl config get
artifacts.html.enabled` returns `true` — never load this file when the mode is off
or unset. Conversational regeneration ("regenerate the artifact for <spec-id>")
reads this same file; there is no other generator.

Structure: hard rules → design contract → per-lens guidance → DAG discipline →
Lavish → pre-publish checklist. Follow it top to bottom when generating.

## 1. Hard rules (the contract — every artifact, no exceptions)

1. **Render lens, never the record.** The markdown spec (and tracker-sync) is the
   sole source of truth. Artifacts are regenerable derivations; NEVER parse an
   artifact back as state, never edit one by hand expecting persistence. Every
   footer carries the sentence "Render lens, not record." and names the source file.
2. **Self-contained single file.** Inline ALL CSS in one `<style>` block and ALL JS
   in one `<script>` block. ZERO external requests of any kind: no CDN scripts, no
   Google Fonts, no Tailwind, no `@import`, no remote `url(...)`, no `<img>`/`<iframe>`
   pointing off-disk, no `fetch()`. The habit of reaching for a CDN is the #1 failure
   mode — the artifact must open identically from `file://`, inside Lavish, in a CI
   archive, and on paper. Run the self-check grep (§2) before publishing.
   `<a href="https://...">` navigation links (repo, tracker, PR) are fine — only
   *loaded* resources are banned.
3. **Fixed deterministic output paths.** Spec lens → `.flow/artifacts/<spec-id>/spec.html`;
   PR lens → `.flow/artifacts/<spec-id>/pr.html`. Never timestamped, never suffixed:
   Lavish keys annotation sessions on the absolute path; a moving path orphans the queue.
4. **Idempotent link line in the source spec.** When a spec lens links back from the
   spec markdown, the line carries the marker comment `<!-- flow-next:artifact-link -->`.
   On regeneration, find the marker and REPLACE that whole line in place; if absent,
   insert once after the H1 title. Repeated runs leave exactly one link line — never
   a duplicate. Canonical shape:
   `> HTML render lens: [.flow/artifacts/<spec-id>/spec.html](<repo-relative-path>) — regenerable, markdown is the record. <!-- flow-next:artifact-link -->`
   The link target is REPO-RELATIVE (from `.flow/specs/` that is
   `../artifacts/<spec-id>/spec.html`) — it then resolves on every ref and survives
   branch deletion. NEVER a branch-pinned blob URL here (404s after merge); absolute
   blob URLs belong only where absolute URLs are mandatory (the PR body, per make-pr).
5. **Staleness stamp in every footer**, inside a bordered `.stamp` element so a reader
   can tell when the lens lags the markdown:
   - spec lens: `staleness stamp · spec updated_at <ISO> · repo commit <short-sha> · rendered <YYYY-MM-DD>`
   - PR lens: `staleness stamp · head <short-sha> vs base <ref> · rendered <YYYY-MM-DD>`
6. **localStorage is try-wrapped progressive enhancement only** (review checkmarks,
   collapsed state). It works on `file://` in most browsers and may be blocked
   elsewhere — the artifact stays fully readable and usable with it unavailable.
   Every access sits inside `try { ... } catch (e) {}`.
7. **Print CSS is mandatory.** `@media print` overrides the dark vars to a light
   theme, hides sticky chrome (nav rail / progress bar) and the grain overlay,
   sets `section { break-inside: avoid-page; animation: none; }`, and declares
   `@page { size: A4; margin: 1.2cm; }` (`A4 landscape` when a DAG is present).
8. **Deterministic JS only.** Inline scripts may measure the DOM, wire hover/checkbox
   interactions, and persist to localStorage. No network, no randomness, no clock-
   dependent rendering (the render date is baked in as text at generation time).

## 2. Self-containment self-check

Before publishing, run this against the generated file — it must print OK:

```bash
F=.flow/artifacts/<spec-id>/spec.html   # or pr.html
if grep -nE '<script[^>]+src=|<link[^>]+href=|<img[^>]+src=|<iframe|srcset=|@import|@font-face|url\([[:space:]]*["'"'"']?https?:|fetch[[:space:]]*\(' "$F"; then
  echo "FAIL: external/loaded resources found — inline or remove them"
else
  echo "OK: self-contained"
fi
```

## 3. Design contract — the instrument-panel house style

Positive contract first: copy these blocks verbatim, then compose. The aesthetic is
a **warm-black instrument panel** — hairline rules, uppercase micro-labels, monospace-
led with a serif editorial counterpoint, amber as the single dominant accent.

### 3.1 CSS variables (copy-paste; do not invent a new palette)

```css
:root {
  --bg: #0c0b09; --panel: #14120e; --panel-2: #1a1712;
  --line: #2c2719; --line-soft: #211d14;
  --ink: #e8e2d4; --dim: #9a917c; --faint: #645d4c;
  --amber: #ffb454; --amber-deep: #cc8b33;
  --green: #87d96c; --red: #f07178; --cyan: #5ccfe6; --violet: #c9a7f5;
  --mono: "Berkeley Mono", "JetBrains Mono", "SF Mono", ui-monospace, "Cascadia Code", Menlo, Consolas, monospace;
  --serif: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
}
```

Semantic accent usage: **amber** = identity/emphasis (ids, kickers, section numbers,
critical path); **green** = good/pass/additions; **red** = risk/fail/deletions;
**cyan** = code/cross-references/secondary data; **violet** = sparingly, tertiary
grouping. Body text is `--ink` on `--bg`; supporting prose `--dim`; micro-labels `--faint`.

### 3.2 Print-theme variable overrides (copy-paste into `@media print`)

```css
@media print {
  :root { --bg:#fff; --panel:#fafaf7; --panel-2:#f2f0ea; --line:#ccc7ba; --line-soft:#e2ded2;
          --ink:#1a1812; --dim:#4a463c; --faint:#8a8678; --amber:#9a6a10; --amber-deep:#9a6a10;
          --green:#2e7d32; --red:#b3261e; --cyan:#0a6e8a; --violet:#6a3fae; }
  body::before { display: none; }
  nav.rail, .progress { display: none; }
  section { break-inside: avoid-page; animation: none; }
  @page { size: A4; margin: 1.2cm; }  /* switch to `size: A4 landscape;` ONLY when the artifact renders a DAG */
}
```

### 3.3 Typography and atmosphere

- Base: `font-family: var(--mono); font-size: 14px; line-height: 1.65;` on a `--bg` body.
- One serif moment per artifact: the `.tldr` lead paragraph — `font-family: var(--serif);
  font-size: 20–21px; line-height: 1.6; max-width: 920px;` with `strong` in amber and
  `em` in cyan. This contrast is the signature; do not serif anything else.
- Micro-labels everywhere: `font-size: 10–11px; letter-spacing: .14–.22em;
  text-transform: uppercase; color: var(--faint);` (dial captions, section heads, kickers).
- Atmosphere overlay (subtle scanline grain + top glow) on `body::before`:

```css
body::before {
  content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 999;
  background:
    repeating-linear-gradient(0deg, transparent 0 2px, rgba(255,180,84,0.012) 2px 4px),
    radial-gradient(ellipse 120% 60% at 50% -10%, rgba(255,180,84,0.05), transparent 60%);
}
```

### 3.4 Core components (recipes, not optional)

- **Masthead**: uppercase amber `.kicker` line (artifact type · provenance · date,
  `·` separators in `--faint`) → `h1` with the id in an amber `<span class="id">` →
  a **dials strip**: one bordered `--panel` row of stat cells, each a big 19px bold
  value over a 10px uppercase caption, hairline-separated. Dials carry the at-a-glance
  numbers (R-IDs, coverage, tasks, diff ±, status).
- **Sticky chrome**: spec lens gets a `nav.rail` of uppercase section links
  (`position: sticky; top: 0; backdrop-filter: blur(6px);` on translucent `--bg`);
  PR lens gets the review-progress bar instead (§5).
- **Section heads**: `.shead` — amber two-digit number, uppercase 17px title, hairline
  bottom border, right-aligned `--faint` note (e.g. `scope: business`, row counts).
- **Panels and cards**: `border: 1px solid var(--line); background: var(--panel);`
  — square corners. Inner elements step to `--panel-2`. Callouts get a 3px left
  border in the semantic accent.
- **Tables**: full-width, `border-collapse: collapse`, uppercase `--faint` headers,
  `--line-soft` row rules, row hover lifts text to `--ink` on `#1c170d`.
- **Chips**: bordered inline-blocks, 10–11px — `.tchip` for task ids; provenance
  `.tagchip` variants colored green (`user`) / cyan (`paraphrase`) / red (`inferred`).
- **Two-column IS / IS-NOT boundaries**, green ✓ / red ✕ `::marker` content.
- **Motion**: exactly one high-impact moment — the staggered section reveal:
  `@keyframes rise { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }`
  with per-section `animation-delay` steps of ~.05s. Plus at most one functional
  transition (bar fills, hover lifts). Nothing else animates.
- **Responsive**: one `@media (max-width: 760px)` pass collapsing grids to single
  column and tightening the wrap padding.

### 3.5 Forbidden (verbatim — the anti-slop list)

Per Anthropic's web-artifacts-builder guidance, these are banned outright:

- **centered-everything layouts** — this is a left-anchored instrument panel
- **purple gradients** (and any purple-on-white default scheme)
- **uniform rounded corners** — corners are square; borders are hairlines
- **Inter** — and every other CDN-fetched font; the stacks in §3.1 are local-only
- emoji as iconography; decorative stock illustration; glassmorphism cards
- timid gray-on-white minimalism — commit to the warm-black palette

## 4. Spec lens — one pathway, state-dependent rendering

Generated from the spec markdown plus flowctl exports (`show --json`, the task list
when present). ONE generator; what renders depends on what state exists.

**Always (pre-plan, spec-only view — the business-review surface):**
1. Masthead + dials (status, R-ID count, activation mode, tracker link if synced).
2. Thesis — `.tldr` serif lead distilling the goal, then a `.thesis` amber-left-border
   callout carrying the one load-bearing clarification.
3. Acceptance criteria table — every R-ID row with **source-tag provenance chips**
   (`user` / `paraphrase` / `inferred`) pulled from the spec's tags. Long criteria
   collapse behind `<details>` summaries.
4. Architecture panel — boxes-and-arrows grid built from bordered divs (`.archgrid`),
   plus a `.ladder` strip for fallback chains when the spec has one.
5. Edge cases grouped into 3–4 accent-colored cards by blast radius.
6. Boundaries as the IS / IS-NOT two-column block.
7. Decision context — `.dec` cards: D-number tag, chosen path, quoted user evidence
   in green italics, **Rejected:** line in red.
8. Proof point (when the spec has one) — amber-bordered gradient panel.
9. Footer: render-lens sentence + source path + staleness stamp (§1.5).

**Added post-plan (same file, same path, regenerated):**
- The dependency DAG (§6) with critical path, directly after the thesis.
- An "Owned by" chips column on the acceptance table (R-ID → tasks), and a hover
  wire: hovering a DAG node lights the rows of the R-IDs it satisfies
  (`data-rids` on nodes, `data-rid` on rows, `.lit` class toggle).
- Dials gain: tasks count, R-ID coverage `n / n`, critical-path depth.

Link-back, GitHub limitation, and commit-or-ignore: after writing the artifact,
update the spec's marker link line (§1.4). GitHub renders committed HTML as raw
source and rejects `.html` attachments — link with local-open guidance. Artifacts
are committed by default; the spec-md link is repo-relative per §1.4 (resolves on
every ref — blob URLs are reserved for the PR body, where make-pr requires absolute
URLs). When the project gitignores the artifact (`git check-ignore --no-index -q`
against the EXACT artifact file path hits — catching `.flow/artifacts/**`, `*.html`,
and exact-path rules the dir-level probe misses; `--no-index` so an already-tracked
artifact still honors a later ignore rule), emit local-open guidance only —
never a link that 404s.

## 5. PR lens — read-only review instrument

Derived from the **diff** (`git diff --stat base...head`, file-level churn), never
from commit messages; verified against the spec's R-ID export before publishing.
No annotate loop, ever — review conversation belongs to the code host.

1. Masthead: PR number + title, branch → base line, dials (diff `+n −n`, files,
   R-ID coverage, tasks done, **human-review lines** — added lines minus generated/
   mechanical churn, with a one-line footnote explaining the subtraction).
2. **Sticky review-progress bar**: checked-count over total of the §5.4 checklist,
   amber fill bar, reset button; persists via try-wrapped localStorage.
3. The 90-second read: `.tldr` + a callout naming the 2–3 load-bearing claims to verify.
4. **Churn map** — `<details class="cgroup">` groups ordered by review intent:
   canonical changes (the thing to actually review) → behavior-visible plumbing →
   **generated mirrors** (tagged `generated`; instruct "verify the generator ran
   clean, don't line-review") → docs/release surfaces → mechanical (version
   manifests) → process state. Each summary row: name + intent micro-caption,
   `+n −n` colored stat, file count, proportional churn bar (gray for generated).
5. **R-ID → evidence table**: every R-ID, abridged criterion, owning tasks, commit
   shas in cyan. **A mismatch between the diff and the R-ID export renders as a
   visibly flagged row** (red R-ID cell + a `mismatch` chip and one-line reason) —
   warn-in-artifact; never block, never silently drop the row.
6. **Where-to-look checklist**: 6–10 checkbox cards, each naming a file/seam and the
   question the reviewer must answer there. Checked cards strike through and turn
   the border green; state persists locally.
7. **Risk register**: cards rated high/med/low by accent color — what could bite later.
8. Footer: render-lens sentence + staleness stamp (PR variant, §1.5).

## 6. DAG discipline (the top rendering risk)

Hand-typed SVG coordinates are BANNED. They desync from content on the first edit
and are unmaintainable by regeneration. The mandated pattern:

- **Layout**: a layered CSS grid — one column per dependency depth (L0, L1, …),
  nodes as bordered divs stacked per column (`.dagcol` flex columns inside a
  `.daggrid`), each node carrying `id`, `data-deps` (comma-separated ids) and
  `data-rids`. Depth = longest path from a root; compute it from the dependency
  edges, don't eyeball it.
- **Edges**: an absolutely positioned `<svg id="edges">` underlay sized to the grid,
  paths drawn by a small inlined deterministic script that READS NODE POSITIONS FROM
  THE DOM at load (`getBoundingClientRect`), drawing cubic curves right-edge →
  left-edge; redraw on `resize`. Critical-path edges get the `crit` class (amber,
  thicker). Worked example — reuse this verbatim shape:

```html
<script>
(function () {
  var svg = document.getElementById('edges');
  var wrap = svg.parentElement;
  var CRIT = { 'n1>n2': 1, 'n2>n3': 1 };           // edge keys on the critical path
  function draw() {
    var grid = document.getElementById('dag');
    var w = Math.max(grid.scrollWidth, wrap.clientWidth), h = grid.scrollHeight + 26;
    svg.setAttribute('width', w); svg.setAttribute('height', h);
    svg.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
    svg.innerHTML = '';
    var wb = wrap.getBoundingClientRect();
    document.querySelectorAll('#dag .node').forEach(function (n) {
      (n.dataset.deps || '').split(',').filter(Boolean).forEach(function (d) {
        var a = document.getElementById(d).getBoundingClientRect(), b = n.getBoundingClientRect();
        var x1 = a.right - wb.left + wrap.scrollLeft, y1 = a.top + a.height / 2 - wb.top;
        var x2 = b.left - wb.left + wrap.scrollLeft, y2 = b.top + b.height / 2 - wb.top;
        var mx = (x1 + x2) / 2;
        var p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        p.setAttribute('d', 'M' + x1 + ',' + y1 + ' C' + mx + ',' + y1 + ' ' + mx + ',' + y2 + ' ' + x2 + ',' + y2);
        if (CRIT[d + '>' + n.id]) p.setAttribute('class', 'crit');
        svg.appendChild(p);
      });
    });
  }
  window.addEventListener('resize', draw);
  requestAnimationFrame(draw);
})();
</script>
```

- **Legend** under the graph: critical-path swatch + spelled-out path
  (`.1 → .2 → … (n deep)`), dependency swatch, parallel-lane note.
- **Scale limit**: above ~20 nodes, collapse to lane/group rendering — one node per
  group/phase with a count badge, expandable `<details>` listing members — rather
  than a hairball. Never render >20 individual nodes.
- The graph container is horizontally scrollable on screen (`overflow-x: auto`) and
  `overflow: visible` in print.

## 7. Lavish integration (optional, never required)

`lavish-axi` is a detect-on-PATH companion: it serves an artifact in a browser
session where humans annotate; annotations queue globally and an agent session
drains them as markdown-source edits, then regenerates the lens.

- **Detect**: `command -v lavish-axi` — absent ⇒ plain artifact, zero mention of
  Lavish in output, never an error, never an install attempt.
- **Open (interactive sessions only)**: `lavish-axi <absolute-artifact-path>` opens
  the session; poll for feedback in the background via the `lavish-axi poll` CLI.
  Feedback is **pull-only and session-spanning**: it lives in `~/.lavish-axi/state.json`,
  survives agent death, and any later session may drain it.
- **Stable-path rule**: sessions key on the ABSOLUTE artifact path — another reason
  paths are fixed (§1.3). Different worktrees = different absolute paths = different
  sessions (documented, accepted).
- **Apply loop**: each drained annotation maps to an edit of the markdown source of
  truth (never the HTML), then the lens regenerates at the same path.
- **Conversational regen**: when a user asks "regenerate the artifact for <spec-id>"
  (after hand edits, an interview, drained annotations), reload this file, re-read
  the spec + flowctl state, regenerate at the fixed path, and re-run §8.
- **Autonomous contexts generate only**: pilot/Ralph/autonomous runs may write
  artifacts but NEVER open a session and NEVER poll — never block on a human. At
  most a one-line note that a session has pending prompts.
- **Idle-stop is invisible**: the server idle-stops (~30 min); the artifact still
  renders as a static page. Reopening resumes the session.

## 8. Pre-publish checklist (self-checkable — run every generation)

- [ ] Self-check grep (§2) prints `OK: self-contained` — zero loaded external resources
- [ ] Opens correctly from `file://` (no behavior depends on a server or network)
- [ ] Prints clean: light theme, sticky chrome hidden, sections unbroken, A4 (§1.7)
- [ ] Footer carries "Render lens, not record.", the source path, and the staleness
      stamp with real values (spec `updated_at` / head sha, short commit, render date)
- [ ] Every `<a href>` resolves: repo/tracker/PR links are absolute URLs; file links
      follow the ignore-status rule (§4) — no blob link that 404s
- [ ] The source spec markdown contains EXACTLY ONE `<!-- flow-next:artifact-link -->`
      line (`grep -c 'flow-next:artifact-link' <spec.md>` == 1) — spec lens only
- [ ] DAG (when present): zero hand-typed edge coordinates — edges come from the
      DOM-measuring script; ≤20 individual nodes or collapsed lanes
- [ ] Palette and font stacks match §3.1 verbatim; nothing from the §3.5 forbidden list
- [ ] localStorage accesses are try-wrapped; page fully readable with it blocked
- [ ] Output path is exactly `.flow/artifacts/<spec-id>/spec.html` or `…/pr.html`
