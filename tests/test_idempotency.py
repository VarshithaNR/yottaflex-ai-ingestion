from app.storage import Store

def test_schema_has_unique_event_key(tmp_path):
    s=Store(tmp_path/"x.db")
    with s.connect() as c:
        cols=[r[1] for r in c.execute("PRAGMA table_info(order_events)")]
    assert "source_event_id" in cols
