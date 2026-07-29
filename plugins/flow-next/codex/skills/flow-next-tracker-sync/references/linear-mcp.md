# Linear MCP shape

MCP is one of the five retained judgment surfaces because its tools exist only
in the host agent environment. Flowctl cannot invoke them.

## Allowed use

- discover accessible Linear teams and projects during the confirmed ceremony;
- create an issue only when the user authorized that action and no
 shell-reachable Linear credential can complete it;
- return the created issue identity to deterministic persistence.

MCP does not perform routine update, status, comment, relation, attachment,
pull, or reconcile operations. Those use flowctl's GraphQL transport.

## Handoff

Capture the MCP result as:

```json
{"identifier": "TEAM-123", "id": "optional durable UUID", "url": "optional canonical URL"}
```

Then call `tracker persist-external` with source `mcp`. If the durable id is
missing, flowctl resolves the display identifier before persisting it. Failure
to resolve leaves local link state unchanged.

Never copy OAuth tokens, tool metadata, or raw MCP diagnostics into Flow state
or receipts.
