# fn-23-zgk.1 Add slugify and update epic creation

## Description
Add a stdlib-only `slugify()` function and integrate it into epic creation.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`

## Approach

1. Add `slugify()` function after line 582 (after `generate_epic_suffix`):
   - Use Django pattern (unicodedata + re, no deps)
   - Max 40 chars (leaves room for `fn-XXX-` prefix in 63 char limit)
   - Return `None` if result is empty (for fallback)

2. Update `cmd_epic_create()` at line 2664-2665:
   - Call `slugify(args.title)` 
   - Fallback to `generate_epic_suffix()` if slugify returns None/empty
   - Keep existing random suffix as fallback for edge cases

## Key context

Django's slugify pattern (no external deps):
```python
import re, unicodedata
text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
text = re.sub(r"[^\w\s-]", "", text.lower())
text = re.sub(r"[-\s]+", "-", text).strip("-_")
```

Edge cases requiring fallback to random:
- Empty title: `--title ""`
- Only special chars: `--title "!@#$"`
- Unicode-only: `--title "中文"` (with ascii encoding)
## Acceptance
- [ ] `slugify("Add OAuth Login")` returns `"add-oauth-login"`
- [ ] `slugify("Fix bug #123!")` returns `"fix-bug-123"`
- [ ] `slugify("Multiple   spaces")` returns `"multiple-spaces"`
- [ ] `slugify("")` returns `None` (empty)
- [ ] `slugify("!@#$%")` returns `None` (no alphanumeric)
- [ ] Long titles truncate at word boundary within 40 chars
- [ ] `flowctl epic create --title "Add OAuth"` produces `fn-N-add-oauth`
- [ ] `flowctl epic create --title ""` falls back to 3-char random
- [ ] Existing tests still pass
## Done summary
Added slugify() function using Django pattern (stdlib only) and updated epic creation to use slugified titles as suffixes with random fallback. Updated regex patterns in both plugin and vendored copies for parity.
## Evidence
- Commits: 453eac5, f5b5488
- Tests: smoke_test.sh (45/45 pass)
- PRs: