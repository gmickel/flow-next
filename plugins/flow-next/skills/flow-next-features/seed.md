# /flow-next:features seed

Execute these phases in order. Each gates on the prior. Stop on a user-blocking error - never plow through with bad state, and never write a map against an undriven or broken base.

Autonomy refusal and `MODE=seed` are already resolved in [SKILL.md](SKILL.md). Feature file shape: [references/feature-entry-contract.md](references/feature-entry-contract.md). Doctor + proof: [references/doctor-and-proof.md](references/doctor-and-proof.md).

**Live driving consumes the drive skill by pointer.** Read [`plugins/flow-next/skills/flow-next-drive/SKILL.md`](../flow-next-drive/SKILL.md) (surface detection + universal flow + ladder) and the relevant rung reference under `plugins/flow-next/skills/flow-next-drive/references/`. **That prose stays there.** A copy of CDP / agent-browser / Computer-Use actuation detail written into this file has broken this. Execute the universal flow (`observe → snapshot fresh refs → act → verify → capture`) yourself. A transcript that "calls" flow-next-drive as if it were an API has broken this too.

Run notes and live evidence land under `.flow/tmp/features-<run-id>/` (gitignored, same per-run tmp convention QA uses), referenced by path, never inlined. The committed map is `.flow/features/` only.

---

## Phase 1: Interview the repo

**Goal:** answer five facts from the checkout. Ask only what cannot be observed.

| Fact | What it names | Where to look |
|------|---------------|---------------|
| Surface | web, cli, desktop, or none | README, package manifests, UI entrypoints, binary CLIs |
| Run command | how a user starts it | README, Makefile, `package.json` scripts, compose files |
| Drive mechanism | URL, CLI argv, window | documented dev URL, `--help`, launch target |
| Observable evidence | what a drive can capture | screenshots, CLI stdout, files written, HTTP traces |
| Isolation | can two instances run side by side | ports, data dirs, profiles; say so in the index when they cannot |

Read first. Grep/Glob second. Ask third, and only for a remaining unknown.

Ask **one question at a time** via `AskUserQuestion` (call `ToolSearch` with `select:AskUserQuestion` first if its schema is not loaded). On portable hosts without that tool, a plain-text numbered prompt with a final `Other - type your own answer` option. Never silently skip.

A repo with **no drivable user surface** (a pure library) ends `REFUSED` with the reason. Do not manufacture a map.

Multi-surface repos (web + CLI) seed **per-surface feature groups** under one index. Enumeration is observation, not a question. Every feature file will carry a `**Surface:**` identifier (`web`, `cli`, ...).

### Done when

- The five facts are recorded, each tagged `observed` or `asked`.
- A library with no surface has already terminated `REFUSED`.
- Nothing was asked that a file in the repo already answers.

---

## Phase 2: Checkout health and Doctor

**Goal:** a live instance this run started, worth driving.

A checkout that does not build or start as-is: **fix that first or report it precisely** and end `REFUSED`. Never write a map against a broken base (it teaches wrong steps). A genuinely irrelevant missing asset may be created as clearly-marked verification scaffolding and removed in cleanup.

**No usable driver on this host** (drive skill degraded to documented-limitation / no rung that can act): end `REFUSED` naming the missing driver. Same refusal family as no surface.

Read [references/doctor-and-proof.md](references/doctor-and-proof.md) before the first drive. Doctor is the one read-only worth-driving check (right build/version, port owned by this run, auth valid). Run it **before the first drive, on each fresh session, and again after any failed drive.**

Never drive an instance this run did not start. An orphaned port from a crashed prior run: Doctor reports it and the run ends `BLOCKED` with the reclaim instruction for the human. Two concurrent runs isolate by disposable profile/port; where the app cannot run twice, the owned-port check fails and the second run ends `BLOCKED`.

### Done when

- The checkout starts, or the run ended `REFUSED` with the precise breakage.
- Doctor has run once for this session and named the instance this run owns.
- A usable driver is named, or the run ended `REFUSED` naming the missing driver.
- An orphaned port or failed isolation ended `BLOCKED` rather than sharing a drive.

---

## Phase 3: Identify the top handful

**Goal:** the first map is small and real. Later maintain passes extend it.

Walk user-facing surfaces. For each, list the features a real user would name (home, sign-in, the primary object, settings). Cap at a handful this run. Multi-surface: group candidates by Surface identifier.

Per candidate record: slug, `Surface`, one-line user-visible behavior, likely entry points (user POV). No implementation details, no source paths.

