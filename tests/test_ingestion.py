import json
from pathlib import Path
from types import SimpleNamespace
from app.generator import make_dataset
from app.ingestion import ingest
from app.storage import Store
from app.client import APIError
from app.generator import make_quality_dataset
import pytest

class Client:
    def __init__(self,data): self.data=data; self.retries=0
    def get_page(self,stream,page,size):
        rows=self.data[stream]; start=(page-1)*size
        return {"items":rows[start:start+size],"has_more":start+size<len(rows)}

def test_happy_empty_duplicate_and_checkpoint(tmp_path,monkeypatch):
    data=make_dataset(3); data["orders"].append(dict(data["orders"][0]))
    cfg=SimpleNamespace(database_path=str(tmp_path/"db.sqlite"),raw_dir=str(tmp_path/"raw"),quarantine_dir=str(tmp_path/"q"),api_url="unused",api_token="x",timeout=1,max_retries=1,backoff_base=0,page_size=2)
    monkeypatch.setattr("app.ingestion.APIClient",lambda *a:Client(data))
    m=ingest(cfg)
    assert m["raw_records"]==5 and m["orders"]==3 and m["order_events"]==3
    assert m["duplicates"]==1
    assert Store(cfg.database_path).checkpoint("orders")==3
    m2=ingest(cfg)
    assert m2["raw_records"]==0

def test_unknown_customer_quarantined(tmp_path,monkeypatch):
    data=make_dataset(1); data["orders"][0]["customer_id"]="MISSING"
    cfg=SimpleNamespace(database_path=str(tmp_path/"db.sqlite"),raw_dir=str(tmp_path/"raw"),quarantine_dir=str(tmp_path/"q"),api_url="unused",api_token="x",timeout=1,max_retries=1,backoff_base=0,page_size=10)
    monkeypatch.setattr("app.ingestion.APIClient",lambda *a:Client(data))
    m=ingest(cfg)
    assert m["rejected_records"]==1 and m["orders"]==0

def test_conflicting_event_and_late_arriving_event(tmp_path,monkeypatch):
    data=make_dataset(1)
    first=data["orders"][0]
    conflict=dict(first,amount="999.99")
    late=dict(first,source_event_id="EVT-late",status="refunded",updated_at="2024-01-01T00:00:00+00:00")
    newer=dict(first,source_event_id="EVT-new",status="shipped",updated_at="2025-02-01T00:00:00+00:00")
    data["orders"]=[first,conflict,late,newer]
    cfg=SimpleNamespace(database_path=str(tmp_path/"db.sqlite"),raw_dir=str(tmp_path/"raw"),quarantine_dir=str(tmp_path/"q"),api_url="unused",api_token="x",timeout=1,max_retries=1,backoff_base=0,page_size=10)
    monkeypatch.setattr("app.ingestion.APIClient",lambda *a:Client(data))
    metrics=ingest(cfg)
    assert metrics["rejected_records"]==1
    with Store(cfg.database_path).connect() as c:
        order=c.execute("SELECT status,last_event_id FROM orders").fetchone()
        assert tuple(order)==("shipped","EVT-new")
        assert c.execute("SELECT COUNT(*) FROM order_events").fetchone()[0]==3

def test_failed_page_restarts_from_durable_checkpoint(tmp_path,monkeypatch):
    data=make_dataset(3)
    class FailPageTwo(Client):
        def get_page(self,stream,page,size):
            if stream=="orders" and page==2 and not getattr(self,"failed",False):
                self.failed=True
                raise APIError("injected failure")
            return super().get_page(stream,page,size)
    instance=FailPageTwo(data)
    cfg=SimpleNamespace(database_path=str(tmp_path/"db.sqlite"),raw_dir=str(tmp_path/"raw"),quarantine_dir=str(tmp_path/"q"),api_url="unused",api_token="x",timeout=1,max_retries=1,backoff_base=0,page_size=2)
    monkeypatch.setattr("app.ingestion.APIClient",lambda *a:instance)
    with pytest.raises(APIError): ingest(cfg)
    assert Store(cfg.database_path).checkpoint("orders")==2
    with Store(cfg.database_path).connect() as c:
        status,failure=c.execute("SELECT status,failure FROM ingestion_runs ORDER BY started_at DESC LIMIT 1").fetchone()
    assert status=="failed" and "injected failure" in failure
    metrics=ingest(cfg)
    assert metrics["orders"]==3
    assert Store(cfg.database_path).checkpoint("orders")==3

def test_empty_input_finishes_with_zero_rows(tmp_path,monkeypatch):
    cfg=SimpleNamespace(database_path=str(tmp_path/"db.sqlite"),raw_dir=str(tmp_path/"raw"),quarantine_dir=str(tmp_path/"q"),api_url="unused",api_token="x",timeout=1,max_retries=1,backoff_base=0,page_size=10)
    monkeypatch.setattr("app.ingestion.APIClient",lambda *a:Client({"customers":[],"orders":[]}))
    metrics=ingest(cfg)
    assert metrics["raw_records"]==0 and metrics["rejected_records"]==0
    assert metrics["customers"]==metrics["orders"]==metrics["order_events"]==0

def test_quality_mix_is_repeatable_and_quarantines_labelled_cases(tmp_path,monkeypatch):
    data=make_quality_dataset(1)
    cfg=SimpleNamespace(database_path=str(tmp_path/"db.sqlite"),raw_dir=str(tmp_path/"raw"),quarantine_dir=str(tmp_path/"q"),reports_dir=str(tmp_path/"reports"),api_url="unused",api_token="x",timeout=1,max_retries=1,backoff_base=0,page_size=20)
    monkeypatch.setattr("app.ingestion.APIClient",lambda *a:Client(data))
    metrics=ingest(cfg)
    assert metrics["duplicates"]==1
    assert metrics["rejected_records"]==3
    assert metrics["orders"]==1 and metrics["order_events"]==2
    assert metrics["unexpected_source_fields"]["unexpected_source_flag"]==6
    assert metrics["referential_integrity_failures"]==0
    assert metrics["current_orders_match_latest_event_state"]
    quarantine=Path(metrics["quarantine_file"]).read_text(encoding="utf-8").splitlines()
    assert len(quarantine)==3
