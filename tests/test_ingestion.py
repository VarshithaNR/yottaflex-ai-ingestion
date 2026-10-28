import json
from types import SimpleNamespace
from app.generator import make_dataset
from app.ingestion import ingest
from app.storage import Store

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
