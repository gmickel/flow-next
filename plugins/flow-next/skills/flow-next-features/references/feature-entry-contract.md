# Feature-entry contract

This page is the shape a cold agent seeds and drives from. The map lives at `.flow/features/`. The index is `.flow/features/README.md`. One file per user-facing feature sits beside it. No other paths belong in this contract.

Consumers (QA, drive) discover the map by existence check only. They select a feature deterministically by its `**Surface:**` identifier plus sub-feature IDs.

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

## Worked example

A small notes app. Invented. The file below is a complete feature file a seed run would write after one live drive of each listed route.

```markdown
# Notes list

The notes list is the home surface: a signed-in user sees every note they own, newest first, and can open one or start a new note.

**Surface:** web

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
