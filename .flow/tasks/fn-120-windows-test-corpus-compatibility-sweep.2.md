---
satisfies: [R4, R5, R7, R10]
---
# fn-120-windows-test-corpus-compatibility-sweep.2 Reproduce and fix real Windows 8.3 path failures

## Description
Reproduce and fix normalize's Windows short-path failure and independently remediate task-create's actual Windows portability failure.

**Size:** L
**Files:** plugins/flow-next/tests/test_normalize_section_content.py, plugins/flow-next/tests/test_task_create_files.py, plugins/flow-next/scripts/flowctl.py or shared test helpers only when evidence identifies the owner, .github/workflows/test-flow-next.yml

### Approach

Run each file independently with verbose/bounded output on `windows-latest`. For normalize, capture the traceback and create a deterministic fixture that passes a real valid short path (observed `RUNNER~1` shape) through the production CLI `--file` contract. For task-create, start from the current `os.geteuid()` evidence: guard only the POSIX permission premise while keeping every portable assertion active, unless Task 1's fresh characterization proves a different owner. Do not assume the errors share a root cause.

For normalize, test short-form and normal long-form paths, spaces, drive letters, and UTF-8 contents. Remove each exclusion atomically with the proven fix and green Windows run.

### Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_normalize_section_content test_task_create_files -q
```
## Acceptance
- [ ] Both files are isolated independently and exact Windows tracebacks are captured before remediation.
- [ ] Normalize regression fixtures exercise a real valid Windows 8.3/short path, not a mocked separator string; valid short and long `--file` paths with spaces/drive letters/UTF-8 content work through the real CLI.
- [ ] Task-create guards the POSIX-only permission premise (`os.geteuid()` or evidenced equivalent) while all portable tests continue running on Windows.
- [ ] A shared fix is used only if evidence proves one root cause; otherwise each owner receives a narrow fix.
- [ ] Both exclusions are removed in the same commit(s) as their fixes and focused Windows runs are green.
- [ ] Workflow run URL/ID is recorded; POSIX focused tests remain green.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
