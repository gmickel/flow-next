# make-pr — manual smoke expectations

Maintainer reference for `workflow.md`. Not part of any render path: the skill never
reads this file at runtime. It is the manual-invocation checklist that stands in for
the unit tests a markdown skill can't have.

The skill itself is markdown — no unit-test surface. Phase 0 validation is exercised via the smoke test and by manual invocation in a real session. Expected behavior:

- `command -v gh` missing → exit 1 with install instructions.
- `gh auth status` failing → exit 1 with login instructions.
- `--base <bad-ref>` → exit 1 with `git rev-parse --verify` failure message.
- Branch with no `branch_name` match in any `.flow/specs/*.json` AND no positional spec id → interactive `AskUserQuestion`; Ralph hard-errors with exit 2.
- Tasks not all done + interactive → warn on stderr + proceed (open items force a draft via §4.2); Ralph exits 2; `--dry-run` warns and continues. No `AskUserQuestion` for open tasks.
- Branch with an OPEN PR → exit 1 with `/flow-next:resolve-pr` hint.
- Branch with a CLOSED or MERGED PR (no OPEN) → continues cleanly. **This is the load-bearing check** — fn-42 spike validated empirically that bare `gh pr view --json url` rc=0 for closed/merged PRs would false-positive without the `select(.state == "OPEN")` filter.
- Branch with no PR history at all (`gh pr view` exits 1) → continues cleanly.
- Ralph mode (`FLOW_RALPH=1`) → no `AskUserQuestion` calls in Phase 0; deterministic exit codes on missing context.
- `artifacts.html.enabled` unset/false → Phase 1.5b performs one config read; no HTML-reference load, no `pr.html` write or commit, and no render-lens body line. Phase 1.5 still persists the structured PR cognitive-aid and renders its supported current walkthrough into the body.
- `artifacts.html.enabled` true + supported current v1 input → `.flow/artifacts/<spec-id>/pr.html` written with the exact semantic carrier, self-check grep prints `OK: self-contained`, no artifact commit advances `HEAD`, and the body carries local-open guidance.
- `artifacts.html.enabled` true + labeled legacy fallback + tracked artifact → exactly one `chore(flow): pr artifact <spec-id>` commit (artifact file only — `git show --stat` lists one path) before `gh pr create`, and the blob link resolves on the remote branch.
- `artifacts.html.enabled` true + `--dry-run` → no artifact written, no commit, no render-lens line in the stdout body.
- `artifacts.html.enabled` true + the artifact file ignored by ANY rule (`.flow/artifacts/`, `.flow/artifacts/**`, `*.html`, or the exact path) → no commit, body carries local-open guidance, no blob link.
- `artifacts.html.enabled` true + artifact commit fails (e.g. rejecting pre-commit hook) → PR still created, no render-lens body line, exactly one stderr note.
- `artifacts.html.enabled` true + Ralph → artifact may generate, but stdout is still exactly `PR_URL=<url>`; all artifact messaging on stderr; no `lavish-axi` invocation in the transcript (interactive or autonomous — the PR lens never opens a session).
