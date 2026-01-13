# fn-9.19 README and usage docs

## Description

Create README.md for flow-next-tui and update existing docs to link to it.

### flow-next-tui/README.md (new)
- Installation instructions (bun add, npm)
- CLI usage and flags (--light, --no-emoji, --run, etc.)
- Integration with Ralph (how TUI connects to runs)
- Keyboard shortcuts reference
- Screenshots/examples of TUI in action
- Troubleshooting common issues

### Update existing docs to link
- `plugins/flow-next/docs/ralph.md`: Add "Ralph TUI" section with quickstart, link to full readme
- `plugins/flow-next/README.md`: Add brief TUI section in Ralph area, link to readme
- `README.md` (root): Add TUI mention in Ralph section, link to readme

## Acceptance
- [ ] flow-next-tui/README.md exists with full docs
- [ ] Installation section with bun/npm commands
- [ ] CLI usage with all flags documented
- [ ] Ralph integration explained
- [ ] Keyboard shortcuts table
- [ ] At least one screenshot or ASCII mockup
- [ ] plugins/flow-next/docs/ralph.md has TUI quickstart section
- [ ] plugins/flow-next/README.md mentions TUI
- [ ] Root README.md mentions TUI in Ralph section

## Done summary
- Created flow-next-tui/README.md with installation, CLI usage, keyboard shortcuts, layout diagram, tool icons, architecture, troubleshooting
- Updated plugins/flow-next/docs/ralph.md with TUI quickstart section
- Updated plugins/flow-next/README.md with TUI link
- Updated root README.md with TUI link

Why:
- Provide comprehensive documentation for TUI users
- Link TUI from Ralph docs for discoverability

Verification:
- bun test (379 tests pass)
- All acceptance criteria from spec met
## Evidence
- Commits: 7b6b4c01005343565440bea14ea99fcc28400f75
- Tests: bun test
- PRs: