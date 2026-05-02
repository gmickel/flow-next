# Strategy Interview

Loaded by `SKILL.md` at the start of Phase 1 and revisited per-section in Phase 2. Every section below maps one-to-one to a section in `strategy-template.md`.

For each section: ask the opening question, evaluate the answer against the quality bar, push back when it falls into a named anti-pattern, and capture the final answer in the user's own language.

## Overall Rules

1. **Ask, don't prescribe.** Do not offer menu options for open answers (problem, approach, persona, metrics, tracks). Use free-form responses. Reserve single-select for routing decisions only (which section to revisit, include this optional section, foreign-file resolution).
2. **Push back once, maybe twice.** If the first answer is weak, name the specific issue and ask a sharper question. If the second answer is still weak, capture what the user has given and append the HTML comment `<!-- worth revisiting -->` to the section body. Do not let the interview spiral.
3. **Quote the user back at them.** When challenging an answer, use the user's own words verbatim. Paraphrasing softens the challenge and is easier to dismiss.
4. **Keep each answer to 1-3 sentences.** Longer answers are usually hiding something vague. If the user writes a paragraph, ask them to pick the sentence that matters most.
5. **Don't leak the anti-pattern names.** The user does not need to hear "that's a vanity metric" or "that's fluff" — just ask the sharper question that follows. Names like `vanity`, `fluff`, `feature-list-as-track`, `goal-stated-as-problem` are internal labels for the agent's diagnosis, not vocabulary for the conversation.

---

## 1. Target Problem

**Opening question:** "What's the core problem this product solves — and what makes that problem hard?"

