# fn-9.16 CI/CD workflow

## Description

Create GitHub Actions workflow for CI/CD and npm publishing.

### File

`.github/workflows/publish-tui.yml`

### Triggers

- Push to `tui-v*` tags
- Manual workflow_dispatch

### Packaging strategy (follows gno pattern)

Publish TypeScript source directly - Bun executes .ts natively.

**package.json fields:**
```json
{
  "bin": { "flow-next-tui": "src/index.ts", "fntui": "src/index.ts" },
  "files": ["src"],
  "engines": { "bun": ">=1.3.0" }
}
```

**Shebang required**: `src/index.ts` must start with `#!/usr/bin/env bun` for global installs to work. npm creates symlinks to the bin target; the shebang tells the OS to use bun.

### Jobs

1. **test** (matrix: ubuntu, macos)
   - Setup Bun
   - `bun install --frozen-lockfile`
   - `bun run lint:check`
   - `bun test`

2. **pack-test** (needs test, ubuntu only - Windows best-effort)
   - `npm pack`
   - `npm install -g ./gmickel-flow-next-tui-*.tgz`
   - `flow-next-tui --version`
   - `flow-next-tui --help`
   - `fntui --help` (verify both aliases)

3. **publish** (needs pack-test)
   - Setup Node 24+ (for npm OIDC)
   - Setup Bun
   - `npm publish --provenance --access public`

### OIDC publishing

```yaml
permissions:
  id-token: write
  contents: read
```

Configure trusted publisher on npmjs.com for `@gmickel/flow-next-tui`.
## Acceptance
- [ ] Workflow triggers on tui-v* tags
- [ ] Tests run on ubuntu and macos
- [ ] Lint check passes
- [ ] npm publish with provenance
- [ ] Tarball contains src/index.ts (not dist)
- [ ] Installed package runs: `flow-next-tui --help`
- [ ] Manual trigger works
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
