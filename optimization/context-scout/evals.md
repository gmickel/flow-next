# Binary evals (5) — max score per run = 5; max_score = 5 × 3 runs = 15

Accuracy evals (R3 ≥2–3 mandatory): EVAL 1 Grounded, EVAL 2 Coverage, EVAL 3 Tagged.
Token lever: EVAL 4 Lean. Format guard: EVAL 5 Focused.

EVAL 1: Grounded  [ACCURACY]
Question: Does EVERY `path` / `path:Lx-y` reference in the output point to a file that actually
exists in `~/work/DocIQ-Sphere`?
Pass: All cited paths resolve to real files (verified with `test -f`). Zero hallucinated paths.
Fail: Any cited path does not exist.

EVAL 2: Coverage  [ACCURACY] — the R4-mandated coverage eval
Question: Does the output surface the core anchor files for the requested feature (named explicitly
or by an unambiguous equivalent path)?
Per-input anchor sets (pass = names the area AND ≥ the stated minimum anchors):
- T1 (chat): MUST surface `apps/web/components/chat/chat-session.tsx` (or .client/.server variant)
  AND ≥2 of {`chat-timeline.tsx`, `chat-transcript.tsx`, `chat-types.ts`, `native-conversation.tsx`}
  AND identify where a question/message is sent to the backend (a Convex action / API call).
- T2 (docx engine): MUST surface `apps/docx-atomic-backend/app/engine/docx_engine.py`
  AND the FastAPI entry (`app/server.py` or `app/main.py`)
  AND ≥2 engine stage modules from {`extract.py`, `markup.py`, `xml_util.py`, `workspace.py`,
  `part_scope.py`, `comment_parts.py`}.
- T3 (auth): MUST surface `packages/convex/convex/betterAuth/auth.ts` (or adapter.ts/schema.ts)
  AND a web auth lib (`apps/web/lib/auth-server.ts` or `auth-client.ts`)
  AND the route `apps/web/app/api/auth/[...all]/route.ts`.
Pass: meets the per-input minimum. Fail: misses the area or below the minimum.

EVAL 3: Tagged  [ACCURACY]
Question: Does every "Key Files" finding carry exactly one `[VERIFIED]` or `[INFERRED]` confidence
tag (per the prompt's Token Efficiency Rule 6)?
Pass: every key-file bullet has exactly one tag. Fail: any key-file bullet untagged or double-tagged.

EVAL 4: Lean  [TOKEN LEVER]
Question: Is the total returned output ≤ 650 tokens (~490 words)?
Pass: word count × 4/3 ≤ 650. Fail: over 650 tokens.

EVAL 5: Focused (no copy-paste bloat / no absolute paths)
Question: Does the output obey lean-output discipline — repo-relative paths only (no absolute
`/Users/...`), no fenced code block > 10 lines, no complete function/file body pasted?
Pass: relative paths only AND no block > 10 lines AND no full bodies.
Fail: any absolute path, any block > 10 lines, or a pasted full body.
