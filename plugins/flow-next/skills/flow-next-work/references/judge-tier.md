# Judge at dispatch

Before each worker or scout spawn, ask once with `$FLOWCTL judge --preset tier --state-file <tier-state.json> --json`. Assemble `task_title`, `task_body`, `acceptance`, `touches_count`, `has_quick_commands`, and `repo` from the task and repository (for a scout, its actual bounded assignment). Keep the result for this admission; never reroute a running worker. A rolling admission consumes this same decision in Phase 3c, without a second call.

Use the preset's decision, not a second host classification. The following selector takes the judge JSON (`result`), an explicit invocation model (`explicit_model`, or null), the routing block's fast-scout model (`fast_model`, or null), and the host's verified reach (`can_spawn_model`, `can_bridge`). It returns the dispatch fields and line:

```python
# fence:judge-tier-dispatch
selected_model = None
implementer = explicit_model
if not result["available"]:
    tier_line = "Tier: session (jev-unavailable(%s))" % result["reason"]
else:
    answer = result["answers"]["tier"]
    value = result["decision"]["value"]
    confidence = answer["confidence"]
    if value == "mechanical" and not explicit_model:
        if fast_model and (can_spawn_model or can_bridge):
            selected_model = fast_model if can_spawn_model else None
            implementer = fast_model
            tier_line = "Tier: mechanical (jev %.2f) -> %s" % (confidence, fast_model)
        else:
            reason = "no fast-scout model" if not fast_model else "no spawn-model parameter or bridge"
            tier_line = "Tier: mechanical (jev %.2f) -> session (%s)" % (confidence, reason)
    elif value == "long_running":
        tier_line = "Tier: long_running (jev %.2f) - bridge recommended" % confidence
    else:
        tier_line = "Tier: session (jev %s %.2f)" % (answer["choice"], confidence)
    if explicit_model:
        tier_line += " (explicit IMPLEMENTER preserved)"
spawn_model_args = {"model": selected_model} if selected_model else {}
```

Expand `spawn_model_args` into the Task invocation so the selected model reaches its **`model` parameter**; on another host map that field to its equivalent spawn-model parameter. Also pass `IMPLEMENTER: <implementer>` in the worker prompt when set. The prompt alone never selects a native model. For bridge-only reach, leave the native spawn unchanged and let worker Phase 1b resolve the `IMPLEMENTER` bridge. An explicit invocation remains authoritative; the selector never changes its existing spawn routing. Scouts use the same native selection with the host's read-only restrictions preserved; on bridge-only reach without a scout bridge, retain the existing scout model and state that limitation.

Print `tier_line` at dispatch and retain it in the task's done summary (or scout findings). After return append `(model: <actual_model>)` only when the returned model is backed by host execution metadata or the worker's actual bridge command. Missing model evidence gets no model annotation; never copy the requested model into the actual-model field. A long-running recommendation is advisory and creates no bridge or approval requirement.
