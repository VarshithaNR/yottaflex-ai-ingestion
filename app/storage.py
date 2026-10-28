"""SQLite persistence with atomic target/checkpoint transactions."""
import json, sqlite3
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS customers(customer_id TEXT PRIMARY KEY,name TEXT NOT NULL,email TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS orders(order_id TEXT PRIMARY KEY,customer_id TEXT NOT NULL REFERENCES customers(customer_id),amount TEXT NOT NULL,currency TEXT NOT NULL,status TEXT NOT NULL,updated_at TEXT NOT NULL,last_event_id TEXT NOT NULL,source_page INTEGER NOT NULL,ingestion_run_id TEXT NOT NULL REFERENCES ingestion_runs(run_id));
CREATE TABLE IF NOT EXISTS order_events(source_event_id TEXT PRIMARY KEY,order_id TEXT NOT NULL,customer_id TEXT NOT NULL REFERENCES customers(customer_id),amount TEXT NOT NULL,currency TEXT NOT NULL,status TEXT NOT NULL,updated_at TEXT NOT NULL,payload_hash TEXT NOT NULL,source_page INTEGER NOT NULL,ingestion_run_id TEXT NOT NULL REFERENCES ingestion_runs(run_id));
CREATE INDEX IF NOT EXISTS ix_events_order ON order_events(order_id,updated_at);
CREATE TABLE IF NOT EXISTS ingestion_runs(run_id TEXT PRIMARY KEY,started_at TEXT NOT NULL,ended_at TEXT,status TEXT NOT NULL,pages_fetched INTEGER DEFAULT 0,raw_records INTEGER DEFAULT 0,accepted_records INTEGER DEFAULT 0,inserted_records INTEGER DEFAULT 0,updated_records INTEGER DEFAULT 0,duplicates INTEGER DEFAULT 0,rejected_records INTEGER DEFAULT 0,retries INTEGER DEFAULT 0,elapsed_seconds REAL,failure TEXT);
CREATE TABLE IF NOT EXISTS checkpoints(stream TEXT PRIMARY KEY,next_page INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS quarantined_records(id INTEGER PRIMARY KEY,run_id TEXT,stream TEXT,page INTEGER,record_json TEXT,reason TEXT,created_at TEXT);
"""

class Store:
    def __init__(self, path):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as c:
            c.executescript(SCHEMA)
            self._ensure_column(c,"orders","source_page","INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(c,"orders","ingestion_run_id","TEXT NOT NULL DEFAULT ''")
            self._ensure_column(c,"order_events","source_page","INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(c,"order_events","ingestion_run_id","TEXT NOT NULL DEFAULT ''")
    @staticmethod
    def _ensure_column(connection, table, name, definition):
        if name not in {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
    def connect(self):
        c=sqlite3.connect(self.path); c.row_factory=sqlite3.Row; c.execute("PRAGMA foreign_keys=ON"); return c
    def checkpoint(self, stream):
        with self.connect() as c:
            r=c.execute("SELECT next_page FROM checkpoints WHERE stream=?",(stream,)).fetchone()
            return r[0] if r else 1
    def save_page(self, stream, page, callback):
        with self.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            callback(c)
            c.execute("INSERT INTO checkpoints(stream,next_page) VALUES(?,?) ON CONFLICT(stream) DO UPDATE SET next_page=excluded.next_page",(stream,page+1))
    def counts(self):
        with self.connect() as c:
            return {t:c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("customers","orders","order_events")}
