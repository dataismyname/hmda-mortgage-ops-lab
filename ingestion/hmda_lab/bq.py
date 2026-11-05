"""Thin BigQuery helpers. Idempotency pattern: load file into a scratch table,
then DELETE the target scope + INSERT in one multi-statement transaction."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

log = logging.getLogger(__name__)


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


def ensure_table(client, table_id: str, ddl: str) -> None:
    log.info("Ensuring table %s", table_id)
    client.query(ddl).result()


def load_csv_to_scratch(client, csv_path: Path, scratch_table_id: str, fields) -> int:
    from google.cloud import bigquery

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        schema=to_schema(fields),
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        allow_quoted_newlines=True,
    )
    with open(csv_path, "rb") as fh:
        job = client.load_table_from_file(fh, scratch_table_id, job_config=job_config)
    job.result()
    rows = client.get_table(scratch_table_id).num_rows
    log.info("Loaded %s rows into scratch %s", rows, scratch_table_id)
    return rows


def replace_scope(client, sql: str) -> None:
    log.info("Running idempotent swap:\n%s", sql)
    client.query(sql).result()
