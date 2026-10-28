# Design decisions

- Page numbers keep the demo inspectable. The checkpoint means “next page to fetch” and is committed only after that page is handled. Use source snapshots/cursors when the source mutates during pagination.
- Current state is keyed by order ID; immutable event history is keyed by source event ID. Older events remain in history but do not overwrite a newer current state. Ties are resolved by lexicographically greater source event ID for deterministic results.
- Duplicate event IDs with identical payload hashes count as duplicates. Reuse with a different payload is quarantined.
- SQLite transactions cover target, quarantine, and checkpoint writes. Raw JSON retention is a separate filesystem operation; restart can safely re-fetch an uncheckpointed page.
- Rate limit and 5xx/network errors retry within a bounded budget; ordinary 4xx and malformed JSON fail the run.
- Unknown schema fields are allowed by Pydantic and retained in raw responses, avoiding ingestion outage for additive changes. Required fields remain validated.
- Synthetic generation is deterministic and uses only the standard library. No service credentials are needed.
- One transaction handles each source page, reducing SQLite commit overhead while keeping its target writes and checkpoint advancement atomic. The larger run demonstrates throughput, but no controlled row-at-a-time baseline was measured.