Strong answers name a specific situation the target user is in, identify what makes the situation hard *right now* (a crux, a constraint, something that isn't easy to route around), and are falsifiable — you could imagine the problem being absent and know the difference.

**Anti-patterns and pushback:**

- **goal-stated-as-problem** ("the problem is we need to grow revenue") → "That's a goal, not a problem. What's in the world that's making that goal hard to achieve? Whose situation are you changing?"
- **vague-wish** ("people need better tools for X") → "Whose situation specifically? Doing what? What do they try today, and why doesn't it work?"
- **symptom-not-cause** ("users churn after 30 days") → "That's a symptom. What's happening in their world that makes them stop caring? What's the underlying condition?"
- **too-broad** ("communication at work is broken") → "That's a civilization-scale problem. Narrow it to a situation you can actually affect — which users, doing what, when does it hurt most?"
- **feature-shaped** ("there's no good way to do [specific workflow] with AI") → "That's a missing feature, not the underlying problem. What outcome do users want that the feature would give them?"

**Capture:** One or two sentences naming the user's situation and the crux. No solution language.

---

## 2. Our Approach

**Opening question:** "Given that problem, what's your approach — the commitment or principle that makes it tractable?"

This is the guiding choice: how the product competes or operates, so that many downstream decisions become easier. It is not the product and it is not a feature list.

Strong answers are a choice (implying alternatives explicitly *not* pursued), are general enough to direct many decisions but specific enough to rule things out, and sound more like "we win by [doing X differently]" than "we do [a list of things]".

**Anti-patterns and pushback:**

- **fluff** ("we're customer-obsessed and move fast") → "Those are values, not an approach. What are you doing *differently* from the other products users could pick? If the answer applies to any company, it's not your approach."
- **feature-list** ("we're building AI-powered X, Y, and Z") → "That's a feature list. What's the underlying bet that makes you pick those features over others? What principle is guiding what you ship?"
- **product-description-as-approach** ("we use AI to draft replies") → "That's what the product does, but what's the *choice* inside it? Every competitor will say the same thing. Your approach should name what you're doing that the obvious alternative isn't — is it a grounding choice, a trust-building commitment, a workflow bet? What are you betting on that they're not?"
- **goal-restated** ("our approach is to be the market leader") → "That's still the goal. How does the product win? What choice are you making that competitors aren't?"
- **multiple-approaches-at-once** ("we're going deep on enterprise, self-serve, and a consumer app") → "Pick one as the guiding approach. The others may still get work, but one of them organizes the rest. Which is it?"
- **doesnt-connect-to-problem** (problem: "users can't trust AI output"; approach: "build a fast, beautiful UI") → "How does that approach solve the problem you named? If there's no line between them, one of the two is wrong."

**Capture:** One or two sentences. Ideally ends with or implies "...so that [outcome tied to the problem]".

---

## 3. Who It's For

**Opening question:** "Who is the primary user, and what job are they hiring this product to do?"

Jobs-to-be-done framing — the user isn't a demographic, they're someone in a situation trying to make progress.

Strong answers name one primary persona (additional personas allowed but secondary), identify them by role or situation rather than demographic, and state a concrete job as a verb phrase.

**Anti-patterns and pushback:**

- **too-many-primary-personas** ("it's for founders, PMs, engineers, and designers") → "If it's for everyone, it's for no one. Who matters most? The others can still benefit, but one of them drives the product decisions."
- **demographic-framing** ("25-45 year old professionals") → "That's a demographic, not a user. What are they trying to do that makes them pick up this product?"
- **role-without-situation** ("PMs") → "PMs doing what? Running a roadmap review? Writing a spec at midnight? Convincing a skeptical eng lead? The situation is where the product matters."
- **generic-job** ("they want to be more productive") → "Productive at what specifically? They're hiring this product to do *what*? The more specific, the better the product decisions downstream."

**Capture:** Persona name plus JTBD sentence. Example: "Solo founders running their own roadmap. They're hiring the product to keep strategy and execution aligned without a PM on staff."

---

## 4. Key Metrics

**Opening question:** "What 3-5 metrics will tell you whether the approach is working?"

Metrics are the feedback loop. Bad metrics create the illusion of progress while the product gets worse.

Strong answers stay at 3-5 (not 10), mix leading and lagging (something that moves weekly and something that moves quarterly), and could plausibly regress if the product got worse.

**Anti-patterns and pushback:**

- **vanity** ("total signups, total pageviews, cumulative users") → "Those can all go up while the product gets worse. What moves when users actually get value?"
- **too-many** ("here are 12 metrics we watch") → "A dashboard isn't a strategy. Pick the 3-5 you'd stake the quarter on. What are the others telling you that those don't?"
- **outputs-not-outcomes** ("ship velocity, deploys per week") → "Those measure the team, not the product. If the team doubled velocity but users didn't care, would you call it a win?"
- **can-only-go-up** ("cumulative hours saved") → "A metric that can only go up doesn't tell you much. What's the rate, the ratio, or the thing that can regress?"
- **unmeasurable** ("user delight") → "How specifically? If you can't define how you'd check it on a Tuesday, it's aspirational, not a metric."

**Capture:** A list of 3-5. Each with a one-line definition. Note where each is measured (analytics, DB, qualitative, etc.) if known. If measurement is undefined, ask: "Where does this metric live today? If nowhere, is this something you can start measuring?"

---

## 5. Tracks

**Opening question:** "What are the 2-4 tracks of work you're investing in to execute the approach?"

Tracks are the coherent-actions half of the strategy kernel — concrete areas of investment that flow from the approach. They are not feature lists and not personal todo items. Each track is a named *domain of work*.

Strong answers stay at 2-4 (not 8, not 1), connect clearly back to the approach, and are broad enough that multiple features live inside each one.

**Anti-patterns and pushback:**

- **feature-list-as-track** ("track 1: Slack integration; track 2: mobile app; track 3: dark mode") → "Those are features. What's the *investment area* each one lives inside? 'Integrations' might be one track, with Slack, Teams, and Discord as candidates inside it."
- **too-many-tracks** ("we have 7 tracks this quarter") → "With 7 tracks, every track is starved for attention. Which 3 are load-bearing? The others either fold in or drop."
- **doesnt-connect-to-approach** (approach: "win by being the easiest to onboard"; track: "enterprise SSO") → "How does that track serve the approach? If it's a separate bet, name it as one. If it's load-bearing for onboarding, explain the link."
- **too-vague** ("improve the product") → "Every track is 'improve the product.' What's the specific investment area that's different from the others?"
- **one-track-only** → "With one track, there's no real choice being made. What are the 2-3 things the product needs to be good at, and how are they different?"

**Capture:** 2-4 tracks. For each: a name, a one-line purpose, and a short note on why this serves the approach.

---

## 6. Milestones (optional)

**Opening question:** "Are there any dated milestones worth anchoring — a launch, a fundraise, a conference, a renewal? Skip if none apply."

Only capture externally visible, real milestones. Avoid turning this into an internal schedule.

Default is to skip. Do not push the user to invent milestones. If they name some, capture them verbatim with dates.

**Anti-patterns and pushback:**

- **internal-schedule-disguised** ("v2.3 ships March 15, refactor done by April") → "Those are sprint dates, not milestones. Is there an *externally visible* anchor — something users or stakeholders see? If not, skip the section."
- **manufactured-milestones** (user lists half-real dates to fill the section) → "If they're not real anchors, the section is hurting more than helping. Skip it; that's the right call most of the time."

**Capture:** Verbatim dates + one-line description per milestone. Do not encourage a long list.

---

## 7. Not Working On (optional)

**Opening question:** "Is there anything you've explicitly decided *not* to do right now that's worth naming? This is for things the team keeps being tempted by."

Clarity tool, not a blocker list. Skip by default. If the user names items, one sentence each. Do not encourage a long list.

**Anti-patterns and pushback:**

- **catalog-of-rejections** (long list of things never seriously considered) → "This section is for things the team keeps being tempted by. Stuff you never considered isn't useful here. Pick the 1-2 that actually pull at you."
- **competitor-bashing** ("we're not building a clone of <competitor>") → "That's not a strategic boundary, it's a swipe. What's the *type of work* you're declining? E.g. 'enterprise SSO before product-market-fit' or 'mobile app before web is solid'."

**Capture:** 1-3 items max. One sentence each.

---

## After the Interview

Once sections 1-5 are captured (and any optional sections the user engaged with), the per-section atomic writes have already landed each section on disk. Run `flowctl strategy read --json` to get the current state, present the full draft in chat for read-back, offer one round of edits, then confirm.

The post-write checklist (in `strategy-template.md` §Post-write checklist) is the agent's own scan-pass before showing the read-back — catch placeholder leftovers, sentence-count violations, missing-frontmatter cases, metric/track count out of range, and Target-problem ↔ Our-approach disconnect.
