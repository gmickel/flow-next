# Binary evals (5) — max per run = 5; max_score = 5 × 2 inputs = 10

EVAL 1: Key docs + API surfaced  [FEATURE PRESERVATION]
Question: Does the output surface the input's must-keep canonical doc(s) (with URL) AND name the key
API inline (D1: express-rate-limit + rateLimit({windowMs,limit,statusCode}); D2: Zod + safeParse +
z.object/.strict + flatten + z.infer)?
Pass: must-keep docs + key API named. Fail: a must-keep doc or key API dropped.

EVAL 2: Critical gotchas surfaced  [FEATURE PRESERVATION]
Question: Are the input's load-bearing gotchas present (one line each)? D1: trust-proxy/IP-keying
(+ MemoryStore-not-shared); D2: v3-vs-v4 import (+ flatten-top-level-only).
Pass: the critical gotchas surfaced. Fail: a load-bearing gotcha dropped.

EVAL 3: No code blocks / capped  [BUDGET TARGET]
Question: Does the output avoid fenced code blocks > 6 lines AND multi-line `>` excerpt blocks
(signatures named inline; no exhaustive config-option dump)?
Pass: no code block > 6 lines, no multi-line excerpt, no full option list. Fail: any of those.

EVAL 4: Lean  [TOKEN LEVER]
Question: Is the output ≤ 450 tokens (~340 words)?
Pass: word count × 4/3 ≤ 450. Fail: over 450 tokens.

EVAL 5: Sources grounded  [ACCURACY]
Question: Are cited doc URLs / source paths real/plausible official sources (not fabricated)?
Pass: URLs resolve to the named official docs. Fail: a fabricated/wrong-project URL.
