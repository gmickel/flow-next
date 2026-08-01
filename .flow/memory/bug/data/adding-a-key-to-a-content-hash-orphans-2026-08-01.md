---
title: Adding a key to a content hash orphans records the old binary wrote
date: "2026-08-01"
track: bug
category: data
module: plugins/flow-next/scripts/flowctl.py
tags: [fingerprint, idempotence, upgrade-compat, golden-fixture, chart]
problem_type: data
symptoms: Post-upgrade identical retry fails chart_not_open on a chart the pre-fix binary reopened and re-briefed
root_cause: "Conditional-omission compat rule covered records with the key absent, not records written while it was present but unhashed"
resolution_type: fix
related_to: [bug/data/fence-preserving-writer-needs-fence-2026-07-02, bug/data/migrationrollback-cli-10-review-cycle-2026-05-08, bug/data/paired-snapshot-setter-must-write-both-2026-06-03, bug/data/yaml-frontmatter-writer-unescaped-2026-07-24]
---

## Problem

`chart briefing` is idempotent on a content fingerprint. `chart reopen` staled every
briefing but changed nothing the fingerprint hashed, so re-briefing an untouched ledger
matched the stale briefing and echoed it back with `noop: true` - a `briefable: true`
chart with no capture-ready briefing and no path to one.

The fix folds the reopen epoch (`reopened_at`) into `_briefing_fingerprint`, with the key
**omitted entirely** when the chart carries no reopen so charts already on disk hash
byte-identically.

## What Didn't Work

The conditional-omission rule was written for "charts never reopened", which is only half
the installed base. A chart that was reopened AND successfully re-briefed by the old binary
has a `reopened_at` **and** an epoch-free stored hash on its *live* briefing. After the
upgrade the epoch-aware hash missed it, the retry found no match, and the command died on
the now-`done` chart with `chart_not_open`. A valid current briefing became unreachable
purely by upgrading the binary. Review (rp) caught it; no test in the first round could,
because both golden fixtures covered never-reopened charts.

## Solution

Accept the epoch-free hash as well when the chart carries a reopen, but only for a
**non-stale** briefing (`flowctl.py` `emit_chart_briefing`, the `accepted_fingerprints`
set). The safety argument is what makes it sound: every reopen stales every briefing, so a
non-stale match can only have been minted in the current epoch. A stale legacy match is
exactly the defect being closed and stays refused by the read-side guard.

The idempotent envelope now reports the matched briefing's own stored hash, identical on
every ordinary match.

## Prevention

- **Two fixtures, not one.** A hash-input change needs a golden fixture per *class of prior
  state*, not per algorithm. Here: never-reopened AND reopened-then-re-briefed. Enumerate
  the states the new key can be in for records the old binary wrote - absent, present-but-
  unhashed - and pin one fixture for each.
- **Generate the fixture from the OLD binary** (`git show <base>:path/to/cli.py`) and check
  the bytes in. A same-version emit-then-retry proves only that the new algorithm agrees
  with itself; it passes even when the hash has become incompatible with everything on disk.
- **Prove the fixture bites.** Patch the naive variant (here: hash the key unconditionally)
  into a scratch copy and confirm the fixture test fails. A compat fixture that cannot fail
  is decoration.
