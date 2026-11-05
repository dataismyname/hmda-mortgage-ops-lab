"""HMDA LAR ingestion: CFPB/FFIEC Data Browser API or Snapshot files -> BigQuery raw.

Field names follow the FFIEC "Public HMDA - LAR Data Fields" dictionary
(https://ffiec.cfpb.gov/documentation/publications/loan-level-datasets/lar-data-fields),
e.g. ``action_taken``, ``loan_amount``, ``denial_reason-1``, ``derived_msa-md``, ``lei``.
BigQuery column names cannot be relied on to keep ``-``, so hyphens become ``_``
(``denial_reason-1`` -> ``denial_reason_1``, ``derived_msa-md`` -> ``derived_msa_md``).
"""
from __future__ import annotations

import csv
import io
import logging
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Sequence
from urllib.parse import urlencode

log = logging.getLogger(__name__)

DATA_BROWSER_CSV = "https://ffiec.cfpb.gov/v2/data-browser-api/view/csv"
SNAPSHOT_ZIP = "https://files.ffiec.cfpb.gov/static-data/snapshot/{year}/{year}_public_lar_csv.zip"
SUPPORTED_YEARS = (2024, 2025)
RAW_TABLE = "hmda_lar"

# 99 public LAR columns, in file order, as returned by the Data Browser API (checked Nov 2026).
HMDA_COLUMNS: tuple[str, ...] = tuple(
    (Path(__file__).with_name("_cols.txt")).read_text().split()
)
INGEST_COLUMNS = ("_source", "_ingested_at")


def normalize_column(name: str) -> str:
    """``denial_reason-1`` -> ``denial_reason_1``; lower-case; strip BOM/space."""
    name = name.strip().lstrip("\ufeff").lower()
    return re.sub(r"[^0-9a-z_]", "_", name)


RAW_COLUMNS = tuple(normalize_column(c) for c in HMDA_COLUMNS)


def raw_schema() -> list[tuple[str, str]]:
    """Raw layer keeps everything STRING (values like 'NA', 'Exempt', '<20%');
    only activity_year is INT64 so it can drive integer-range partitioning."""
    fields = [(c, "INT64" if c == "activity_year" else "STRING") for c in RAW_COLUMNS]
    return fields + [("_source", "STRING"), ("_ingested_at", "TIMESTAMP")]


def validate_year(year: int) -> int:
    if year not in SUPPORTED_YEARS:
        raise ValueError(f"Year {year} not in phase-1 scope {SUPPORTED_YEARS}")
    return year


def api_url(year: int, states: Sequence[str] | None = None, actions: Sequence[int] | None = None) -> str:
    """Data Browser CSV endpoint. The API requires a geography filter (states, msamds, counties or leis)."""
    validate_year(year)
    if not states:
        raise ValueError("Data Browser API needs at least one state; use --source snapshot for nationwide")
    params = {"years": year, "states": ",".join(s.upper() for s in states)}
    if actions:
        params["actions_taken"] = ",".join(str(a) for a in actions)
    return f"{DATA_BROWSER_CSV}?{urlencode(params, safe=',')}"


def snapshot_url(year: int) -> str:
    return SNAPSHOT_ZIP.format(year=validate_year(year))


def table_ddl(table_id: str) -> str:
    cols = ",\n  ".join(f"`{n}` {t}" for n, t in raw_schema())
    return (
        f"CREATE TABLE IF NOT EXISTS `{table_id}` (\n  {cols}\n)\n"
        "PARTITION BY RANGE_BUCKET(activity_year, GENERATE_ARRAY(2018, 2031, 1))\n"
        "CLUSTER BY state_code, lei, action_taken\n"
        "OPTIONS (description = 'HMDA public LAR, raw strings, one partition per activity_year')"
    )


def swap_sql(table_id: str, scratch_id: str, year: int, states: Sequence[str] | None) -> str:
    """DELETE the exact scope being reloaded, then INSERT: re-running is idempotent."""
    scope = f"activity_year = {int(year)}"
    if states:
        quoted = ", ".join(f"'{s.upper()}'" for s in states if re.fullmatch(r"[A-Za-z]{2}", s))
        scope += f" AND state_code IN ({quoted})"
    cols = ", ".join(f"`{n}`" for n, _ in raw_schema())
    return (
        "BEGIN TRANSACTION;\n"
        f"DELETE FROM `{table_id}` WHERE {scope};\n"
        f"INSERT INTO `{table_id}` ({cols})\nSELECT {cols} FROM `{scratch_id}` WHERE {scope};\n"
        "COMMIT TRANSACTION;"
    )


