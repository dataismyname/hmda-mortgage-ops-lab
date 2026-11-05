"""FRED series ingestion -> BigQuery raw.fred_observations.

Series: MORTGAGE30US, MORTGAGE15US (weekly, Freddie Mac PMMS), FEDFUNDS, UNRATE (monthly),
DGS10 (daily). API docs: https://fred.stlouisfed.org/docs/api/fred/series_observations.html
"""
from __future__ import annotations

import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence
from urllib.parse import urlencode

log = logging.getLogger(__name__)

FRED_OBS = "https://api.stlouisfed.org/fred/series/observations"
SERIES = ("MORTGAGE30US", "MORTGAGE15US", "FEDFUNDS", "DGS10", "UNRATE")
RAW_TABLE = "fred_observations"
SCHEMA = [
    ("series_id", "STRING"),
    ("observation_date", "DATE"),
    ("value", "NUMERIC"),
    ("realtime_start", "DATE"),
    ("realtime_end", "DATE"),
    ("_ingested_at", "TIMESTAMP"),
]


def obs_url(series_id: str, api_key: str, start: str = "2018-01-01", end: str | None = None) -> str:
    if series_id not in SERIES:
        raise ValueError(f"Unknown series {series_id}; allowed {SERIES}")
    params = {"series_id": series_id, "api_key": api_key, "file_type": "json",
              "observation_start": start}
    if end:
        params["observation_end"] = end
    return f"{FRED_OBS}?{urlencode(params)}"


def redact(url: str) -> str:
    import re
    return re.sub(r"api_key=[^&]+", "api_key=***", url)


def parse_observations(series_id: str, payload: dict, ingested_at: str | None = None) -> list[dict]:
    """FRED uses '.' for missing values; those rows are dropped."""
    ingested_at = ingested_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    for o in payload.get("observations", []):
        v = o.get("value", ".")
        if v in (".", "", None):
            continue
        rows.append({
            "series_id": series_id, "observation_date": o["date"], "value": str(float(v)),
            "realtime_start": o.get("realtime_start"), "realtime_end": o.get("realtime_end"),
            "_ingested_at": ingested_at,
        })
    return rows


def write_csv(rows: Iterable[dict], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[c for c, _ in SCHEMA])
        w.writeheader()
        for r in rows:
            w.writerow(r)
            n += 1
    return n


def table_ddl(table_id: str) -> str:
    cols = ",\n  ".join(f"`{n}` {t}" for n, t in SCHEMA)
    return (f"CREATE TABLE IF NOT EXISTS `{table_id}` (\n  {cols}\n)\n"
            "PARTITION BY DATE_TRUNC(observation_date, MONTH)\nCLUSTER BY series_id")


def swap_sql(table_id: str, scratch_id: str, series: Sequence[str]) -> str:
    ids = ", ".join(f"'{s}'" for s in series if s in SERIES)
    cols = ", ".join(n for n, _ in SCHEMA)
    return ("BEGIN TRANSACTION;\n"
            f"DELETE FROM `{table_id}` WHERE series_id IN ({ids});\n"
            f"INSERT INTO `{table_id}` ({cols}) SELECT {cols} FROM `{scratch_id}`;\n"
            "COMMIT TRANSACTION;")


def fetch(series_id: str, api_key: str, start: str, end: str | None) -> dict:
    import requests

    url = obs_url(series_id, api_key, start, end)
    log.info("GET %s", redact(url))
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.json()


def run(settings, series: Sequence[str], start: str, end: str | None, data_dir: Path, dry_run: bool) -> dict:
    from . import bq

    table_id = settings.table_id(RAW_TABLE)
    scratch = settings.table_id("_scratch_fred")
    plan = {"table": table_id, "series": list(series),
            "urls": [redact(obs_url(s, settings.fred_api_key or "DUMMY", start, end)) for s in series],
            "sql": swap_sql(table_id, scratch, series)}
    if dry_run:
        log.info("[dry-run] %s", plan)
        return plan
    if not settings.fred_api_key:
        raise RuntimeError("FRED_API_KEY is not set")
    rows = []
    for s in series:
        rows += parse_observations(s, fetch(s, settings.fred_api_key, start, end))
    path = data_dir / "fred" / "observations.csv"
    plan["rows"] = write_csv(rows, path)
    client = bq.get_client(settings.gcp_project_id, settings.bq_location)
    bq.ensure_dataset(client, f"{settings.gcp_project_id}.{settings.bq_dataset}", settings.bq_location)
    bq.ensure_table(client, table_id, table_ddl(table_id))
    bq.load_csv_to_scratch(client, path, scratch, SCHEMA)
    bq.replace_scope(client, plan["sql"])
    client.delete_table(scratch, not_found_ok=True)
    return plan
