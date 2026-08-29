# Doctor and proof standards

Shared by seed and maintain. A cold agent reads this before the first drive.

---

## Doctor

One read-only check answering **is this instance worth driving**. It does not click, type, or mutate. It observes.

### What it checks

| Check | Passes when |
|-------|-------------|
| Right build / version | The process this run started is the checkout under test (the binary or bundle this worktree built, the matching version string / commit if the app exposes one). |
| Port owned by this run | The listening port (or socket, or CLI pid) is the one this run bound. The owner pid/container/compose project is in this run's notes. |
| Auth valid | The disposable profile is signed in as the documented user, or the scenario is the public unauthenticated path. Credentials are never guessed and never committed. |

All three must pass before a drive. One failure is a stop, not a hope.

### When it runs

- Before the first drive of the run.
- On each fresh session (a new chat, a resumed host, a driver reconnect).
- After any failed drive, before the next attempt.

Skipping a required Doctor run has broken this.

### Ownership

**Never drive an instance this run did not start.** Doctor names the owner from this run's notes (pid, container id, compose project, bound port, profile path). An instance with no matching note is not this run's.

**Never kill by process name.** Kill what this run started: the recorded pid, the compose project this run created, the container id this run launched. `pkill <app>` / kill-by-name is forbidden even for this repo's own wreckage.

### Orphaned port (crashed prior run)

A port (or socket) is owned by a process this run did not start. Doctor reports the port, the foreign pid if known, and stops.

The run ends `BLOCKED` with the reclaim instruction for the human. The kill-by-name ban holds. Reclaim is left to the human. The next invocation re-enters fresh; there is no resume state.

### Concurrent runs

Each run's disposable profile and port (the index's baseline preconditions) is the isolation mechanism.

Where the app **can** run twice: bind a free port, use a fresh profile, proceed. Doctor's owned-port check passes because this run owns its listener.

Where the app **cannot** run twice: Doctor's owned-port check fails (the only listener belongs to someone else). The second run ends `BLOCKED`. Never a shared drive. Never "just attach, the UI is already up."

### Wedged UI on a healthy process

Doctor sees a live process, right build, owned port, valid auth - and the UI is stuck (spinner, blank shell, modal that never dismisses). Doctor cannot see a wedge from process health alone.

Reset to a known state or relaunch rather than hoping. Record the reset in the run notes. Drive only after Doctor runs again on the recovered instance.

---

## Proof standards

A landed route has been driven once against the live instance. Narration is not proof. A screenshot of the final screen alone is not proof.

### Capture action and resulting state

Record the **user action** (the click, the command, the URL typed) **and** the **resulting state** (heading present, row gone, prompt returned, file written). The pair is the proof. A final-screen capture with no action record cannot be replayed and does not land.

### Side effects beside the visible

Verify the effect next to what the UI or CLI shows:

- Write path: server / DB row, API response, or file on disk confirming the persisted state. Do not trust an optimistic render.
- CLI: exit code plus stdout/stderr, not the happy banner alone.
- Delete path: the thing is gone on a reload, not only removed from the current view.

A green-looking DOM or a zero exit while the request returned 500 (or the file was not written) is a failed proof.

### Real user paths

Exercise the path a user takes: the documented URL, the sidebar label, the CLI the README tells them to run.

Never a test-only endpoint, a hidden debug view, a `?e2e=1` bypass, or an admin RPC the product UI does not expose. A route proven only that way does not land.

### Unreachable is reported, never substituted

When a route cannot be reached, report:

- the **attempted route** (the entry point that was driven)
- the **unmet precondition** (auth, seed data, feature flag, missing driver rung)

Never record it as verified-via-another-path. Reaching a similar screen by a shortcut does not prove the documented user entry point. An unstated prerequisite is itself drift (seed: name it in the failure list; maintain: treat it as map drift).

A feature is `verified-unreachable` only with that pair. Maintain owns that label; seed simply does not land the route and names the failure.

### Cleanup never eats evidence

Cleanup removes **instances and scratch state this run started** (the process, the disposable profile, temp data dirs, verification scaffolding).

Cleanup **never** removes evidence. Screenshots, console dumps, CLI transcripts, API traces stay at their named paths under `.flow/tmp/features-<run-id>/` (gitignored; referenced by path).

After teardown, verify each evidence file still exists at the path recorded in the run notes. A cleanup that eats the proof fails the step: the route does not land, and the verdict is not `SEEDED` for that feature.

Evidence is not the committed map. The map is `.flow/features/**`. Run notes, scratch, and evidence stay out of any later maintain PR.
