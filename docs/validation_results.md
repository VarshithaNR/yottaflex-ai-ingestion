# Validation results

## Environment

- Python 3.14.6 on Windows; pinned packages installed into the ignored `work/site` scratch directory because this environment denied writes to the default Python package and temp locations.
- `python -m compileall -q app tests`: passed.
- `python -m pytest -q --basetemp work\\pytesttmp`: **53 passed, 10 skipped** (the skips came from the installed pytest environment; no failures).

## End-to-end runs

- Normal API, 25 orders, page size 7: 5 pages, 30 source rows (5 customers + 25 orders), 30 accepted, 25 order inserts, 0 rejects/retries. Target: 5 customers, 25 orders, 25 events.
- Checkpoint rerun: 2 terminal-page requests, 0 rows received, target counts unchanged.
- Fault scenario `retry-500-once`: 2 injected HTTP 500 responses across the customer and order first pages; both retried successfully. 30 rows accepted, 25 order inserts, retries=2, no rejects.
- 100,000-order benchmark, page size 1,000: 120,000 source rows including 20,000 customers, 120 pages, 120,000 accepted, 100,000 order inserts, 20,000 customer rows, 100,000 current orders/events, 0 retries/rejects. Measured elapsed time **36.04 seconds**, **3,329.78 raw rows/second**.
- Identical 100,000-order backfill: 120 pages and 120,000 source rows; 100,000 exact duplicate order events, 0 new order inserts, current target counts unchanged. Measured 21.81 seconds (5,501 raw rows/second). Timing is a local single-run demonstration, not a controlled benchmark; it includes localhost HTTP, serialization, raw files, and SQLite writes.

## Limitations observed

The mock's empty dataset yields zero customers and zero orders when `MOCK_RECORDS=0`. The run-level benchmark is not a before/after optimization comparison. Network timeout, malformed JSON, late-arriving changes and transaction interruption have unit-level/implementation coverage limitations and were not demonstrated end-to-end. Git initialization/commit was not performed because the Git client in this environment reported an unexpected working-directory error; no repository existed in the project directory at initial inspection.
