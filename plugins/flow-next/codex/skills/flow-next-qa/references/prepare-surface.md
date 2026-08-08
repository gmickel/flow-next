# Prepare — accounts, personas, and the device matrix

Reached from `workflow.md` Phase 3 on the paths that need them: **§1** when a scenario
needs a test account or a fresh-user persona, **§2** on a web-surface run that has to pick
viewports. A run whose scenarios are all public and single-surface reaches neither.

The session-hygiene rules themselves (fresh storage, one session per agent, auth cool-down,
unique persona, reset between role changes) live in `qa-discipline.md`, which `workflow.md`
§3.3 links directly — do not duplicate them here. The driving commands
(`set viewport`, `screenshot`, storage clear, `state save/load`) are fn-51's
(`flow-next-drive/references/`).

## 1. Test accounts + personas

Most scenarios beyond the public happy path need credentials. Resolve them before authoring
auth-dependent steps:

1. Look for a documented playbook — auth-provider dev mode, a seed script (`scripts/seed-*`, `db/seeds/`, `supabase/seed.sql`), fixtures (`__fixtures__/`, `test-data/`), or a `.env.test.example`.
**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

2. If none is documented: when `NO_PROMPT=0`, **ask the user** (`plain-text numbered prompt`, info prompt): the auth provider / dev-user docs, an admin account (or permission to create one), and the per-run email-suffix convention — offer to document the convention as part of the pass. When `NO_PROMPT=1` (autonomous / Ralph), undocumented accounts are a hard limitation → BLOCKED + clean exit (the public happy-path scenarios may still run if a target URL resolved; auth-dependent scenarios that cannot proceed without credentials make the outcome BLOCKED).
3. **Never guess credentials**, and never commit a password to the repo — record only the email pattern + role; pass secrets via the existing chat / vault. (Provider fixtures like Clerk's `424242` OTP or Stripe's `4242…` test card are out of this lean borrow's scope — reach for the provider's docs when a flow needs one.)

Generate fresh-user personas with the collision-proof suffix from `qa-discipline.md` —
`qa-<persona>+run<MMDD>-<N>@example.com` (`example.com` never sends real mail; bump `N` on
every retry).

## 2. Device matrix (v1 = viewport emulation only)

v1 covers **one desktop + one mobile viewport** via fn-51's web ladder — viewport
**emulation**, not real-device / cross-device testing (the spec's planning decision; true
device coverage inherits fn-51's surface support later):

| Mode | Reference viewport | Set via (fn-51) |
|------|--------------------|-----------------|
| Desktop | `1280 × 800` | `agent-browser set viewport 1280 800` |
| Mobile | `375 × 812` | `agent-browser set viewport 375 812` |

Lead with the app's **primary** target: take it from the spec; if the spec is silent, ask the
user which mode matters most when `NO_PROMPT=0`; when `NO_PROMPT=1` (autonomous / Ralph — no
user to ask), infer the likely primary from repo signals (responsive CSS / framework defaults
/ marketing copy) and **note the assumption** in the run notes. The viewport choice is a soft
default, not a blocking fact — it never gates the run (unlike an undocumented target URL /
accounts, which BLOCK). Record the chosen viewports against each scenario so Phase 4 drives at
the right size and the evidence tuple's `viewport` field is accurate. Layout / overflow /
tap-target bugs hide at the breakpoint you skip — run the relevant scenarios at **both**
viewports, not just the primary.
