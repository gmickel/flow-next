# Frozen test inputs (3 underspecified feature requests + gap answer keys)

Each is a deliberately-thin feature request. The answer key lists the **critical gaps a competent
gap-analyst MUST surface** — the Coverage eval (feature preservation) scores against it. Held
constant across baseline + every experiment.

---

## FG1 — "Add a 'share document via public link' feature"

Request: *"Add the ability to share a document via a public link — anyone with the link can view it.
Button on the document page generates the link."*

**Answer key — must surface ≥6 of these critical gaps:**
- Link **expiry** (does it expire? configurable?)
- Link **revocation** (can the owner disable a live link?)
- **Access scope** (view-only vs comment/edit? the request says "view" — confirm/enforce)
- **Document deleted/moved** while a link is live (link → 404? graceful?)
- **Permissions** (who can generate a link — any viewer, or only owner/editor?)
- **Password / extra protection** option (or explicitly out of scope?)
- **Analytics / audit** (who viewed, how many times?)
- **Abuse / rate limiting** (link scraping, hotlinking, DoS)
- **Versioning** (does the link show the version at share-time or live?)

## FG2 — "Add CSV export to the reports page"

Request: *"Users want to export the current report as a CSV. Add an Export button that downloads a
CSV of the report data."*

**Answer key — must surface ≥6 of these critical gaps:**
- **Large datasets** (sync download vs async/streaming/pagination; timeout on big reports)
- **Which columns / scope** (visible columns only, or all underlying data? current filters applied?)
- **Encoding / delimiter / locale** (UTF-8 BOM for Excel, comma vs semicolon, decimal/date formats)
- **Empty data** (export with zero rows — header-only? error?)
- **Permissions** (can the user export everything they can see — any row-level access concerns?)
- **Concurrent / repeated exports** (debounce, double-click)
- **Special characters / CSV injection** (leading `=`/`+`/`-`/`@` formula-injection safety)
- **Filename / collision** (naming, timestamp)
- **Progress / failure feedback** (what if generation fails mid-way?)

## FG3 — "Add 'undo' to the bulk-delete action"

Request: *"After a user bulk-deletes items, show an 'Undo' toast so they can restore everything they
just deleted."*

**Answer key — must surface ≥6 of these critical gaps:**
- **Undo window** (how long is the toast / undo available? what after it dismisses?)
- **Where deleted state lives** during the window (soft-delete vs in-memory; survives refresh/navigation?)
- **Concurrent edits** (another user/tab modifies or deletes the same items during the window)
- **Partial restore** (some items can't be restored — dependencies, permission changed, child records)
- **Hard-delete timing** (when does deletion actually commit — immediately + restore, or deferred?)
- **Navigation / session end** mid-window (close tab → are items gone or restored?)
- **Multiple rapid bulk-deletes** (stacked undos? only the last? toast collision)
- **Side effects** of the deleted items (cascades, notifications, external sync already fired)
- **Accessibility / discoverability** of the undo affordance (keyboard, screen-reader, timeout for a11y)
