# Per-stack readiness matrix

One row per stack. The matrix drives three things: the Phase 2 non-interactive **verify** command (the operability-ladder evidence), the **LSP** / **Map** recommendations, and the **gotcha** findings. It is a **maintained opinion table** - rows are explicit, reviewable, and correctable per portfolio experience; unknown stacks degrade generically (last section).

**Pattern / instantiation discipline (load-bearing).** The skill's logic, phases, checks, and report prose reference only the GENERIC patterns - the operability ladder, the LEG1-LEG9 legibility patterns (defined in playbooks.md), the ranked-actions catalog. Everything stack-specific is DATA in a row here. **Adding a stack = adding a row, never editing skill logic.** No stack name is hardcoded in workflow / playbook logic; this is what keeps the playbook reusable across a 10-11-stack portfolio and stops the skill ossifying around one stack's quirks.

**LSP reality (honest, not aspirational).** Claude Code has native LSP via code-intelligence plugins since v2.0.74; Serena MCP is the cross-agent alternative. **NEITHER covers Pascal/Delphi, VB6, PowerBuilder, or PL/SQL** - the matrix says so plainly and routes those stacks to the LEG3 substitute-navigation recommendation instead of pretending an LSP exists.

**DE7 map gating.** The **Map** column IS the `/flow-next:map` (clawpatch) suggestion gate: suggest a map ONLY when the row's Map cell is `yes`. `none` / `partial` SUPPRESSES the `/flow-next:map` suggestion and routes to the LEG3 substitute-navigation class (a generated dependency-graph artifact, a hand-written orientation map, or static analysis as the proxy verifier). Never suggest `/flow-next:map` on a stack clawpatch cannot parse.

**Non-interactive + non-mutating.** Every verify command is the CHECK-mode, non-interactive form (CI=true, `--console=plain`, no watch mode). Assessment never mutates the assessed repo: lint / typecheck run in check mode, tests run as discovery / list or a bounded run, builds are bounded (~5 min timeout). Windows-only or license-bound builds that cannot run on the current host are recorded "not probed on this host", never a fabricated pass.

---

## Matrix

| Stack | Detect | Verify (non-interactive) | LSP for agents | Map tooling | Gotchas |
|---|---|---|---|---|---|
| TS/JS | `package.json` | `pnpm lint && pnpm test` (CI=true) | tsserver plugin (trivial) | yes (clawpatch, aider) | watch-mode default test scripts; pick ONE package manager |
| Python | `pyproject.toml` | `ruff check && pytest -q` | pyright (trivial) | yes | env resolution (uv / poetry / pip) is the probe |
| Go | `go.mod` | `go build ./... && go vet ./... && go test ./...` | gopls (trivial) | yes | gold standard; little to fix |
| Java | `pom.xml` / `gradlew` | `./mvnw -B verify` / `./gradlew build --console=plain` | jdtls (setup cost) | yes | wrapper scripts are the readiness marker; old Java EE often drops to compile-only |
| C#/.NET modern | `*.csproj` net6+ | `dotnet build && dotnet test --no-build` | Roslyn LSP plugins | yes | central package mgmt; nullable-as-errors |
| C#/.NET Framework 4.x | old-style `*.csproj`, `packages.config` | `msbuild /t:Build /restore`; `vstest.console.exe` | partial | partial | Windows-only build; WSL agents cannot build; NOT `dotnet build` |
| PHP | `composer.json` | `composer validate && vendor/bin/phpstan && vendor/bin/pest` | Intelephense / phpactor | yes | facades / container blind the LSP; phpstan is the real verifier |
| Ruby/Rails | `Gemfile` | `bundle exec rubocop && bundle exec rspec` | ruby-lsp | yes | metaprogramming limits LSP payoff; DB-dependent tests need services |
| C/C++ | `CMakeLists` / `Makefile` | `cmake --build build && ctest` | clangd REQUIRES `compile_commands.json` | yes | `compile_commands.json` presence is THE readiness probe |
| Kotlin/Android | `settings.gradle.kts` | `./gradlew assembleDebug lint testDebugUnitTest` | jdtls / kotlin-ls | yes | distinguish unit (Robolectric) vs instrumented tiers; emulator not agent-verifiable |
| Swift/iOS | `Package.swift` / `*.xcodeproj` | SPM `swift build && swift test`; app `xcodebuild ... \| xcbeautify` | SourceKit-LSP (SPM good, xcodeproj weak) | SPM only | macOS-only; SPM packages far stronger agent territory than xcodeproj apps |
| SQL/PLSQL | `*.pks` / `*.pkb` | utPLSQL-cli against a disposable Oracle container (gvenzl images) | none practical | none | cannot verify without a DB; container or dev schema is the readiness move |
| Delphi | `*.dpr` / `*.dproj` | `rsvars.bat && msbuild X.dproj /t:Build`; DUnitX console -> NUnit XML | none practical (license-bound) | none | encoding, `.dfm`/`.pas` pairing, IDE-managed files - see LEG instantiations below |
| VB6/PowerBuilder | `*.vbp` / `*.pbl` | `vb6.exe /make`; OrcaScript | none | none | binary `.pbl` needs source export first; honest answer is often migration tooling |
| COBOL | `*.cbl` + JCL | static-parse tier; characterization tests | none | none | Anthropic Code Modernization Playbook is the canonical reference |

