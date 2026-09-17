# Memory without a scout spawn

When `memory.enabled` is true, run `$FLOWCTL memory search "<task or planning query>" --rerank --json` directly. Use relevant module/category filters as before; status remains active, excluding stale and hardened entries. One request scores the top 15 hits; consume the returned order and do not rerank it in the host.

When `rerank` is `jev`, replace the memory-scout dispatch with the returned findings: render `## Memory findings` and the unchanged `Track | Category | Entry | Why relevant` table, one short title/relevance bullet per entry, no bodies. Print the returned `stage_line`: `memory: reranked (jev, <input count> -> <count>)`. Zero hits needs no judge or scout and renders the existing no-relevant-entries result.

When `rerank` is `bm25` because the judge is unavailable, print the returned `stage_line`, `memory: bm25 (jev-unavailable(<rerank_reason>))` and dispatch `flow-next:memory-scout` as before, passing the BM25 result and unavailability reason so it does not retry the judge for that same query. A failed search is `Memory scan FAILED: <first error line>`, never an empty-memory claim. The scout retains the existing module, deduplication and recency rules and table format.

Consume the JSON without changing its ordering. `spawn_memory_scout` selects the fallback dispatch; `memory_matches` supplies either the direct table or that scout's input:

```python
# fence:judge-memory-consumer
memory_matches = result["matches"]
spawn_memory_scout = result["rerank"] == "bm25" and bool(memory_matches)
memory_line = result["stage_line"]
```

For work, store the findings in the existing run temporary area and pass its `MEMORY_FINDINGS` path; plan consumes the table directly. A retrieval with no hits is complete regardless of judge availability.
