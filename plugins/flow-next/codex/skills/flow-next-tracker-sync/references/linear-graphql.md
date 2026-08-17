# Linear GraphQL transport shape

Flowctl sends JSON GraphQL documents to Linear's GraphQL endpoint. Variables
carry every identifier and user-authored value. The executor attaches the API
key and applies timeout, retry, classification, and redaction policy.

## Addressing

- durable issue address: Linear UUID;
- display address: team key plus issue number;
- destination scope: resolved team UUID and key;
- status scope: resolved workflow-state ids;
- label and assignee values: resolved provider ids.

## Operation mapping

| Wire verb | GraphQL shape |
|---|---|
| `read` | issue selection by UUID |
| `update` | issue update mutation with supplied fields only |
| `comment-add` | comment create mutation |
| `comment-list` | cursor-paginated comments |
| `comment-update` | comment update mutation |
| `comment-delete` | comment delete mutation |
| `label` | issue label id set |
| `assign` | issue assignee id set |
| `list-open` | cursor-paginated issues in resolved team/ready state |
| `list-states` | single `workflowStates` page (100) + `complete` flag; read-only |
| `attach` | upload negotiation plus presigned anonymous byte upload |
| `attach-get` | authenticated metadata lookup, then safe download policy |

Status uses the resolved workflow-state id. Relations use Linear's native issue
relation shape. Bodies and comments normalize as Markdown.

GraphQL top-level errors, missing `data`, malformed selections, and HTTP
failures are normalized into the common structured envelope. Callers never
parse GraphQL error text.
