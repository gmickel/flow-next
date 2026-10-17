# Diagnose a captured artifact (gated reference)

> **Loaded only when** the route is a captured artifact to explain: a CPU profile, a performance
> trace, a heap snapshot, a crash dump or a similar recording, handed over with a why or what
> question and no request for a fix.

The deliverable is a diagnosis, not a change. Write no fix, no `.flow/` file and no pull request.

- **Make it queryable.** Load the artifact with tools the repository or host already has (the
  profiler's own export or command line, `jq`, a throwaway SQLite table in scratch, the runtime's
  developer tools). Install nothing to read it; an artifact nothing available can read is named
  as unreadable, with the export that would work or a live reproduction as the next step.
- **Answer the question it was handed with.** Name what bounds the cost, what holds the memory, or
  where the crash happened, and map it to source. When the artifact was recorded at another
  revision than the checkout, say which findings depend on code that has changed since.
- **Call it what the evidence supports.** A cause is confirmed only by a before-and-after pair or
  a reproduction; otherwise it is the strongest supported hypothesis, and the answer says so.
- **Quote sparingly.** From a dump that can hold secrets or personal data, quote only what the
  diagnosis needs.
- **End with `Next:`** naming the route that would act on it: measured slowness, hill climb, or
  the defect route, with the artifact as its baseline evidence.

Example: a `boot.cpuprofile` with "why does the first window take six seconds?" Loaded into
per-function rows, a synchronous directory walk takes 2.1 s and a settings-cache parse 1.4 s. The
walk maps to the plugin loader scanning the whole user data folder; thousands of per-file stat
calls against a handful of plugin loads make an over-broad scan the strongest supported
hypothesis. The loader is unchanged since the recording, the cache code is not, and the answer
says so. `Next:` the hill-climb route on first-window time.
