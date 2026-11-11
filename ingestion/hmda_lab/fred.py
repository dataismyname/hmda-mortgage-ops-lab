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


PARTITION_BY = "DATE_TRUNC(observation_date, MONTH)"
CLUSTER_BY = "series_id"
DESCRIPTION = "FRED observations (see SERIES), one row per series and date"


def partition_by(sandbox: bool) -> str | None:
    """Monthly partitions on observation_date, except in the BigQuery sandbox.

    The sandbox expires every time-unit partition 60 days after its partition
    date, so partitions for 2018-2025 observations would be dropped as soon as
    they are written. The table is tiny (a few series), so in sandbox mode it is
    left unpartitioned and only clustered by series_id.
    """
    return None if sandbox else PARTITION_BY


def table_ddl(table_id: str, sandbox: bool = True) -> str:
    cols = ",\n  ".join(f"`{n}` {t}" for n, t in SCHEMA)
    part = partition_by(sandbox)
    return (f"CREATE TABLE IF NOT EXISTS `{table_id}` (\n  {cols}\n)\n"
            + (f"PARTITION BY {part}\n" if part else "")
            + f"CLUSTER BY {CLUSTER_BY}\n"
            f"OPTIONS (description = '{DESCRIPTION}')")


def scope_predicate(series: Sequence[str]) -> str:
    ids = ", ".join(f"'{s}'" for s in series if s in SERIES)
    if not ids:
        raise ValueError(f"No known FRED series in {list(series)}; allowed {SERIES}")
    return f"(series_id IN ({ids}))"


def swap_sql(table_id: str, staging_id: str, series: Sequence[str], sandbox: bool = True) -> str:
    """Sandbox-safe idempotent swap (DDL only): rebuild the table keeping other
    series and replacing the reloaded ones with the staging rows."""
    from . import bq

    return bq.rebuild_sql(table_id, staging_id, [n for n, _ in SCHEMA], scope_predicate(series),
                          partition_by(sandbox), CLUSTER_BY, DESCRIPTION)


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
    staging = settings.table_id("_staging_fred")
    sandbox = getattr(settings, "bq_sandbox", True)
    plan = {"table": table_id, "series": list(series), "sandbox": sandbox,
            "urls": [redact(obs_url(s, settings.fred_api_key or "DUMMY", start, end)) for s in series],
            "sql": swap_sql(table_id, staging, series, sandbox)}
    if dry_run:
        log.info("[dry-run] %s\nDDL:\n%s", plan, table_ddl(table_id, sandbox))
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
    plan["rows_loaded"] = bq.load_scope(
        client, table_id=table_id, staging_id=staging, csv_path=path, fields=SCHEMA,
        create_ddl=table_ddl(table_id, sandbox), rebuild=plan["sql"],
    )
    return plan
