
# Reliable API Data Ingestion Pipeline

A runnable local demonstration of reliable paginated API ingestion with bounded retries, rate-limit handling, raw-response retention, schema validation, record quarantine, SQLite event history, current-state publishing, and durable page checkpoints.

## 1. Project Overview

This project demonstrates how to build a reliable data ingestion pipeline that retrieves paginated order data from a mock REST API, validates incoming records, stores valid data, and preserves invalid records for investigation.

The pipeline is designed to support repeatable execution, controlled failure scenarios, checkpoint-based recovery, and reconciliation of source and target data.

### Key Features

- Paginated API ingestion
- Configurable authentication
- HTTP 429 and transient HTTP 500 retry handling
- Bounded retries with backoff
- Raw API response retention
- Schema and business-rule validation
- Duplicate detection and quarantine
- SQLite storage for current state and event history
- Durable page checkpoints
- Run reports and operational metrics
- Deterministic synthetic data generation
- Automated tests and performance measurement

## 2. Technology Stack

- **Language:** Python 3.11+
- **Mock API:** FastAPI and Uvicorn
- **HTTP client:** Requests
- **Validation:** Pydantic and application-level business rules
- **Storage:** SQLite
- **Testing:** Pytest
- **Data format:** JSON

The project is designed to run locally without paid cloud services or external API credentials.

## 3. Requirements and Setup

Python 3.11 or newer is required. The development environment used for the recorded execution was Python 3.14.6 on Windows.

### Windows PowerShell

Create and activate a virtual environment:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

### Unix/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Configuration

Copy `.env.example` to `.env` and configure the required values.

**Important:** The application reads environment variables directly and does not automatically load `.env`. Export the values in your shell or configure an appropriate environment loader if needed.

The default credentials are local dummy credentials. Never commit real tokens or secrets.

## 4. Running the Demo

Start the mock API in the first terminal:

```bash
python -m uvicorn app.mock_api:app --host 127.0.0.1 --port 8000
```

Keep the API running.

In a second terminal, activate the virtual environment and start ingestion:

```bash
python -m app.cli ingest
```

Generate a report:

```bash
python -m app.cli report
```

Run ingestion again to observe checkpoint behavior.

### Backfill

To deliberately start ingestion from the first page again:

```bash
python -m app.cli ingest --backfill
```

Backfill relies on event idempotency to prevent repeated logical events from being inserted unnecessarily.

### Reset Demo State

```bash
python -m app.cli reset --yes
```

**Warning:** Reset is destructive and removes the configured SQLite database. Back up any data you want to retain.

## 5. Simulating API Failures

The mock API supports controlled failure scenarios.

### Transient HTTP 500

Windows PowerShell:

```powershell
$env:MOCK_SCENARIO = 'retry-500-once'
python -m uvicorn app.mock_api:app --host 127.0.0.1 --port 8000
```

Unix/macOS:

```bash
MOCK_SCENARIO=retry-500-once python -m uvicorn app.mock_api:app --host 127.0.0.1 --port 8000
```

### HTTP 429 Rate Limit

Set the scenario to `rate-limit-once` using the same approach. The mock API returns a rate-limit response with a `Retry-After` header.

The client should respect retry limits and apply the configured retry policy.

Normal mode uses deterministic data and does not deliberately inject failures.

## 6. Configuration Options

The pipeline supports the following configuration variables:

| Variable | Purpose |
|---|---|
| `MOCK_RECORDS` | Synthetic workload size |
| `PAGE_SIZE` | Records requested per page |
| `DATABASE_PATH` | SQLite database location |
| `RAW_DIR` | Directory for raw API responses |
| `QUARANTINE_DIR` | Directory for quarantine artifacts |
| `API_URL` | Mock API base URL |
| `API_TOKEN` | Authentication token |
| `REQUEST_TIMEOUT` | HTTP request timeout |
| `MAX_RETRIES` | Maximum retry attempts |
| `BACKOFF_BASE` | Base delay for exponential backoff |

The data generator produces deterministic synthetic customers and orders.

**Empty-input limitation:** Setting `MOCK_RECORDS=0` does not currently produce a completely empty database input because the generator still creates a customer row. This should be considered when interpreting empty-batch tests.

## 7. Data Model and Validation

