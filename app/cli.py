"""Command line entry point."""
import argparse, json, logging, os
from .config import Config
from .ingestion import ingest
from .storage import Store

def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="command",required=True)
    q=sub.add_parser("ingest"); q.add_argument("--backfill",action="store_true")
    sub.add_parser("report")
    q=sub.add_parser("reset"); q.add_argument("--yes",action="store_true")
    args=p.parse_args(); cfg=Config(); logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")
    if args.command=="ingest": print(json.dumps(ingest(cfg,backfill=args.backfill),indent=2))
    elif args.command=="report": print(json.dumps(Store(cfg.database_path).counts(),indent=2))
    elif args.command=="reset":
        if not args.yes: raise SystemExit("Destructive reset requires --yes; this deletes all target/checkpoint/run data.")
        if os.path.exists(cfg.database_path): os.remove(cfg.database_path)
        Store(cfg.database_path); print("Database reset.")
if __name__=="__main__": main()
