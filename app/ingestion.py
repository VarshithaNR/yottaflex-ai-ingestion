"""Page ingestion coordinator."""
from datetime import datetime, timezone
import hashlib, json, logging, time, uuid
from pathlib import Path
from .client import APIClient
from .storage import Store
from .validation import validate_customer, validate_order

log=logging.getLogger(__name__)
def utcnow(): return datetime.now(timezone.utc).isoformat()

def ingest(config, streams=("customers","orders"), backfill=False):
    run_id=str(uuid.uuid4()); started=time.monotonic(); store=Store(config.database_path)
    raw_dir=Path(config.raw_dir); quarantine_dir=Path(config.quarantine_dir); raw_dir.mkdir(parents=True,exist_ok=True); quarantine_dir.mkdir(parents=True,exist_ok=True)
    client=APIClient(config.api_url,config.api_token,config.timeout,config.max_retries,config.backoff_base)
    metrics={"run_id":run_id,"pages_fetched":0,"raw_records":0,"accepted_records":0,"inserted_records":0,"updated_records":0,"duplicates":0,"rejected_records":0,"retries":0}
    with store.connect() as c: c.execute("INSERT INTO ingestion_runs(run_id,started_at,status) VALUES(?,?,?)",(run_id,utcnow(),"running"))
    try:
        for stream in streams:
            page=1 if backfill else store.checkpoint(stream)
            while True:
                payload=client.get_page(stream,page,config.page_size)
                raw_path=raw_dir/f"{run_id}_{stream}_{page}.json"
                raw_path.write_text(json.dumps(payload,sort_keys=True),encoding="utf-8")
                rows=payload.get("items")
                if not isinstance(rows,list): raise ValueError(f"{stream} page {page}: items must be a list")
                metrics["pages_fetched"]+=1; metrics["raw_records"]+=len(rows)
                accepted=[]; rejects=[]; duplicates=0
                for record in rows:
                    parsed,err=(validate_customer(record) if stream=="customers" else validate_order(record))
                    if err: rejects.append((record,err)); continue
                    accepted.append(parsed)
                def persist(c):
                    nonlocal duplicates
                    for record,reason in rejects:
                        c.execute("INSERT INTO quarantined_records(run_id,stream,page,record_json,reason,created_at) VALUES(?,?,?,?,?,?)",(run_id,stream,page,json.dumps(record,default=str),reason,utcnow()))
                    for rec in accepted:
                        if stream=="customers":
                            c.execute("INSERT INTO customers VALUES(?,?,?,?) ON CONFLICT(customer_id) DO UPDATE SET name=excluded.name,email=excluded.email,created_at=excluded.created_at",(rec["customer_id"],rec["name"],rec["email"],rec["created_at"]))
                            continue
                        if not c.execute("SELECT 1 FROM customers WHERE customer_id=?",(rec["customer_id"],)).fetchone():
                            rejects.append((rec,"unknown customer_id")); c.execute("INSERT INTO quarantined_records(run_id,stream,page,record_json,reason,created_at) VALUES(?,?,?,?,?,?)",(run_id,stream,page,json.dumps(rec),"unknown customer_id",utcnow())); continue
                        digest=hashlib.sha256(json.dumps(rec,sort_keys=True).encode()).hexdigest()
                        old=c.execute("SELECT payload_hash FROM order_events WHERE source_event_id=?",(rec["source_event_id"],)).fetchone()
                        if old:
                            if old[0]==digest: duplicates+=1
                            else:
                                c.execute("INSERT INTO quarantined_records(run_id,stream,page,record_json,reason,created_at) VALUES(?,?,?,?,?,?)",(run_id,stream,page,json.dumps(rec),"conflicting source_event_id",utcnow()))
                                rejects.append((rec,"conflicting source_event_id"))
                            continue
                        c.execute("INSERT INTO order_events VALUES(?,?,?,?,?,?,?,?)",(rec["source_event_id"],rec["order_id"],rec["customer_id"],rec["amount"],rec["currency"],rec["status"],rec["updated_at"],digest))
                        current=c.execute("SELECT updated_at FROM orders WHERE order_id=?",(rec["order_id"],)).fetchone()
                        if not current or rec["updated_at"]>=current[0]:
                            if current: metrics["updated_records"]+=1
                            else: metrics["inserted_records"]+=1
                            c.execute("INSERT INTO orders VALUES(?,?,?,?,?,?,?) ON CONFLICT(order_id) DO UPDATE SET customer_id=excluded.customer_id,amount=excluded.amount,currency=excluded.currency,status=excluded.status,updated_at=excluded.updated_at,last_event_id=excluded.last_event_id",(rec["order_id"],rec["customer_id"],rec["amount"],rec["currency"],rec["status"],rec["updated_at"],rec["source_event_id"]))
                store.save_page(stream,page,persist)
                metrics["accepted_records"]+=len(accepted)-sum(1 for _,e in rejects if e=="unknown customer_id")
                metrics["rejected_records"]+=len(rejects); metrics["duplicates"]+=duplicates
                if not payload.get("has_more"): break
                page+=1
        metrics["retries"]=client.retries; elapsed=time.monotonic()-started
        with store.connect() as c: c.execute("UPDATE ingestion_runs SET ended_at=?,status='succeeded',pages_fetched=?,raw_records=?,accepted_records=?,inserted_records=?,updated_records=?,duplicates=?,rejected_records=?,retries=?,elapsed_seconds=? WHERE run_id=?",(utcnow(),metrics["pages_fetched"],metrics["raw_records"],metrics["accepted_records"],metrics["inserted_records"],metrics["updated_records"],metrics["duplicates"],metrics["rejected_records"],metrics["retries"],elapsed,run_id))
        metrics.update(store.counts()); metrics["elapsed_seconds"]=elapsed; metrics["records_per_second"]=metrics["raw_records"]/elapsed if elapsed else 0
        (Path("artifacts/reports")/f"{run_id}.json").parent.mkdir(parents=True,exist_ok=True)
        Path("artifacts/reports",f"{run_id}.json").write_text(json.dumps(metrics,indent=2),encoding="utf-8")
        return metrics
    except Exception as exc:
        with store.connect() as c: c.execute("UPDATE ingestion_runs SET ended_at=?,status='failed',failure=?,pages_fetched=?,raw_records=?,retries=? WHERE run_id=?",(utcnow(),str(exc),metrics["pages_fetched"],metrics["raw_records"],client.retries,run_id))
        raise
