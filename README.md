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

Copy `.env.example` to `.env` and edit values as needed. Configuration loads that file with `python-dotenv`; environment variables override file values. Defaults are local dummy credentials only.

## Run the demo

In terminal 1: `python -m uvicorn app.mock_api:app --host 127.0.0.1 --port 8000`; open `http://127.0.0.1:8000/docs` to inspect the source API. A starter customer/order dataset and its separately stored expected summary are checked in under `data/sample/`.

In terminal 2: `python -m app.cli ingest`; inspect totals with `python -m app.cli report`; rerun to observe checkpoint behavior. `python -m app.cli ingest --backfill` deliberately starts from page 1 and relies on event idempotency. Reset demo state with `python -m app.cli reset --yes` (destructive: removes the configured SQLite database).

The mock API supports deterministic `retry-500-once`, `rate-limit-once`, `malformed-json-once`, `empty`, and `quality-mix` scenarios through `MOCK_SCENARIO`. For example, in PowerShell set `$env:MOCK_SCENARIO='retry-500-once'` before starting Uvicorn; on Unix use `MOCK_SCENARIO=retry-500-once python -m uvicorn app.mock_api:app`. Restart the service to reset its deterministic per-process fault counters. Normal mode is deterministic and succeeds.

Set `MOCK_RECORDS` for workload size, `PAGE_SIZE` for request pages, and `DATABASE_PATH`, `RAW_DIR`, `QUARANTINE_DIR`, `REPORTS_DIR`, `API_URL`, `API_TOKEN`, `REQUEST_TIMEOUT`, `MAX_RETRIES`, and `BACKOFF_BASE` for client configuration. Generate tracked starter data with `python -m app.cli generate --orders 25`; use `--scenario quality-mix` to generate labeled duplicate, conflict, missing-field, invalid-FK, late-event, and additive-schema cases. The expected-case summary is stored separately from source records. `MOCK_SCENARIO=empty` provides a true empty-source run.

## Data and operational behavior

See [architecture](docs/architecture.md), [data dictionary](docs/data_dictionary.md), [design decisions](docs/design_decisions.md), and [reconciliation SQL](docs/reconciliation.sql). Raw responses are retained in `artifacts/raw`; run reports are JSON in `artifacts/reports` (configurable with `REPORTS_DIR`). Record validation errors and foreign-key failures are persisted in SQLite and exported as one JSON Lines quarantine manifest per run under `artifacts/quarantine`. A page advances only after database writes commit. Failed pages are fetched again after restart. Page-number pagination cannot guarantee completeness against a changing upstream dataset; use snapshot IDs or stable cursors for such sources.

Customer email and required fields are validated; orders require non-negative decimal amounts, an allowlisted currency/status, timezone-aware timestamps, event IDs, and existing customers. Unknown additive fields are retained in raw pages and accepted for compatibility. Reconciliation compares raw source event IDs with durable event history, verifies current orders against latest event state and amount aggregates, and reports foreign-key failures.

## Tests and evidence

Run `python -m pytest -q`. The observed project test result is recorded in [validation results](docs/validation_results.md). To reproduce the larger run, set `MOCK_RECORDS=100000`, `PAGE_SIZE=1000`, and a fresh `DATABASE_PATH`, then start Uvicorn and run the CLI. PowerShell example: `$env:MOCK_RECORDS='100000'; $env:PAGE_SIZE='1000'; $env:DATABASE_PATH='data/benchmark.sqlite'; python -m uvicorn app.mock_api:app --host 127.0.0.1 --port 8000` in one terminal, then set the same database and page-size variables in terminal 2 and run `python -m app.cli ingest`. Unix example: `MOCK_RECORDS=100000 PAGE_SIZE=1000 DATABASE_PATH=data/benchmark.sqlite python -m uvicorn app.mock_api:app --host 127.0.0.1 --port 8000`; set the same client variables in terminal 2. The final-schema local run completed in 54.41 seconds (2,205.54 raw rows/second) on Python 3.14.6/Windows 11 with an 8 logical-core Intel host. This is an illustrative single run, not a controlled performance comparison.

Target entity row counts can differ from source rows: source rows may repeat event IDs, invalid records are quarantined, multiple events can update one order, and customers are separate entities. `order_events` preserves logical event history while `orders` contains one current row per order. A page-sized SQLite transaction is the primary throughput optimization; it amortizes commit cost while keeping target writes and checkpoint advancement atomic. The benchmark is not a controlled comparison against row-at-a-time commits.

## Submission status

This working tree has local Git commits but does not yet have a public GitHub remote. Do not claim the public repository requirement is complete until the candidate connects GitHub, selects the destination repository, and verifies that the push succeeded.

Sample raw API pages, labeled quality cases, and quarantine manifests are checked in under `data/sample/`; observed normal, quality-mix, and 100,000-order benchmark reports are under `artifacts/reports/`.
