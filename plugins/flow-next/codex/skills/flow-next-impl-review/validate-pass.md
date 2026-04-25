# Validator prompt (fn-32.1 --validate)

You are validating review findings for false positives. The primary review has
already produced a NEEDS_WORK verdict with a list of findings. For each finding
below, independently re-check it against the **current code** and decide whether
the finding is actually valid.

**Conservative bias — only drop findings that are clearly wrong.** When
uncertain, keep the finding. A kept false-positive is cheap (one extra check by
the fixer); a dropped real bug is expensive (escapes to production).

## Procedure

For each finding:

1. Open the cited file and read around the cited line (±20 lines of context).
2. Check whether the claimed issue is actually present in the current code.
3. Look for guards, handlers, or assumptions that address the concern elsewhere
 in the call chain (the primary reviewer may have missed them).
4. Consider whether the finding is factually correct about the language /
 framework / library semantics.

Do **not** re-score confidence, re-classify severity, or invent new findings.
Decide only: is this finding a real issue in the current code, or not?

## Output format

Return exactly one line per finding in this strict format:

```
<finding-id>: validated: <true|false> -- <one-sentence reason>
```

Examples:

```
f1: validated: true -- null deref confirmed; no upstream guard
f2: validated: false -- null check already present at src/auth.ts:40
f3: validated: true -- race condition reproducible with concurrent requests
f4: validated: false -- suggested fix misunderstands TypeScript narrowing
```

Rules:
- One line per finding id. Missing ids are treated as `validated: true`
 (conservative — when you say nothing, the finding stays).
- Reason must fit on one line (≤200 chars is a good cap).
- Use the literal tokens `validated: true` or `validated: false`. No synonyms.
- Emit the lines anywhere in your response — the parser finds them by regex.

## Findings to validate

<!-- FINDINGS_BLOCK -->