See the following documentation:

- [Architecture](docs/architecture.md)
- [Data Dictionary](docs/data_dictionary.md)
- [Design Decisions and Trade-offs](docs/design_decisions.md)
- [Validation Results](docs/validation_results.md)

### Data Quality Rules

The pipeline validates customer and order records.

Customer validation includes required fields and email format.

Order validation includes:

- Required identifiers and source event IDs
- Non-negative monetary amounts
- Allowed currency and status values
- Timezone-aware timestamps
- Referential integrity against existing customers

Invalid records and foreign-key failures are preserved for investigation rather than silently discarded.

### Raw Data and Quarantine

Raw API responses are retained under `artifacts/raw`.

Quarantine records are stored with validation or processing errors under the configured quarantine location. These artifacts help trace rejected data to its source.

Unknown additive fields are retained in raw responses and accepted for compatibility. A dedicated field-level schema-drift report is not currently implemented.

## 8. Checkpoints, Recovery and Idempotency

A page checkpoint advances only after the corresponding database writes have committed.

If processing fails before the checkpoint advances, the failed page can be fetched again after restart. Event-level idempotency is used to prevent repeated logical events from creating unintended duplicates.

The project supports backfill by restarting from the first page.

**Known limitation:** Page-number pagination alone cannot guarantee complete ingestion if the upstream dataset changes between requests. A production implementation should prefer stable cursors, source snapshots, or another source-supported consistency mechanism.

The pipeline also needs to account for the boundary between database transactions and file-based raw-response retention when recovering from partial failures.

## 9. Automated Tests

Run the test suite:

```bash
python -m pytest -q
```

The recorded test execution reported **12 passed**.

Refer to `docs/validation_results.md` for the recorded test and execution evidence. Rerun the tests in your own environment before submission and update the documentation if results differ.

## 10. Performance Measurement

The recorded benchmark for 100,000 orders reported:

| Metric | Recorded result |
|---|---:|
| Input orders | 100,000 |
| Page size | 1,000 |
| Elapsed time | 36.04 seconds |
| Reported throughput | 3,329.78 raw rows/second |
| Environment | Python 3.14.6, Windows |

These are results from one recorded run, not a controlled benchmark. Performance may vary with hardware, storage, configuration, and workload.

A reasonable optimization to evaluate is batched SQLite writes with appropriately selected indexes. Any claimed improvement should be supported by a repeatable before-and-after measurement.

## 11. Reconciliation

Source and target row counts do not necessarily match.

Differences can arise because:

- Duplicate source events are deduplicated.
- Invalid records are quarantined.
- Multiple events may update the same order.
- Customer records and order records represent separate entities.
- Event history preserves multiple logical changes while the current-state table stores one row per order.

Reconciliation should compare the appropriate grains and report accepted, rejected, duplicate, inserted, updated, and current-state counts separately.

## 12. Known Limitations

- The mock API does not reproduce every behavior of a real external API.
- Page-number pagination can be inconsistent when upstream data changes during ingestion.
- Dedicated field-level schema-drift reporting is not yet implemented.
- File-based raw retention and SQLite transactions do not share a single atomic transaction.
- The recorded benchmark represents one environment and workload.
- Empty-input generation requires refinement because a customer record is still generated when the configured order count is zero.

These limitations are documented so reviewers can distinguish demonstrated behavior from future improvements.

## 13. Future Improvements

Potential improvements include:

- Stable cursor or snapshot-based pagination
- More comprehensive schema-drift reporting
- Stronger recovery coordination between raw-file persistence and database transactions
- Additional fault-injection scenarios
- Controlled performance comparisons
- Structured monitoring and alerting for operational failures

## 14. AI Assistance Disclosure

AI tools were used during development for assistance with implementation, debugging, testing ideas, and documentation, where applicable.

The candidate should maintain the actual prompt history, review the implementation, rerun tests, validate the recorded results, and ensure that the final disclosure accurately reflects their contribution.

See `prompt_history/prompts.md` for the recorded prompts.

## 15. Repository Contents

The repository contains the pipeline source code, tests, configuration examples, sample data, generated artifacts, and supporting documentation.

Before submission, verify that the public GitHub repository includes the required files, contains no secrets or sensitive data, and can be cloned and executed using the documented instructions.