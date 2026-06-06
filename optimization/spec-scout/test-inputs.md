# Frozen inputs — spec-scout (deterministic inline "open specs" corpus, no flowctl/web needed)

The subagent is given the corpus inline (these ARE the open specs it would get from `flowctl specs`),
so the eval is deterministic and repo-independent. Model held: claude-sonnet-4-6. Same corpus for both
inputs.

## OPEN SPECS CORPUS (given to the subagent verbatim each run)

- **os-1** — "OAuth callback handler": owns `src/auth/oauth.ts`; adds `authService.validateToken()`. Acceptance: callback validates token, sets session.
- **os-2** — "Rate limiter middleware": owns `src/middleware/rateLimit.ts`; wraps `src/api/handlers.ts` routes. Acceptance: ≥3 req/s per client rejected.
- **os-3** — "User profile API": owns `src/api/handlers.ts`, `src/models/user.ts`; adds `GET /profile`. Acceptance: returns the authed user's profile.
- **os-4** — "Email notification service": owns `src/services/email.ts`; **needs an event bus to subscribe to (not built yet)**. Acceptance: sends an email on a published `user.created` event.
- **os-5** — "Database migration tooling": owns `scripts/migrate.ts`; CLI to run/rollback migrations. Acceptance: migrations apply idempotently.
- **os-6** — "Design system tokens": owns `styles/tokens.css`; defines color/spacing tokens. Acceptance: components reference tokens not raw hex.

---

## S1 — new request (API + auth)

REQUEST: *"Add a new `GET /admin/users` endpoint that lists all users. It must require authentication,
will live in the API handlers, and reads the user model."*

**Answer key (must surface):**
- **Dependency:** os-1 (uses `authService.validateToken()` for the auth requirement).
- **Overlap:** os-3 (both own/touch `src/api/handlers.ts` + `src/models/user.ts`); os-2 (wraps `src/api/handlers.ts` routes — the new route is affected by the rate limiter).
- **No relationship:** os-4, os-5, os-6.

## S2 — new request (events)

REQUEST: *"Add an event bus that publishes a `user.created` event when a user signs up, so other
services can subscribe."*

**Answer key (must surface):**
- **Reverse dependency:** os-4 (the email service is waiting for exactly this event bus / `user.created` event — it depends on the new plan).
- **Overlap / dependency:** os-3 (user signup path touches `src/models/user.ts` / the user-creation flow); os-1 (signup may follow the auth/session flow) — surfacing os-3 is required; os-1 is acceptable.
- **No relationship:** os-2, os-5, os-6.
