from app.storage import Store
from app.reporting import build_run_report
from app.generator import make_dataset
from app.ingestion import ingest
from types import SimpleNamespace

class Client:
    def __init__(self,data): self.data=data; self.retries=0
    def get_page(self,stream,page,size):
        return {"items":self.data[stream],"has_more":False}

def test_empty_counts(tmp_path):
    assert Store(tmp_path/"x.db").counts()=={"customers":0,"orders":0,"order_events":0}

def test_run_report_reconciles_source_and_latest_event_state(tmp_path,monkeypatch):
    data=make_dataset(2)
    cfg=SimpleNamespace(database_path=str(tmp_path/"db.sqlite"),raw_dir=str(tmp_path/"raw"),quarantine_dir=str(tmp_path/"q"),reports_dir=str(tmp_path/"reports"),api_url="unused",api_token="x",timeout=1,max_retries=1,backoff_base=0,page_size=10)
    monkeypatch.setattr("app.ingestion.APIClient",lambda *a:Client(data))
    run=ingest(cfg)
    assert run["source_unique_event_ids_this_run"]==2
    assert run["source_event_ids_not_in_target_history"]==0
    assert run["referential_integrity_failures"]==0
    assert run["current_orders_match_latest_event_state"]
    assert all(run["current_order_amounts_match_event_history_by_currency"].values())
    with Store(cfg.database_path).connect() as c:
        page,run_id=c.execute("SELECT source_page,ingestion_run_id FROM orders LIMIT 1").fetchone()
        assert page==1 and run_id==run["run_id"]