### Done when

- A short list exists, grouped by Surface.
- Enumeration came from observation, not a user question.

---

## Phase 4: Prove each route

**Goal:** every seeded route is proven by one live drive before it lands. Nothing enters the map that was not driven once. A cleanup that eats the proof fails the step.

For each candidate, for each user entry point:

1. **Doctor** - before the first drive this session; again after any failed drive; again on a fresh session.
2. **Drive** via the flow-next-drive read-and-drive contract (pointer above). Universal flow: observe → snapshot fresh refs → act → verify → capture.
3. **Proof** follows [references/doctor-and-proof.md](references/doctor-and-proof.md): capture the user action **and** the resulting state, not just the final screen; verify side effects beside what is visible; exercise the real user path, never a test-only endpoint.
4. Only a proven route is eligible to land.

Failed route: name it, do not land it, continue. Partial seed lands proven features and reports failures by name - never all-or-nothing discard, never an undriven entry.

Unreachable: report the attempted route and the unmet precondition. Never record it as verified-via-another-path. An unstated prerequisite is itself a finding, not a pass.

Wedged UI on a healthy process (Doctor cannot see it): reset to a known state or relaunch rather than hoping.

Never drive an instance this run did not start.

### Done when

- Every route queued to land has one live-drive proof with evidence at a named path under `.flow/tmp/features-<run-id>/`.
- Failures are named. Zero undriven entries are queued to write.
- **No live target or no available driver already ended `REFUSED` in Phase 2.** A run that skipped the proof step and still wrote a feature file has broken this.

---

## Phase 5: Write the map

**Goal:** a cold agent can drive from `.flow/features/` alone.

Write `.flow/features/README.md` from the index shape in [references/feature-entry-contract.md](references/feature-entry-contract.md). Required operating-rule sections: baseline preconditions, driving conventions, proof standards, feature-entry contract pointer. Group entries by `**Surface:**`. State isolation (side-by-side ports/profiles, or a run refuses to double-drive a shared instance).

Write **one file per proven feature**. Each opens with H1 title + one paragraph of user-visible behavior + a one-line `**Surface:**` identifier, then exactly four H2s in order: `Sub-features` / `How to get to it (user POV)` / `Driving it` / `Gotchas`. Driving it starts with `Preconditions:`, then labeled bullets pairing each user action with an exact command and its observable result.

Partial seed: write the proven files; name failures in the index and in the verdict `reason`. Do not write a file for a failed route.

### Done when

- The index carries the four operating-rule sections plus surface grouping/selection semantics (consumers select by surface + sub-feature IDs).
- Each feature file matches the four-H2 + `**Surface:**` contract.
- Failures are named. Zero undriven files sit under `.flow/features/`.

---

## Phase 6: Cleanup and verdict

**Goal:** instances and scratch this run started are gone; evidence remains; the terminal line is last.

Cleanup removes instances and scratch state, **never evidence**. After teardown, verify each evidence file still exists at its named location. A cleanup that eats the proof fails the step.

Then print the terminal line as the **last line** of the run, nothing after it:

```text
FEATURES_VERDICT=<SEEDED|CLEAN|CHANGED|BLOCKED|REFUSED> features=<n> reason="<one line>"
```

Seed outcomes this file emits:

| Verdict | When |
|---------|------|
| `SEEDED` | At least one proven feature landed. `features=<n>` is the landed count. Partial seed names failures in `reason`. |
| `REFUSED` | No drivable surface, no usable driver on this host, or broken checkout (reason names which). Autonomy refusal is SKILL.md's fence. |
| `BLOCKED` | Orphaned port, concurrent isolation failure, or another named blocker. Reclaim left to the human where ownership is in doubt. |

`CLEAN` and `CHANGED` are maintain outcomes; seed does not emit them.

### Done when

- Instances and scratch this run started are gone; evidence remains at its named paths.
- The last line of the run is one `FEATURES_VERDICT=` line matching the grammar above.

---

## Refusal paths (summary)

| Condition | Verdict | Reason names |
|-----------|---------|--------------|
| No drivable user surface | `REFUSED` | that the repo has no user-facing surface to drive |
| No usable driver on this host | `REFUSED` | the missing driver |
| Checkout does not build or start as-is | `REFUSED` | the precise breakage (or it was fixed first, and seed continued) |
| Autonomy marker (SKILL.md fence) | `REFUSED` | autonomy marker present |
| Orphaned port / concurrent shared instance | `BLOCKED` | the port/process this run did not start; reclaim is the human's |
