from app.storage import Store
import sqlite3

def test_schema_has_unique_event_key(tmp_path):
    s=Store(tmp_path/"x.db")
    with s.connect() as c:
        cols=[r[1] for r in c.execute("PRAGMA table_info(order_events)")]
    assert "source_event_id" in cols

def test_store_adds_trace_columns_to_older_database(tmp_path):
    path=tmp_path/"old.db"
    with sqlite3.connect(path) as c:
        c.execute("CREATE TABLE orders(order_id TEXT PRIMARY KEY,customer_id TEXT,amount TEXT,currency TEXT,status TEXT,updated_at TEXT,last_event_id TEXT)")
        c.execute("CREATE TABLE order_events(source_event_id TEXT PRIMARY KEY,order_id TEXT,customer_id TEXT,amount TEXT,currency TEXT,status TEXT,updated_at TEXT,payload_hash TEXT)")
    Store(path)
    with Store(path).connect() as c:
        assert {"source_page","ingestion_run_id"}.issubset({r[1] for r in c.execute("PRAGMA table_info(orders)")})
        assert {"source_page","ingestion_run_id"}.issubset({r[1] for r in c.execute("PRAGMA table_info(order_events)")})
