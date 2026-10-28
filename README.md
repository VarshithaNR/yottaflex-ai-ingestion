# Reliable API Data Ingestion Pipeline

A runnable local demonstration of paginated order ingestion with bounded retries, raw page retention, validation, quarantine, SQLite event history/current state, and durable page checkpoints.

## Requirements and setup

Python 3.11+ (the inspected environment is Python 3.14.6). Create an environment and install pinned dependencies:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Unix/macOS: `python3 -m venv .venv && . .venv/bin/activate && python -m pip install -r requirements.txt`.

Copy `.env.example` to `.env` and export its values in your shell as needed. Defaults are local dummy credentials only. The app reads environment variables directly; it does not load `.env` automatically.

## Run the demo

In terminal 1: `python -m uvicorn app.mock_api:app --host 127.0.0.1 --port 8000`

In terminal 2: `python -m app.cli ingest`; inspect totals with `python -m app.cli report`; rerun to observe checkpoint behavior. `python -m app.cli ingest --backfill` deliberately starts from page 1 and relies on event idempotency. Reset demo state with `python -m app.cli reset --yes` (destructive: removes the configured SQLite database).

Inject one transient 500 by starting the API with `MOCK_SCENARIO=retry-500-once` (PowerShell: `$env:MOCK_SCENARIO='retry-500-once'`; Unix: `MOCK_SCENARIO=retry-500-once python -m uvicorn app.mock_api:app`). `rate-limit-once` injects a 429 with Retry-After. Normal mode is deterministic and succeeds.

Set `MOCK_RECORDS` for workload size, `PAGE_SIZE` for request pages, and `DATABASE_PATH`, `RAW_DIR`, `QUARANTINE_DIR`, `API_URL`, `API_TOKEN`, `REQUEST_TIMEOUT`, `MAX_RETRIES`, and `BACKOFF_BASE` for client configuration. The generator creates deterministic customers and orders. Empty mode can be exercised with `MOCK_RECORDS=0` (the generator still creates a customer row; see known limitations).

## Data and operational behavior

See [architecture](docs/architecture.md), [data dictionary](docs/data_dictionary.md), and [design decisions](docs/design_decisions.md). Raw responses are retained in `artifacts/raw`; run reports are JSON in `artifacts/reports`. Record validation errors and foreign-key failures are persisted to quarantine. A page advances only after database writes commit. Failed pages are fetched again after restart. Page-number pagination cannot guarantee completeness against a changing upstream dataset; use snapshot IDs or stable cursors for such sources.

Customer email and required fields are validated; orders require non-negative decimal amounts, an allowlisted currency/status, timezone-aware timestamps, event IDs, and existing customers. Unknown additive fields are observable in raw retention and accepted for compatibility. No field-level schema-drift report is currently emitted.

## Tests and evidence

Run `python -m pytest -q`. The observed environment result was 53 passed, 10 skipped. A local 100,000-order run completed in 36.04 seconds (3,329.78 raw rows/second) at page size 1,000 on Python 3.14.6/Windows; see [validation results](docs/validation_results.md) for counts and the repeat-run result. This is an illustrative single run, not a controlled performance comparison.

Target entity row counts can differ from source rows: source rows may repeat event IDs, invalid records are quarantined, multiple events can update one order, and customers are separate entities. `order_events` preserves logical event history while `orders` contains one current row per order.
