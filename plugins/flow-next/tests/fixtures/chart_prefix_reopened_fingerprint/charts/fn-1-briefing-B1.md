# fn-1 briefing B1

**Briefing:** B1
**Status:** final
**Chart:** fn-1 - Tenant isolation
**Chart status:** open

## Outcome

Ready to capture

## Decisions

- **fn-1.D1:** Storage choice - Use Postgres for tenant metadata - [record](.flow/charts/fn-1/1.md)
- **fn-1.D2:** Auth model - OIDC with per-tenant issuers - [record](.flow/charts/fn-1/2.md)

## Superseded decisions

(none)

## Ledger (chart)

<!-- the ledger: one line per resolved decision, append-only, D-IDs never reused -->

- **D1:** Use Postgres for tenant metadata -- [record](.flow/charts/fn-1/1.md)
- **D2:** OIDC with per-tenant issuers -- [record](.flow/charts/fn-1/2.md)

## Boundaries

(none)

## Assets

(none)

## Clusters

- **cluster 1:** Single captureable surface - decisions: fn-1.D1, fn-1.D2

## Shared context

(none)
