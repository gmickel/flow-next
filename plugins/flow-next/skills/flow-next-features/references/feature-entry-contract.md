# Feature-entry contract

This page is the shape a cold agent seeds and drives from. The map lives at `.flow/features/`. The index is `.flow/features/README.md`. One file per user-facing feature sits beside it. No other paths belong in this contract.

Consumers (QA, drive, flow's bug intake and the other live-app stages below) discover the map by existence check only. They select a feature deterministically by its `**Surface:**` identifier plus sub-feature IDs.

The map records how a user gets there. Specs still say what to prove this time. Live captured evidence is still the only proof.

---

## Per-feature file

Every feature file opens with:

1. An H1 title (the feature a user would name).
2. One paragraph of user-visible behavior. No implementation details, no source paths.
3. A required one-line surface identifier, exactly this form, directly under that paragraph:

```text
**Surface:** <id>
```

`<id>` is a short deterministic token such as `web` or `cli`. The index groups entries by it. Consumers select by surface + sub-feature IDs. Enumeration is observation, not a question for the user.

4. An optional provenance line as the first non-blank line after the surface line:

```text
**Last proven:** <YYYY-MM-DD> at <short commit>
```

The date is the day (UTC) a live drive proved this file's route, and the commit is `git rev-parse --short HEAD` at that drive. Seed, maintain and work's feature-map update step write or refresh it when their live drive proves the route. A file without the line reads as never proven. A malformed line (any other shape or position, or a second copy) reads as absent, and maintain reports it. `flowctl features status --json` parses the line and measures each file's age. The line names no source paths.

Then **exactly four H2s, in this order, no others**:

| H2 | Owns |
|----|------|
| `## Sub-features` | Short IDs, one line each (`notes.list` - see owned notes, newest first). IDs are stable handles consumers cite. |
| `## How to get to it (user POV)` | Every user entry point. Fresh session and already-signed-in. URLs, sidebar labels, CLI invocations a user would type. |
| `## Driving it` | Starts with `Preconditions:`, then labeled bullets pairing each user action with an exact command and its observable result. |
| `## Gotchas` | Traps that waste or invalidate a run (wrong session, empty-state mistaken for a load failure, coordinate clicks that break on layout). |

**Driving it** rules:

- `Preconditions:` is the first body line of that section (launch target, signed-in user, seed data, disposable profile/port).
- Each bullet names the **user action**, the **literal command** (stable handle: role, accessible name, prompt string - never a pixel coordinate), and the **observable result**.
- Commands are treated as literal.
- No implementation details.

**Gotchas** name the failure mode and the recovery. A gotcha that restates a precondition belongs under `Preconditions:` instead.

---

## Index README

`.flow/features/README.md` is the operating-rules page plus the grouped inventory. A cold agent reads it first.

Required sections, in this order:

1. **Baseline preconditions** - launch target, disposable data/profile, seed state, isolation (can two instances run side by side? ports, data dirs, profiles; when they cannot, a run refuses to double-drive a shared instance).
2. **Driving conventions** - stable handles (roles, accessible names, prompt strings) over coordinates; commands treated as literal.
3. **Proof standards** - capture the user action and the resulting state, not just the final screen; verify side effects beside what is visible; exercise real user paths, never test-only endpoints; report an unreachable path with the attempted route and unmet precondition, never as verified-via-another-path. Full text: [doctor-and-proof.md](doctor-and-proof.md).
4. **Feature-entry contract** - pointer at this page, so a cold agent does not re-derive the four-H2 shape.
5. **Surfaces** - entries grouped by `**Surface:**` identifier. Each row: feature file, H1 title, sub-feature IDs. Consumers select by surface + sub-feature ID.

Partial seed: the index names features that were identified but failed to prove, so the next seed or maintain pass can retry them. Failed routes do not get a feature file.

---

## Writers and drift notes

Two writers exist. `/flow-next:features` seeds and maintains the whole map, and work's update step (`flow-next-work/references/feature-map-update.md`) edits only the entries its own change altered. Every other stage that drives from the map (QA, drive, bug intake and the live-app stages below) is a reader and never edits the map mid-run.

A reader that finds a mapped route no longer matching the live app files a drift note, then continues with live route discovery:

- Identity: knowledge track, category `workflow`, tag `feature-map-drift`, title exactly `drift: <surface>/<feature-slug> <sub-feature-id>`. The title is the dedup key, so a changed spelling files a duplicate.
- Write: `flowctl memory upsert` with that title, body two lines, `Expected: <mapped route or command>` and `Observed: <what the live app did>`. When upsert reports `"action": "updated"` and `flowctl memory read <entry_id> --json` shows `frontmatter.status` as `stale`, follow it with `flowctl memory mark-fresh <entry_id>` (a hardened or active note keeps its status): the same route drifting again reopens a note an earlier pass retired, because upsert keeps a stale note stale. QA's fence in `flow-next-qa/references/drift-notes.md` is the reference invocation. A failed upsert or mark-fresh never aborts the run.
- Memory disabled: record Expected/Observed in the stage's run notes instead.

**Retirement.** A maintain pass or a work update that proves the route a note names (corrected or not) marks that note stale, so an open count means open drift: `flowctl memory mark-stale <entry-id> --reason "route re-proven <date> at <short commit>"`. The note list comes from `flowctl features status --json` (`open_drift`: id, title, path). A note whose file already has uncommitted changes (`git status --porcelain -- <path>` non-empty) is left open, so a later restore or staging step never touches edits this run did not make. Memory disabled: nothing is marked.

## Live-app stages

Every stage about to drive a running app reads the map this way: flow's measured-slowness baseline, work's post-change measurement, the defect route's live proof on base and head, QA, and any live check a PR reports. Stages with no running app (questions, refactors, capture, plan, refine) never read the map, and a stage that cannot start the app reads nothing for navigation. Flow's bug intake keeps its own gate ([defect-intake.md](../../flow-next-flow/references/defect-intake.md)).

1. **Check existence.** No `.flow/features/`: drive as before.
2. **Match the target.** Read the index, match the target to its Surfaces row, and read only that feature file, even when the target names its page: `Driving it` and `Gotchas` carry controls that misbehave and state the accessibility tree misreports. Several candidates: read them most specific first and use the one that reaches the target. None: `unmapped`, live discovery. Never read the whole map.
3. **Drive.** Name the file and sub-feature, or `unmapped`, to `flow-next:flow-next-drive`; a stale route gets a drift note as above.

---

## Worked example

A small notes app. Invented. The file below is a complete feature file a seed run would write after one live drive of each listed route.

```markdown
# Notes list

The notes list is the home surface: a signed-in user sees every note they own, newest first, and can open one or start a new note.

**Surface:** web
**Last proven:** 2026-09-20 at 4f2c9ab

## Sub-features

- `notes.list` - see owned notes, newest first
- `notes.open` - open a note from the list
- `notes.new` - start a new note from the empty-state or header action

## How to get to it (user POV)

- Fresh session: open the app, land on `/login`, sign in, arrive at `/notes`.
- Already signed in: open `/notes` directly, or click Notes in the sidebar (accessible name "Notes").

## Driving it

Preconditions:
- Disposable profile on this run's port; a signed-in user. Empty list is a valid state.

- Open the notes list
  - Command: navigate to `/notes`
  - Observable: heading "Notes" and either a list of note titles or the empty-state copy "No notes yet"

- Open the first note (when the list is non-empty)
  - Command: click the first note row (accessible name = that note's title)
  - Observable: the editor heading matches the row title

- Start a new note
  - Command: click the button whose accessible name is "New note"
  - Observable: the editor opens with an untitled document and a focused title field

## Gotchas

- The list is session-scoped. A cookie from another run shows the wrong user's notes. Use the disposable profile from the index.
- Empty list is a valid state, not a load failure. Confirm the empty-state copy before retrying login.
- Note titles are the accessible names. Do not click by nth-child or coordinates; a sort change invalidates those.
```

---

## Index shape (worked)

```markdown
# Feature map

Committed user-POV drive knowledge for this repo. How a user reaches each feature, how an agent drives it, and which traps waste a run.

## Baseline preconditions

- Launch target: `http://127.0.0.1:<port>` on a port this run owns (default `8787` if free).
- Start command: `npm run dev -- --port <port> --host 127.0.0.1`.
- Disposable profile: a fresh browser profile / data dir per run. Never the operator's daily profile.
- Seed state: signed-in as the documented dev user, or the public empty-list path.
- Isolation: two instances can run side by side on different ports and profiles. Do not reuse a port this run did not bind.

## Driving conventions

- Stable handles: roles, accessible names, prompt strings. Never pixel coordinates.
- Commands are literal. Copy them as written in the feature file.
- Re-snapshot after every navigation, click, or submit. Refs go stale.

## Proof standards

- Capture the user action and the resulting state, not just the final screen.
- Verify side effects beside what is visible (network, files, CLI exit).
- Real user paths only. Never a test-only endpoint.
- Unreachable: report the attempted route and the unmet precondition. Never verified-via-another-path.

## Feature-entry contract

Each feature file follows the four-H2 contract (Sub-features / How to get to it (user POV) / Driving it / Gotchas) plus the required `**Surface:**` line. Consumers select by surface + sub-feature IDs.

## Surfaces

### web

| File | Feature | Sub-features |
|------|---------|--------------|
| `notes-list.md` | Notes list | `notes.list`, `notes.open`, `notes.new` |

Identified, not yet proven (retry next pass): -

### cli

No CLI features seeded this pass.
```
