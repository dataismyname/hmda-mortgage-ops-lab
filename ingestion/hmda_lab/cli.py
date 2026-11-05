"""CLI: python -m hmda_lab.cli {hmda,fred} [...] [--dry-run]"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from . import fred, hmda
from .config import Settings, setup_logging

log = logging.getLogger("hmda_lab")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hmda-lab", description="Load HMDA and FRED data into BigQuery raw tables.")
    p.add_argument("--log-level", default="INFO")
    p.add_argument("--data-dir", default="data", type=Path)
    p.add_argument("--dry-run", action="store_true", help="Print plan, URLs and SQL; no download, no BigQuery.")
    sub = p.add_subparsers(dest="command", required=True)

    h = sub.add_parser("hmda", help="HMDA public LAR")
    h.add_argument("--years", type=int, nargs="+", default=list(hmda.SUPPORTED_YEARS))
    h.add_argument("--source", choices=["api", "snapshot"], default="api",
                   help="api = Data Browser CSV (needs --states); snapshot = nationwide zip")
    h.add_argument("--states", nargs="*", help="2-letter state codes, e.g. DE TX")
    h.add_argument("--actions", type=int, nargs="*", help="action_taken codes 1-8 (default: all)")

    f = sub.add_parser("fred", help="FRED rates and macro series")
    f.add_argument("--series", nargs="+", default=list(fred.SERIES))
    f.add_argument("--start", default="2018-01-01")
    f.add_argument("--end", default=None)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    setup_logging(args.log_level)
    settings = Settings.from_env()
    if not args.dry_run and not settings.gcp_project_id:
        log.error("GCP_PROJECT_ID is not set (use --dry-run to only print the plan)")
        return 2
    try:
        if args.command == "hmda":
            if args.source == "api" and not args.states:
                log.error("--source api needs --states (or use --source snapshot)")
                return 2
            plan = hmda.run(settings, args.years, args.source, args.states, args.actions, args.data_dir, args.dry_run)
        else:
            plan = fred.run(settings, args.series, args.start, args.end, args.data_dir, args.dry_run)
    except ValueError as exc:
        log.error("%s", exc)
        return 2
    if args.dry_run:
        print(json.dumps(plan, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
