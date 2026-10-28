# Validation results

## Environment

- Python 3.14.6, Windows 11, Intel 8 logical-core host; pinned packages installed into the ignored `work/site` scratch directory because this environment denied writes to the default Python package and temp locations. Package versions: FastAPI 0.115.12, Uvicorn 0.34.2, Requests 2.32.3, Pydantic 2.12.4, Pytest 8.3.5. Physical-memory details were unavailable from the restricted host.
- `python -m compileall -q app tests`: passed.
- `python -m pytest -q` (project `testpaths=tests`): **22 passed, 0 skipped**.

## End-to-end runs

- Normal API, 25 orders, page size 7: 5 pages, 30 source rows (5 customers + 25 orders), 30 accepted, 25 order inserts, 0 rejects/retries. Target: 5 customers, 25 orders, 25 events.
- Checkpoint rerun: 2 terminal-page requests, 0 rows received, target counts unchanged.
- Fault scenario `retry-500-once`: 2 injected HTTP 500 responses across the customer and order first pages; both retried successfully. 30 rows accepted, 25 order inserts, retries=2, no rejects.
- 100,000-order benchmark, page size 1,000: 120,000 source rows including 20,000 customers, 120 pages, 120,000 accepted, 100,000 order inserts, 20,000 customer rows, 100,000 current orders/events, 0 retries/rejects. With final schema and reconciliation enabled, measured **54.41 seconds**, **2,205.54 raw rows/second**; 100,000 unique event IDs matched target history and current-state/amount aggregates reconciled.
- Identical 100,000-order backfill: 120 pages and 120,000 source rows; 100,000 exact duplicate order events, 0 new order inserts, current target counts unchanged. Measured **56.43 seconds**, **2,126.39 raw rows/second**. Both timings are local single-run demonstrations, not controlled comparisons; they include localhost HTTP, serialization, raw files, reconciliation, and SQLite writes.
- Current normal sample run: 30 raw customer/order rows, 30 accepted, 25 orders inserted, 0 rejects/duplicates, 25 unique source event IDs found in target history, no unmatched event IDs or foreign-key failures, current state and event totals reconciled. Amount total was USD 11,281.88.
- Current `quality-mix` run: 35 source rows, 32 accepted, 3 rejected, 1 exact duplicate, 25 current orders and 26 history events. The two unique IDs absent from history were the invalid-FK event and the missing-status event; the conflicting duplicate reuses an existing ID and is quarantined. Six source occurrences included an additive field. Referential integrity was clean and current-state/event aggregates matched.
- Checked-in output examples are `artifacts/reports/example_run.json`, `artifacts/reports/example_quality_mix.json`, and `artifacts/reports/example_benchmark.json`; their quarantine JSONL manifests are under `data/sample/quarantine/`. Normal and quality-mix raw pages and expected-case labels are in `data/sample/`.

## Limitations observed

The run-level benchmark is not a before/after optimization comparison. Network timeout is covered by a deterministic transport unit test but was not demonstrated against a live server. The local repository has commits; it has no GitHub remote and has not been published. This is an explicit submission blocker until a GitHub destination is connected and push is verified.