Rows are starting opinions maintained here. Below 400K LOC, do NOT recommend the LSP / index tooling in a `yes` cell (measured net-negative per Axis 3); recommend an orientation map + loops instead. Above 400K LOC, DO - where the stack supports it.

---

## Framework dev-MCP (the DR7 gate)

DR7 (framework dev-MCP) is STACK-GATED here, N/A otherwise. Suggest a framework dev-MCP only when a detected stack ships one:

| Stack marker | Dev-MCP | DR7 |
|---|---|---|
| Next.js 16+ (`next` >= 16 in `package.json`) | `next-devtools-mcp` | scored-in-tier |
| any other stack | none shipped | N/A |

---

## LEG-pattern instantiations (data, per stack)

The generic legibility patterns LEG1-LEG9 are defined in playbooks.md; their concrete instantiation for a stack lives ONLY here (Delphi is the worked exemplar because it exercises every pattern - it is data, never skill logic). Modern-stack instantiations are listed too, because eval promoted LEG4/LEG6/LEG7 from the legacy-only playbook to ALL shapes (both fired on a modern plugin repo).

**Delphi (15M-LoC worked exemplar):**

- **LEG1 headless-feedback wrapper:** `Build.cmd` wrapping `rsvars.bat && msbuild X.dproj`; one paid seat legally covers an unattended build server (RAD Studio 12 EULA unattended-build clause).
- **LEG2 toolchain/license reality:** DelphiLSP is license-bound; Windows-only builds are unprobeable from macOS / WSL hosts -> "not probed on this host".
- **LEG3 no-LSP/no-map substitutes:** DUDS / MMX / Pascal Analyzer uses-graph; entrypoints from the `.dpr`; SonarDelphi / FixInsightCL / SARIF as the proxy verifier.
- **LEG4 pathology inventory:** 50K-line units, `.res` / `.dcu`, binary `.dfm`.
- **LEG5 encoding/codepage sweep (P1):** legacy Pascal sources are often ANSI / Windows-1252 or UTF-16; recommend a one-time normalization commit, an encoding-guard hook, or a never-edit list (coding agents have documented corruption bugs on non-UTF-8 files).
- **LEG6 atomic file-pair rule:** `.dfm` + `.pas` - editing one side without the other corrupts the form; require a pairing rule in the agent file.
- **LEG7 tool-managed never-edit list:** `.dproj` / `.dsk` / `.identcache` / `__history` are IDE-rewritten or opaque - explicit never-touch list.
- **LEG8 module carve-outs:** name safe agent territory vs frozen subsystems; a carve-out with its own build + tests is what "agent-ready" means at multi-M LOC, never the whole tree.
- **LEG9 characterization tests:** the verify strategy where unit tests are absent and behavior must be preserved.

**C#/.NET Framework 4.x:**

- **LEG1:** `msbuild /t:Build /restore`, NEVER `dotnet build`.
- **LEG2:** Windows-only build; WSL / macOS agents record "not probed on this host".
- **LEG5:** old VB / C# dumps and UTF-16LE SQL scripts carry the same encoding hazard.
- **LEG6:** WinForms `.Designer.cs` + `.cs` atomic pair.
- **LEG7:** `.sln` user files, `.suo` - never-edit.

**VB6/PowerBuilder:**

- **LEG3:** no LSP, no map; static analysis is the only proxy.
- **LEG8:** binary `.pbl` must be source-exported first; where in-place agent work is impractical, the honest answer is migration tooling (Mobilize VB6 AI Migrator).

**COBOL:**

- **LEG1:** static-parse tier - name it honestly (tier 0/1), do not fabricate a run tier.
- **LEG3:** deterministic dependency-graph artifacts are prerequisites, not nice-to-haves (Microsoft COBOL-agents lesson).
- **LEG9:** characterization / snapshot tests as the verify strategy during modification.

**SQL/PL-SQL:**

- **LEG1:** the readiness move is a disposable Oracle container (gvenzl images) or a dev schema; cannot verify without a DB.
- **LEG5:** UTF-16LE script hazard.

**Modern-stack instantiations (LEG4/6/7 fire everywhere):**

- **LEG6 atomic pairs:** protobuf generated + source; a dual-copy invariant pair (e.g. `scripts/flowctl.py` <-> `.flow/bin/flowctl.py`, a real trap for any contributor's agent when documented only in private notes).
- **LEG7 tool-managed:** a script-regenerated mirror dir ("`codex/` is generated by sync-codex.sh - never hand-edit"); tracked legacy snapshots an agent file marks off-limits.

---

## Unknown stacks - generic degrade

A stack with no row degrades to the generic operability ladder plus an honest line: **find the manifest -> find the build command -> find the test-list command**, name the current operability tier from executed evidence, and print "no per-stack playbook yet for `<stack>`". Never suggest `/flow-next:map`, an LSP, or index tooling for an unknown stack - the Map / LSP gates default closed until a row is added.
