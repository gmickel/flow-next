# Frozen test inputs — audit suite (3 stores, FROZEN, synthetic — scrubbed)

audit classifies each `.flow/memory/` entry Keep / Update / Consolidate / Replace / Delete (autofix
ambiguity → `mark-stale`). audit's Phase-1 INVESTIGATES the codebase, then Phase-2 JUDGES the outcome.
The eval must isolate the **judgment** — so each store's frozen "investigation result" is presented as
**RAW FACTS ONLY** (grep hits, symbol presence, git-log lines, file trees, dates, code snippets) with
**ZERO verdict adjectives** (never "still accurate", "problem gone", "redundant", "distinct value") — the
run must DERIVE the verdict from the facts. Run = `mode:autofix` EMISSION at **sonnet** (emit per-entry
verdict + reason; don't execute). Synthetic; no real PII.

Answer keys are for SCORING only — NOT shown to the run. Where the taxonomy genuinely admits >1 answer,
the key lists the accept-set (per the fn-84.5 fable review: don't force one answer where the prose supports two).

---

## Store M1 — mixed. 7 entries.

**Frozen investigation facts (raw — no verdicts):**
- `grep -n 'def cmd_ready' plugins/flow-next/scripts/flowctl.py` → `def cmd_ready(...)`; its body contains `ready = [t for t in tasks if all(dep_done(d) for d in t.depends_on)]`.
- `grep -rn '_parse_frontmatter' plugins/` → (no matches). `grep -n 'def _read_yaml_header' plugins/flow-next/scripts/flowctl.py` → `def _read_yaml_header(text):  # parses the entry's YAML frontmatter, handles anchors`.
- `ls plugins/flow-next/skills/flow-next-legacy-tui/` → `No such file or directory`. `grep -rn 'tui_bridge\|legacy-tui' .` → (no matches). `git log --oneline --diff-filter=D -- plugins/flow-next/skills/flow-next-legacy-tui/` → `a1b2c3d chore: remove legacy-tui skill (superseded by flow-next-tui) [v2.0.0]`.
- `grep -n 'RP_TIMEOUT\|range(3)' plugins/flow-next/scripts/flowctl.py` → present, unchanged (rp retry code current).
- `grep -n 'codex' CLAUDE.md` → `Do NOT spawn codex/copilot/other LLMs via subprocess from inside flowctl … The host agent is already an LLM running the skill.` `ls .flow/memory/knowledge/decisions/host-agent-does-the-judgment*.md` → 1 file (a decision record stating flowctl stays deterministic; the host agent judges).
- M1-g's frontmatter (shown below) is anchored/nested multi-line YAML. `grep -rn '<the module M1-g names>' plugins/` → 2 partial matches in unrelated files; the referenced module's current identity is not resolvable from these hits.

**Entries (id — body):**
- **M1-a** `bug/build-errors/ready-gate-depends-on-filter` — "cmd_ready must filter tasks by `depends_on` before returning the ready set." `module: flowctl`.
- **M1-b** `bug/integration/frontmatter-parse-helper` — "Read an entry's YAML via `_parse_frontmatter()` — it handles anchors correctly."
- **M1-c** `bug/integration/legacy-tui-socket-handshake` — "The legacy-tui `tui_bridge.py` socket handshake needs a 200ms retry or the TUI drops the first frame." `module: flow-next-legacy-tui`.
- **M1-d** `bug/integration/skill-bash-var-death` — "Shell vars die across tool-call boundaries. Example: `$LEAF` set in one bash block is empty in the next. General principle: never assume env state persists between tool calls."
- **M1-e** `bug/integration/bash-block-redeclare-flowctl` — "Re-define `$FLOWCTL` at the top of every skill bash block. **Fix pattern:** for a value you must carry across blocks (e.g. a computed base commit), persist it to `.flow/tmp/<name>` and re-read it in the next block."
- **M1-f** `knowledge/decisions/spawn-codex-for-judgment` — "Decision: spawn a local `codex exec` from inside flowctl to make memory-classification judgments." `decision_status: accepted`.
- **M1-g** `bug/runtime-errors/unclear-quirky-yaml-entry` — frontmatter: `refs: &a [x, *a]` (self-anchored) + a nested multi-line `notes:` block; body references a module whose identity the grep facts above do not resolve.

**ANSWER KEY (M1):** M1-a → **Keep** (the code fact shows cmd_ready still filters by depends_on = entry accurate).
M1-b → **Update** (`_parse_frontmatter` grep-gone but `_read_yaml_header` in the same file does the same job =
a rename; fix the reference — the recommendation/intent is unchanged). M1-c → **mark-stale** (CORRECTED from an earlier mis-key of Delete — the exact answer-key error the fn-84.5 'fable-review-evals-BEFORE-running' lesson targets). Facts show the legacy-tui code gone (grep-absent + git-log removal), BUT the git-log says 'superseded by **flow-next-tui**' → a successor TUI exists, so the socket-handshake PROBLEM DOMAIN may persist in the successor. Per audit's 'code gone but problem persists → Replace, not Delete' + no evidence on the successor's internals to write a trustworthy Replace → autofix routes to **mark-stale** (insufficient evidence). Delete requires the problem GONE, which 'superseded by' does not support. audit classified this correctly; the Delete key was mine to fix. NOTE: this leaves the suite without a hard clean-Delete case — a fixture-design gap to add next iteration (a feature cut with NO successor). M1-d + M1-e →
**Consolidate** (both about the same bash-var-death bug BUT each carries UNIQUE content — M1-d the `$LEAF`
example + general principle, M1-e the `.flow/tmp` persist-and-reload fix pattern; merging preserves both,
so **Delete-one would be content-lossy** and is wrong here; Keep-both leaves duplication). M1-f → **Replace**
/ supersede (the recommended action contradicts CLAUDE.md and a successor decision record exists). M1-g →
**mark-stale** (un-round-trippable YAML + unresolved module identity = genuine autofix ambiguity).

---

## Store M2 — CLEAN corpus (over-flag guard, finder-shape). 4 entries.

**Frozen investigation facts (raw):**
- `grep -n 'first:' plugins/flow-next/skills/flow-next-tracker-sync/references/linear-graphql.md` → every `nodes` connection carries an explicit `first:` (matches M2-a's guidance).
- `.github/workflows/*.yml` → the pytest step is `python -m pytest -p test_a -p test_b …` (explicit `-p` list, no `discover`) (matches M2-b).
- `grep -rn 'tracker.*drive\|projection' plugins/flow-next/skills/flow-next-tracker-sync/` → the code + docs implement projection; no path where the tracker sets flow state (matches M2-c).
- Windows: `where python3` → `…\WindowsApps\python3.exe` (the MS Store stub); flowctl's launcher probes `python3 -c "..."` rc before use (matches M2-d).

**Entries:** M2-a `bug/performance/linear-graphql-bound-connections` "explicit `first:` on every Linear `nodes` connection"; M2-b `bug/test-failures/ci-explicit-p-pattern` "new tests must be added to CI's `-p` list"; M2-c `knowledge/decisions/tracker-sync-projection-not-coordination` "tracker-sync is projection, not coordination"; M2-d `bug/build-errors/windows-python-stub-9009` "Windows `python3` = MS Store stub (9009); probe don't presence-check".

**ANSWER KEY (M2):** ALL 4 → **Keep** — for each, the raw code fact matches the entry's guidance (no drift,
no gone code). Any Delete/Replace/Consolidate/mark-stale on M2 = OVER-FLAG (a fabricated problem on healthy memory).

---

## Store M3 — STRESS: the facts genuinely underdetermine the surface impression. 4 entries.

The distractor and the fact POINT DIFFERENT WAYS — the run must weigh them, not read a stated conclusion.

**Frozen investigation facts (raw):**
- M3-a: entry dated `2025-11` (~8mo ago); body parenthetical "(back when we used the old ORM)". `grep -n` the export loop → `for row in rows:\n    detail = db.fetch(row.id)` (a per-item fetch inside the loop; no batch/`in (...)` query anywhere in that function). [distractor: age + 'old ORM'; fact: the N+1 code is present + unfixed.]
- M3-b: entry says "retry 3× with **2s FIXED backoff**; set `RP_TIMEOUT=30`". `grep -n` the retry code → `for i in range(3):\n    ...\n    time.sleep(2 ** i)` and `os.environ.get("RP_TIMEOUT")`. [fact: retry-3× ✓ and RP_TIMEOUT ✓ hold; the backoff is `2 ** i` = exponential, not the "2s fixed" the entry states.]
- M3-c1 / M3-c2: both concern flowctl's dual-copy. M3-c1 body = "INVARIANT: `scripts/flowctl` and `.flow/bin/flowctl` must stay byte-identical; edit both." M3-c2 body = "INCIDENT (2026-05): a ready-gate fix landed in `scripts/flowctl` only; `.flow/bin/flowctl` drifted and the gate misbehaved live. Root cause: forgot the dual-copy step. Prevention: add a `diff` check to the gate." `grep` confirms both files exist and are currently identical. [fact: both entries are accurate; they share the topic; M3-c1 is a standing rule, M3-c2 is a dated incident with root-cause + a prevention step not in c1.]

**ANSWER KEY (M3, with genuine-tension accept-sets):**
- M3-a → **Keep** — the N+1 code is present + unfixed, so the guidance still applies; surface age / 'old ORM'
  is not staleness. (Delete/stale here = over-flag failure.)
- M3-b → accept-set **{Update, mark-stale}** — the retry+timeout hold and only the backoff value drifted, so
  Update (fix the one value) is the primary reading; but the drifted item is solution content, so audit's
  Update↔Replace tension legitimately also permits **mark-stale** (ambiguity escape). **Fail = Replace, Delete,
  or Keep** (Keep leaves a now-wrong recommended value in place).
- M3-c1 + M3-c2 → accept-set **{Keep-both, content-preserving Consolidate}** — both are defensible (retrieval-
  value: distinct standing-rule vs debugged-incident → Keep-both; OR merge into one canonical that RETAINS the
  incident's root-cause + prevention). **Fail = Delete-one, or a Consolidate that drops c2's root-cause/prevention
  (content-lossy), or mark-stale.**
