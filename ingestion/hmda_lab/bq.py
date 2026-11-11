"""Thin BigQuery helpers.

Idempotency pattern (BigQuery sandbox compatible, no DML):

1. ``CREATE TABLE IF NOT EXISTS`` the target with its partitioning and clustering (DDL).
2. Load the clean CSV into a staging table with a **load job** (``WRITE_TRUNCATE``).
3. Rebuild the target with one DDL statement::

       CREATE OR REPLACE TABLE target PARTITION BY ... CLUSTER BY ... AS
       SELECT cols FROM target  WHERE NOT COALESCE(<scope>, FALSE)   -- rows outside the reloaded scope
       UNION ALL
       SELECT cols FROM staging WHERE <scope>                         -- fresh rows for the scope

4. Drop the staging table (API call, not DML).

Re-running the same scope gives the same table. The sandbox does not support DML
(INSERT/UPDATE/DELETE/MERGE), so this module never issues it.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Sequence

log = logging.getLogger(__name__)

DML_PATTERN = re.compile(r"\b(INSERT|UPDATE|DELETE|MERGE|TRUNCATE)\b|BEGIN\s+TRANSACTION", re.IGNORECASE)


def get_client(project: str | None, location: str):
    from google.cloud import bigquery  # imported lazily so tests need no GCP

    return bigquery.Client(project=project, location=location)


def ensure_dataset(client, dataset_id: str, location: str) -> None:
    from google.cloud import bigquery

    ds = bigquery.Dataset(dataset_id)
    ds.location = location
    client.create_dataset(ds, exists_ok=True)


def to_schema(fields: Sequence[tuple[str, str]]):
    from google.cloud import bigquery

    return [bigquery.SchemaField(n, t, mode="NULLABLE") for n, t in fields]


def assert_no_dml(sql: str) -> str:
    """Guard: the BigQuery sandbox rejects DML, so nothing we send may contain it."""
    if DML_PATTERN.search(sql):
        raise ValueError("DML is not allowed (BigQuery sandbox); use load jobs + DDL")
    return sql


def run_ddl(client, sql: str) -> None:
    log.info("Running DDL:\n%s", sql)
    client.query(assert_no_dml(sql)).result()


def ensure_table(client, table_id: str, ddl: str) -> None:
    log.info("Ensuring table %s", table_id)
    run_ddl(client, ddl)


def load_csv_to_staging(client, csv_path: Path, staging_table_id: str, fields) -> int:
    """Load job (not DML): replaces the staging table with the file contents."""
    from google.cloud import bigquery

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        schema=to_schema(fields),
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        allow_quoted_newlines=True,
    )
    with open(csv_path, "rb") as fh:
        job = client.load_table_from_file(fh, staging_table_id, job_config=job_config)
    job.result()
    rows = client.get_table(staging_table_id).num_rows
    log.info("Loaded %s rows into staging %s", rows, staging_table_id)
    return rows


def rebuild_sql(table_id: str, staging_id: str, columns: Sequence[str], scope: str,
                partition_by: str | None, cluster_by: str | None, description: str) -> str:
    """CREATE OR REPLACE the target as (target minus scope) UNION ALL (staging within scope).

    ``COALESCE(..., FALSE)`` keeps rows whose scope columns are NULL: a bare
    ``NOT (x IN (...))`` would evaluate to NULL and silently drop them.
    """
    cols = ", ".join(f"`{c}`" for c in columns)
    parts = [f"CREATE OR REPLACE TABLE `{table_id}`"]
    if partition_by:
        parts.append(f"PARTITION BY {partition_by}")
    if cluster_by:
        parts.append(f"CLUSTER BY {cluster_by}")
    parts.append(f"OPTIONS (description = '{description}')")
    parts.append(
        "AS\n"
        f"SELECT {cols} FROM `{table_id}` WHERE NOT COALESCE({scope}, FALSE)\n"
        "UNION ALL\n"
        f"SELECT {cols} FROM `{staging_id}` WHERE {scope}"
    )
    return assert_no_dml("\n".join(parts))


def drop_table(client, table_id: str) -> None:
    client.delete_table(table_id, not_found_ok=True)
    log.info("Dropped %s", table_id)


def load_scope(client, *, table_id: str, staging_id: str, csv_path: Path, fields,
               create_ddl: str, rebuild: str) -> int:
    """Full sandbox-safe load: ensure target, load staging, rebuild target, drop staging."""
    ensure_table(client, table_id, create_ddl)
    try:
        rows = load_csv_to_staging(client, csv_path, staging_id, fields)
        run_ddl(client, rebuild)
    finally:
        drop_table(client, staging_id)
    return rows
