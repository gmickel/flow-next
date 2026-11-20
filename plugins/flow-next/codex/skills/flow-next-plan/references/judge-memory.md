# Memory in one search

When `memory.enabled` is true, run one search on a sentence that states the task (add a module or category filter when the task names one; status stays active, which excludes stale and hardened entries):

```bash
$FLOWCTL memory search "<task sentence>" --limit 15 --rerank --json
```

The same command serves both paths. Without a key, or with the judge off or failing, the matches come back in BM25 order; with a key, Jev reorders the same entries (`jev_score`, `jev_rank`) and drops none. Either way, read the titles and snippets and keep the entries whose lesson applies to this task; that choice is yours on both paths, and `$FLOWCTL memory read <entry-id>` settles a snippet that is not enough. Print the returned `stage_line`.

Render `## Memory findings` with the `Track | Category | Entry | Why relevant` table and one short title/relevance bullet per kept entry, no bodies. Nothing kept, or no matches, renders `No relevant entries in project memory.` A search that reports memory is not initialized renders one line, `Memory is enabled but not initialized (flowctl memory init sets it up).`, in place of the findings. Any other failed search is `Memory scan FAILED: <first error line>`, never an empty-memory claim. Do not spawn `flow-next:memory-scout` for this; the search is the whole retrieval.
