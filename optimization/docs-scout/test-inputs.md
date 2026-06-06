# Frozen inputs — docs-scout (stable canonical-doc framework queries)

Web-backed (non-deterministic), so inputs target frameworks with stable canonical docs; the eval
focuses on the FORMAT budget + survival of the key API/gotchas. Model held: opus.

## D1 — Express rate-limiting
"Add request rate-limiting to an Express.js (Node, v4) REST API — limit each client IP to N requests
per window, returning 429 when exceeded."

**Must-keep (feature):** express-rate-limit lib (URL) · `rateLimit({windowMs, limit, statusCode})` API ·
the **trust-proxy / IP-keying** gotcha (the #1 IP-rate-limit pitfall) · MemoryStore-not-shared gotcha.

## D2 — Zod body validation
"Validate an incoming JSON request body against a typed schema using Zod (v3) in a TypeScript API —
reject invalid bodies with field-level error messages."

**Must-keep (feature):** Zod (URL) · `safeParse` (non-throwing at the boundary) + `z.object().strict()` +
`error.flatten()` for field errors + `z.infer` for typing · the **v3-vs-v4 import** gotcha.
