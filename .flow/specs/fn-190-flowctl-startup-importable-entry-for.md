# fn-190-flowctl-startup-importable-entry-for flowctl startup: importable entry for the main CLI path, one verdict→status site

## Goal & Context
<!-- scope: business -->

Every flowctl invocation pays a fixed tax before it does any work, and the pipeline invokes flowctl constantly — per worker task, per pilot tick, per gate probe, and hundreds of times inside the unit suite. Measured on this machine class 2026-08-13 against current main: running flowctl as a script costs **249ms**, importing the same module from cached bytecode costs **109ms**, and a bare interpreter is **16ms**. The gap is not imports (those total ~25ms); it is CPython re-parsing and re-compiling ~51.7k lines on every single call, because a file run as `python3 file.py` is never bytecode-cached — only imported modules get `__pycache__`.

**Size the win honestly, because it is small.** The saving is fixed at roughly 0.16s per call. An agent run making hundreds of flowctl calls recovers tens of seconds against a multi-hour run — immaterial. An interactive command is 0.16s faster — imperceptible. A pre-implementation spike also measured what it does NOT buy: routing spawn-heavy unit-test files through the entry made those files 35% faster, and moved full-suite wall not at all (573.96s before, 598.59s after, on a tree whose own run-to-run variance is +-5%). The wall-setting test files are slow for unrelated reasons.

So this is a **hygiene and cost** change on a hot path, not a speed feature: the mechanism is correct, the behavior is byte-identical, and the tax simply stops being paid. No agent-speed, gate-speed, or end-to-end claim belongs in this spec, its tasks, or its changelog entry. It ships alongside the verdict-map cleanup because both edit the same module; neither alone would justify a release.

Riding along is a small correctness-shaped cleanup in the same file: the verdict→status mapping exists at three Python sites today. All three are currently byte-identical, which is exactly when consolidation is free — it is a deletion, not a new abstraction, and it removes the drift class that cost review rounds when a fix landed on one site and missed a sibling.

## Architecture & Data Models
<!-- scope: technical -->

**Three entry shapes, one added.** The bundled wrapper already selects between two entries: the main CLI entry, and a manifest-authenticated static-help fast path used for bare `usage` / `--help`. This spec adds a third: a thin entry module that

1. contains `sys.path` to its own directory only — never the working directory, never the consumer's repo, so no consumer module can shadow a flowctl import;
2. imports the flowctl module, which is what makes CPython write and reuse its bytecode cache;
3. normalizes `argv[0]` to the flowctl module's own path, so `argparse` derives an unchanged program name;
4. calls the module's `main()` and lets `SystemExit` propagate untouched.

**The authenticated fast path is untouched.** Its deliberate in-memory-exec, never-read-a-pyc design exists because a runtime-written pyc can validate a source hash without proving the executable payload came from that source. That rationale is scoped to the authenticated path — the main CLI path never made a hash-authentication claim; it simply runs the source. After this change it relies on CPython's standard pyc invalidation (source mtime and size embedded in the pyc header), the same trust model every imported module in this repository already uses, including the tracker package.

**The launcher is an artifact graph, not a file.** Launcher text exists on disk in several distribution copies AND as constants embedded in the flowctl module, because `init` restamps launchers from those constants — so a stale constant silently reverts a shipped launcher on the consumer's next init. Any change to the invocation shape updates the whole graph in one change, and the new entry must ride every channel that carries the flowctl module today. The parity tests define the graph; treat them as the inventory, not as an afterthought.

**One mapping site.** The canonical helper already exists; the two inline duplicates route through it and are deleted. Two non-Python analogues stay deliberately independent and get documented at that single site: a generated harness script's inverse status→verdict mapping (different language, different direction) and a hook's verdict validation enum (a hook must not import CLI internals).

## API Contracts
<!-- scope: technical -->

The CLI surface is byte-identical before and after. Specifically, for the same argv:

- same program name in usage and error text;
- same stdout, same stderr, same exit code — including argparse's own error path and every documented non-zero code;
- same JSON shapes and same marker strings;
- `main()` takes no arguments and communicates exclusively through `SystemExit`.

Entry-shape contract for the wrapper: an entry is a file path the wrapper `exec`s with the resolved interpreter, receiving the original argv tail unchanged.

## Edge Cases & Constraints
<!-- scope: technical -->

- **Unwritable or read-only install directory:** CPython silently skips the pyc write. flowctl works exactly as today, just without the speedup. No error surface, no warning — degradation is the correct behavior, not a condition to report.
- **Stale bytecode:** CPython's own source mtime/size invalidation handles it. No hash, no manifest, no custom staleness logic on this path.
- **Module shadowing:** `sys.path` gains the entry's own directory and nothing else.
- **Windows:** the `.cmd` twin changes in lockstep. Interpreter-probe semantics are unchanged, including skipping the Store alias stub and rejecting too-old interpreters with an actionable message.
- **Committed dogfood copy:** importing writes a `__pycache__` directory beside a tracked copy. It must be ignored, and a warm run must leave the working tree clean — a dirty tree here would silently defeat the green-receipt cleanliness probe.
- **Partially upgraded install:** a channel that shipped without the new entry must fail with a message naming the missing entry and the remedy, never a traceback.
- **Verdict-map unification is conditional:** the three sites must be verified equivalent *including* unknown-verdict fallback semantics before any deletion. Divergence is a finding to surface, not something to unify — unifying divergent behavior would be a behavior change wearing a refactor's clothes.
- **Frozen prompt text:** no embedded prompt constant moves; the prompt-pin hashes stay identical.
- Standing criteria in `.flow/criteria.md` apply as written and are not restated here.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** The main CLI path executes from cached bytecode, and warm per-invocation startup drops by **at least 0.12s** on the same machine class, measured at BOTH boundaries — direct module invocation and through the bundled wrapper — with method and before/after numbers recorded in the task summary and the PR. The **saving is the contract; the ratio is reported, never gated** (a pre-implementation spike measured 1.4x-3.3x for the same fixed saving, because the ratio only reflects how much real work the command does around it). Errors: unwritable directory → pyc write skipped, command succeeds unaccelerated; stale pyc → standard CPython invalidation; a distribution channel missing the entry → wrapper falls back to the source script (today's behavior, no speedup), and an orphaned entry with no source beside it exits non-zero with a message naming the expected path and remedy, never a traceback.
- **R2:** The CLI surface is unchanged. For at least a non-root subcommand's `--help` and a deliberate argparse error, stdout, stderr, and exit code are identical to invoking the module directly, program name included; JSON shapes and marker strings are untouched. Errors: no error surface beyond R1.
- **R3:** The manifest-authenticated static-help path keeps its in-memory-exec design, and the recorded bytecode-cache rejection is **rewritten** (not appended to) so it scopes that rationale to the authenticated path and states the main path's standard-invalidation trust model. Errors: no error surface.
- **R4:** The launcher artifact graph stays coherent: on-disk launcher copies remain byte-identical to the embedded constants, `init` restamping reproduces the shipped launcher, every distribution channel that carries the flowctl module also carries the new entry, and an installed-layout smoke invokes a **non-static** subcommand through the wrapper (proving the entry actually shipped, which bare `usage` cannot prove because it takes the authenticated path). Errors: stale embedded constant → restamp reverts the launcher, caught by the launcher parity tests rather than in the field.
- **R5:** Exactly one Python verdict→status mapping site remains; the former inline duplicates route through it; the harness-script inverse mapping and the hook validation enum are documented at that site as deliberate independents with their reason. Errors: any pre-unification divergence in fallback semantics is surfaced for decision and left unmerged.
- **R6:** New `__pycache__` locations are git-ignored and a warm run leaves the working tree clean; full suite, lint, and the OS smoke matrix are green; prompt-pin hashes unchanged. Errors: no error surface beyond the gate itself.

## Boundaries
<!-- scope: business -->

- No package extraction and no module reorganization — that is its own spec, sequenced after this one.
- No language port. The measured alternative (a compiled single binary) is a distribution and release-pipeline decision, not a refactor; recorded in Decision Context, deliberately not scoped here.
- No change to the authenticated fast path's trust model, and no removal of the interpreter probe.
- No new config keys, no new subcommands, no changes to gate classification or any other taxonomy.
- No agent-speed or end-to-end wall-clock claim anywhere in the change, the CHANGELOG, or the docs — the measured claim is per-invocation startup and its effect on the local gate.
- **The wrapper's own floor is out of scope.** Measured 2026-08-13: shell spawn ~60ms plus the interpreter probe ~33ms ≈ 93ms, which after this change is roughly a third of a warm read-only call. Recorded because it bounds the achievable ratio and explains why the contract is an absolute saving; not addressed here, and the probe is not weakened to chase it (it exists so a Store alias stub or a too-old interpreter fails with a real message).

## Decision Context
<!-- scope: both -->

This spec is the low-risk half of an earlier combined spec, split 2026-08-13 so the measured startup win can land without waiting on a package extraction whose justification is different (parity and navigation) and whose risk is higher. Its research — the artifact graph, the authenticated-path scoping, the program-name parity trap — survives the split and is carried in the task files.

**Why an entry file rather than an inline interpreter one-liner in each launcher:** one quoting-safe implementation instead of two, and a single place to normalize the program name. The one-liner shape also reports its program name as the interpreter flag, which is a frozen-surface diff.

**Why not fix this by making the file smaller:** the compile cost is paid per invocation on whatever the entry script contains, so extracting a subsystem does not reduce it — an extraction of roughly a twentieth of the file would leave the tax essentially intact. Modularity and startup are independent problems with independent fixes.

**Why not port to a compiled binary now:** measured 2026-08-13, a compiled single-file build of the same shape starts in ~14ms and would delete the interpreter probe entirely, but each platform artifact is 62-94MB (23-36MB compressed) with size set by the embedded runtime rather than by our code. That means release-asset distribution plus a per-release build, sign, and publish pipeline, and — because a fresh implementation cannot inherit the white-box half of the current suite — a differential-testing harness before "no behavior change" would mean anything. Worth revisiting only as a deliberate product decision about install story, not as an implementation detail of this spec.

**Pre-implementation spike, 2026-08-13 (main @ 9e111db4) — this spec's numbers are measured, not projected.** A throwaway worktree built the entry and routed the shell wrappers through it. Results: a differential parity sweep over 63 cases (root, all 52 subcommand `--help`, and 9 error/runtime paths) came back byte-identical on stdout, stderr, and exit code; the full suite stayed green at 4,527 tests with the wrapper live; stale-pyc invalidation behaved correctly after touching the source; an orphaned entry with no source beside it exited 1 with an actionable message and no traceback. Timings — direct invocation 0.510s → 0.247s on a write command and 0.217s → 0.067s on `--help`; through the wrapper 0.434s → 0.266s on a read-only JSON command; one representative test dropped 1.586s → 0.922s once it resolved flowctl through the entry.

Two things the spike changed in this spec, and the reason it was worth running instead of a review: **the original ">=2x" acceptance gate was unachievable through the wrapper** (the fixed ~0.16s saving is diluted by the wrapper's own ~93ms floor and by whatever real work the command does), so R1 now contracts on the absolute saving; and **the suite would not have collected the win at all** without R7, because tests resolve flowctl through their own per-file constant rather than through the wrapper. A plan review reading the same design would have had no way to notice either.

**Why the verdict-map cleanup rides along:** it edits the same file as the launcher constants, so pairing them avoids two serialized passes over one file; and its precondition (all three sites byte-identical) is satisfied today, which is not guaranteed to stay true.
