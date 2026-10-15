# Prove what a diff could break (gated reference)

> **Loaded only when** the route is a diff whose risk should be proven: "what could this break",
> "is this safe to merge", or a change handed over with doubt about its reach.

The answer is read-only: no fix, no `.flow/` write. Implementation review stays the gate on the
change; this answers the question.

1. **Read the change**, including what it now does differently that the diff does not spell out.
2. **Find the one fact it is safe because of.** Most risky-looking changes are safe because of a
   single fact ("only entries already past their expiry are evicted early"); proving it clears
   most cases at once. Spend the effort there, not on a long list of maybes.
3. **Look where text search stops:** the dependency's own source at the pinned version and any
   local patch, serialized formats and stored columns, feature flags, another language reading the
   same bytes, scheduling and teardown order, code a few hops downstream.
4. **Prove the fact by running the real code**: a small script or test that calls what the change
   touches and fails loudly if the fact is false, and the running app when it is reachable. A
   proof that needs production or shared live state stops where it can and is called unproven.
5. **Answer** with what the change does, the safety fact and how far its proof got (stated,
   pointed at the line, walked through the failure, ran it, reproduced it in the app), each risk
   with its location, likelihood, cost and the check that would catch it, a separate list of what
   was checked and cleared, and the cheapest check to run before merging.

Example: a cache moves from time-based to size-based eviction. Safety fact: "nothing reads an
evicted entry without reloading it". A script fills the real cache past its bound and asserts
every read after eviction reloads from source (ran it). One risk: a background job holds an entry
across eviction (low likelihood, one stale cycle, caught by the job's integration test). Cleared:
the serializer (unchanged) and the metrics exporter (reads counts only).
