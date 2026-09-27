# Cut mycli --version cold start

## Goal & Context

`mycli --version` pays for plugin discovery and the `stats` tables before it prints one line. Cut its cold start through repeated measured attempts, without changing what any subcommand prints.

## Hill-climb pre-registration

- Metric: `mycli --version` cold-start wall time, median, in milliseconds
- Direction: lower
- Target: below 40 ms
- Attempt floor: 5
- Budget: 10 attempts
- Harness: `python3 bench.py --runs 11 --warmup 3 <dir> [<dir>]` (interleaves the directories; exits 1 on a wrong output)
- Regression gate: `python3 -m unittest discover -s tests`
- Runs per measurement: 11
- Minimum detectable effect: 10 ms

## Acceptance Criteria

- **R1:** `mycli --version` cold start is below 40 ms, measured by the frozen harness.
- **R2:** `mycli --version`, `mycli list` and `mycli stats` print what they print today (the regression gate).
