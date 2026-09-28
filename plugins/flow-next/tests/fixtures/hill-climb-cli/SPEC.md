# Cut mycli --version cold start

## Goal & Context

`mycli --version` pays for plugin discovery and the `stats` tables before it prints one line. Cut its cold start below 40 ms through repeated measured attempts, without changing what any subcommand prints.

## Acceptance Criteria

- **R1:** `mycli --version` cold start is below 40 ms, measured by the frozen harness.
- **R2:** `mycli --version`, `mycli list` and `mycli stats` print what they print today (the regression gate).
