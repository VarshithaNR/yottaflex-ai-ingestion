"""Run-level source, target, integrity, and aggregate reconciliation."""
import json
from decimal import Decimal
from pathlib import Path
from .storage import Store

def write_quarantine_manifest(database_path, quarantine_dir, run_id):
    """Atomically export a run's canonical SQLite rejects as JSON Lines."""
    store=Store(database_path)
    with store.connect() as c:
        rows=c.execute("SELECT id,stream,page,record_json,reason,created_at FROM quarantined_records WHERE run_id=? ORDER BY id",(run_id,)).fetchall()
    output=Path(quarantine_dir); output.mkdir(parents=True,exist_ok=True)
    destination=output/f"{run_id}.jsonl"; temporary=destination.with_suffix(".jsonl.tmp")
    lines=[json.dumps({"quarantine_id":r[0],"run_id":run_id,"stream":r[1],"source_page":r[2],"record":json.loads(r[3]),"reason":r[4],"created_at":r[5]},sort_keys=True) for r in rows]
    temporary.write_text("\n".join(lines)+("\n" if lines else ""),encoding="utf-8")
    temporary.replace(destination)
    return destination

def build_run_report(database_path, raw_dir, run_id):
    """Compare this run's raw event keys with durable history and current state."""
    source_events={}
    unexpected_fields={}
    allowed_fields={"order_id","customer_id","amount","currency","status","updated_at","source_event_id"}
    for path in Path(raw_dir).glob(f"{run_id}_orders_*.json"):
        payload=json.loads(path.read_text(encoding="utf-8"))
        for rec in payload.get("items",[]):
            if isinstance(rec,dict):
                for field in rec.keys()-allowed_fields:
                    unexpected_fields[field]=unexpected_fields.get(field,0)+1
            if isinstance(rec,dict) and isinstance(rec.get("source_event_id"),str):
                source_events.setdefault(rec["source_event_id"],rec)
    store=Store(database_path)
    with store.connect() as c:
        source_ids=set(source_events)
        persisted_ids=set()
        if source_ids:
            for event_id, in c.execute("SELECT source_event_id FROM order_events"):
                if event_id in source_ids: persisted_ids.add(event_id)
        orphan_count=c.execute("SELECT COUNT(*) FROM orders o LEFT JOIN customers c ON c.customer_id=o.customer_id WHERE c.customer_id IS NULL").fetchone()[0]
        history={r[0]:r[1:] for r in c.execute("SELECT order_id,customer_id,amount,currency,status,updated_at,source_event_id FROM order_events ORDER BY updated_at,source_event_id")}
        latest={}
        for order_id,row in history.items():
            latest[order_id]=tuple(row)
        current={r[0]:r[1:] for r in c.execute("SELECT order_id,customer_id,amount,currency,status,updated_at,last_event_id FROM orders")}
        run=c.execute("SELECT started_at,ended_at,status FROM ingestion_runs WHERE run_id=?",(run_id,)).fetchone()
        target_aggregate={}
        derived_aggregate={}
        for order_id, row in current.items():
            target_aggregate[row[2]]=target_aggregate.get(row[2],Decimal(0))+Decimal(row[1])
        for order_id,row in latest.items():
            derived_aggregate[row[2]]=derived_aggregate.get(row[2],Decimal(0))+Decimal(row[1])
        aggregates_match={currency:format(target_aggregate.get(currency,Decimal(0)),"f")==format(derived_aggregate.get(currency,Decimal(0)),"f") for currency in target_aggregate.keys()|derived_aggregate.keys()}
    return {
        "source_unique_event_ids_this_run":len(source_ids),
        "source_event_ids_found_in_target_history":len(persisted_ids),
        "source_event_ids_not_in_target_history":len(source_ids-persisted_ids),
        "unexpected_source_fields":unexpected_fields,
        "target_table_counts":store.counts(),
        "run_started_at":run[0],
        "run_ended_at":run[1],
        "run_status":run[2],
        "referential_integrity_failures":orphan_count,
        "current_orders_match_latest_event_state":current==latest,
        "current_order_amounts_match_event_history_by_currency":aggregates_match,
        "current_order_amount_by_currency":{k:format(v,"f") for k,v in target_aggregate.items()},
    }
