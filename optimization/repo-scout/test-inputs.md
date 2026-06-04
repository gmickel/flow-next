# Frozen test inputs (3 — variety across config / skills / CLI)

T1. "Add a new `flowctl config set` key `tracker.rateLimitPerHour` (int, default 1000) under the tracker block, value-checked like the other tracker keys."

T2. "Add a lifecycle touchpoint to the make-pr skill that posts the PR link as a comment to a Slack channel when the bridge is active — mirror the existing tracker touchpoint gating pattern."

T3. "Add a `--json` output flag to a flowctl review subcommand that currently only prints text, following the existing `--json` convention in flowctl."
