# fn-9.1 Project scaffolding and dependencies

## Description

Enhance existing `flow-next-tui/` scaffold with proper project structure.

### Files to create/update

- `package.json` - add deps, bin fields, scripts
- `tsconfig.json` - strict mode, Bun compat
- `src/` directory structure per spec

### Dependencies

```json
{
  "@mariozechner/pi-tui": "^0.44.0",
  "commander": "^14.0.0"
}
```

### Dev dependencies

Already have oxlint/ultracite from scaffold.

**Remove** `peerDependencies.typescript` from current scaffold - not needed for Bun runtime.

### package.json updates (gno pattern)

```json
{
  "name": "@gmickel/flow-next-tui",
  "type": "module",
  "bin": {
    "flow-next-tui": "src/index.ts",
    "fntui": "src/index.ts"
  },
  "files": ["src"],
  "engines": { "bun": ">=1.3.0" },
  "publishConfig": { "access": "public" },
  "scripts": {
    "dev": "bun run src/index.ts",
    "start": "bun run src/index.ts",
    "test": "bun test",
    "lint": "oxlint --type-aware --type-check",
    "lint:check": "oxlint --type-aware --type-check && oxfmt --check .",
    "format": "oxfmt ."
  }
}
```

No build step needed - Bun runs .ts directly.

**Shebang required** for global installs:
```typescript
#!/usr/bin/env bun
// src/index.ts - first line must be shebang
```

### Directory structure

```
src/
├── index.ts
├── app.ts
├── components/
├── lib/
└── themes/
```
## Acceptance
- [ ] `bun install` succeeds
- [ ] `bun run dev` runs without error (can show placeholder)
- [ ] pi-tui importable: `import { TUI } from '@mariozechner/pi-tui'`
- [ ] Directory structure matches spec
- [ ] `bun run lint` passes
## Done summary
- Added pi-tui and commander dependencies
- Created src/ with components/, lib/, themes/ directories
- Added CLI entry with shebang, theme types, core types

- Scaffolds foundation for TUI implementation
- Follows gno pattern for bin/files/scripts

- bun install: pass
- bun run dev: pass (shows placeholder)
- bun run lint: 0 warnings/errors
## Evidence
- Commits: 24cde68050ac454581829a297fcbf83c0d8005f4
- Tests: bun run lint
- PRs: