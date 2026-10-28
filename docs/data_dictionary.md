# Data dictionary

| Table | Grain and key | Important constraints |
|---|---|---|
| customers | One current customer per `customer_id` | Name/email/created_at required |
| orders | One current order per `order_id` | Customer FK; greatest `(updated_at, source_event_id)` wins; stores last event page and run ID |
| order_events | One source event per `source_event_id` | Immutable payload hash detects conflicting reuse; includes source page and run ID |
| checkpoints | One next page per stream | Advanced in same SQLite transaction as that page |
| ingestion_runs | One row per attempted run | Operational counters and failure detail |
| quarantined_records | One rejected record occurrence | Run, stream, page, record, reason, UTC time |

Amounts are decimal strings with two fractional digits. Timestamps are normalized to UTC. Event uniqueness is distinct from current-order uniqueness: many events can update one order. Source page is represented in raw artifact filenames and quarantine rows; ingestion run is separately tracked.

`artifacts/reports/<run_id>.json` includes source event keys found in history, current target counts, orphan-key count, current-state-versus-event-history comparison, and amount totals by currency. SQL checks are in [`reconciliation.sql`](reconciliation.sql).
