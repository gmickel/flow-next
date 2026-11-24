# Prove Live

Run this on spec and goal work whose acceptance criteria describe observable user behaviour, and whenever a defect is reproduced live. A direct change reports "not verified live" unless the person asked.

A pass rests on evidence captured from the running app, never on reading source or concluding the diff looks right. Reading source to explain an observed failure is fine; reading source to claim a pass is not.

Follow the repo's run-and-prove page to start the app, sign in, and read its logs. Drive each scenario with the host's browser tool (including Chromium-backed desktop apps over a debug port) or computer-use tool when present. Re-snapshot after page changes, check visible state alongside console errors, failed network requests, and app logs where available, and close sessions or processes you started when done.

Evidence means observed live output: screenshots, captured state or responses, console and network checks, and log lines. A clean screen with a console error or failed request fails. Put the evidence in the PR body under `## What changes`.

If the app cannot start, sign-in is unavailable, or a native app has no suitable tool, report inconclusive—never passed—and state what could not be exercised as plainly as what worked.
