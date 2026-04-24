"""CLI: python run.py --event iran_war --query "..." [--as-of YYYY-MM-DD]"""
import argparse
import json
import sys
from datetime import date

from config import load_event
import agent_supervisor


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--event", required=True)
    p.add_argument("--query", required=True)
    p.add_argument("--as-of", default=None, help="YYYY-MM-DD; defaults to event end_date")
    args = p.parse_args(argv)

    try:
        cfg = load_event(args.event)
    except FileNotFoundError as e:
        print(f"error: unknown --event {args.event!r}: {e}", file=sys.stderr)
        return 2
    try:
        as_of = date.fromisoformat(args.as_of) if args.as_of else cfg.end_date
    except ValueError as e:
        print(f"error: --as-of must be YYYY-MM-DD ({e})", file=sys.stderr)
        return 2
    result = agent_supervisor.run(cfg, args.query, as_of=as_of)

    out = {k: v for k, v in result.items() if k != "cfg"}
    if isinstance(out.get("as_of"), date):
        out["as_of"] = out["as_of"].isoformat()
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
