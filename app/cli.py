"""Command line entry point."""
import argparse, json, logging, os
from pathlib import Path
from .config import Config
from .ingestion import ingest
from .storage import Store
from .generator import make_dataset, make_quality_dataset

def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="command",required=True)
    q=sub.add_parser("ingest"); q.add_argument("--backfill",action="store_true")
    sub.add_parser("report")
    q=sub.add_parser("generate"); q.add_argument("--orders",type=int,default=25); q.add_argument("--output",default="data/sample"); q.add_argument("--scenario",choices=("normal","quality-mix"),default="normal")
    q=sub.add_parser("reset"); q.add_argument("--yes",action="store_true")
    args=p.parse_args(); cfg=Config(); logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")
    if args.command=="ingest": print(json.dumps(ingest(cfg,backfill=args.backfill),indent=2))
    elif args.command=="report": print(json.dumps(Store(cfg.database_path).counts(),indent=2))
    elif args.command=="generate":
        if args.orders<0: raise SystemExit("--orders must be non-negative")
        out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
        dataset=(make_quality_dataset if args.scenario=="quality-mix" else make_dataset)(args.orders)
        for name,rows in dataset.items(): (out/f"{name}.json").write_text(json.dumps(rows,indent=2),encoding="utf-8")
        expected={"customers":len(dataset["customers"]),"orders_in_source":len(dataset["orders"]),"seed":731,"scenario":args.scenario}
        if args.scenario=="normal": expected["expected_valid_order_events"]=len(dataset["orders"])
        else:
            expected["expected_quality_cases"]=(
                {
                    "exact_duplicate_event":{"source_event_id":"EVT-00000000","expected":"count as a duplicate without adding a second event"},
                    "conflicting_duplicate_event_id":{"source_event_id":"EVT-00000000","expected":"quarantine the payload conflict"},
                    "missing_required_status":{"source_event_id":"EVT-MISSING-STATUS","expected":"quarantine for missing status"},
                    "unknown_customer_reference":{"source_event_id":"EVT-INVALID-FK","expected":"quarantine for unknown customer_id"},
                    "late_arriving_event":{"source_event_id":"EVT-LATE","expected":"retain in event history without replacing newer current state"},
                    "additive_schema_field":{"field":"unexpected_source_flag","expected":"preserve in raw payload and report as unexpected"},
                } if args.orders>0 else {}
            )
        (out/"expected_summary.json").write_text(json.dumps(expected,indent=2),encoding="utf-8")
        print(json.dumps(expected,indent=2))
    elif args.command=="reset":
        if not args.yes: raise SystemExit("Destructive reset requires --yes; this deletes all target/checkpoint/run data.")
        if os.path.exists(cfg.database_path): os.remove(cfg.database_path)
        Store(cfg.database_path); print("Database reset.")
if __name__=="__main__": main()