def transform_rows(lines: Iterable[str], source: str, ingested_at: str | None = None) -> Iterator[list[str]]:
    """Yield a normalized header then data rows with ingestion metadata appended.
    Raises if the header does not contain every expected HMDA column."""
    ingested_at = ingested_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    reader = csv.reader(lines)
    header = [normalize_column(h) for h in next(reader)]
    missing = [c for c in RAW_COLUMNS if c not in header]
    if missing:
        raise ValueError(f"HMDA file missing columns: {missing[:10]}")
    extra = [c for c in header if c not in RAW_COLUMNS]
    if extra:
        log.warning("Ignoring unexpected columns: %s", extra)
    idx = [header.index(c) for c in RAW_COLUMNS]
    yield list(RAW_COLUMNS) + list(INGEST_COLUMNS)
    for row in reader:
        if not row:
            continue
        yield [row[i] if i < len(row) else "" for i in idx] + [source, ingested_at]


def write_clean_csv(lines: Iterable[str], out_path: Path, source: str) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = -1
    with open(out_path, "w", newline="") as fh:
        w = csv.writer(fh)
        for n, row in enumerate(transform_rows(lines, source)):
            w.writerow(row)
    log.info("Wrote %s data rows to %s", n, out_path)
    return n


def download(url: str, dest: Path, timeout: int = 600) -> Path:
    import requests

    dest.parent.mkdir(parents=True, exist_ok=True)
    log.info("Downloading %s -> %s", url, dest)
    with requests.get(url, stream=True, timeout=timeout, allow_redirects=True) as r:
        r.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
    return dest


def iter_lines(path: Path) -> Iterator[str]:
    """Read a CSV or a zip with one CSV inside, as text lines."""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as zf:
            name = next(n for n in zf.namelist() if n.lower().endswith((".csv", ".txt")))
            with zf.open(name) as raw:
                yield from io.TextIOWrapper(raw, encoding="utf-8", newline="")
    else:
        with open(path, encoding="utf-8", newline="") as fh:
            yield from fh


def run(settings, years: Sequence[int], source: str, states: Sequence[str] | None,
        actions: Sequence[int] | None, data_dir: Path, dry_run: bool) -> list[dict]:
    """Plan (and unless dry_run, execute) one load per year. Returns the plan."""
    from . import bq

    table_id = settings.table_id(RAW_TABLE)
    plan = []
    for year in years:
        url = api_url(year, states, actions) if source == "api" else snapshot_url(year)
        tag = "_".join(sorted(s.upper() for s in states)) if states else "all"
        step = {
            "year": year, "url": url, "table": table_id,
            "scratch": settings.table_id(f"_scratch_hmda_{year}_{tag}"),
            "local_file": str(data_dir / f"hmda_{year}_{source}_{tag}" / "lar.clean.csv"),
            "states": list(states or []),
        }
        step["sql"] = swap_sql(table_id, step["scratch"], year, states)
        plan.append(step)
        if dry_run:
            log.info("[dry-run] year=%s url=%s -> %s\nDDL:\n%s\nSQL:\n%s",
                     year, url, table_id, table_ddl(table_id), step["sql"])
            continue
        raw_path = download(url, Path(step["local_file"]).with_name("download" + (".zip" if source == "snapshot" else ".csv")))
        write_clean_csv(iter_lines(raw_path), Path(step["local_file"]), source=url)
        client = bq.get_client(settings.gcp_project_id, settings.bq_location)
        bq.ensure_dataset(client, f"{settings.gcp_project_id}.{settings.bq_dataset}", settings.bq_location)
        bq.ensure_table(client, table_id, table_ddl(table_id))
        bq.load_csv_to_scratch(client, Path(step["local_file"]), step["scratch"], raw_schema())
        bq.replace_scope(client, step["sql"])
        client.delete_table(step["scratch"], not_found_ok=True)
    return plan
