"""Airflow DAG skeleton: FRED weekly + HMDA yearly reload -> dbt build.

Phase 1 skeleton (not yet deployed). Targets Airflow 2.10+/3.x with the
standard BashOperator; the project is mounted at /opt/hmda-lab.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT = "/opt/hmda-lab"
DEFAULT_ARGS = {"owner": "hmda-lab", "retries": 2, "retry_delay": timedelta(minutes=10)}

with DAG(
    dag_id="hmda_lab_ingest_and_transform",
    description="FRED + HMDA raw loads into BigQuery, then dbt build",
    start_date=datetime(2026, 1, 1),
    schedule="0 6 * * 1",  # Mondays 06:00 UTC; FRED PMMS updates on Thursdays
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["hmda", "fred", "bigquery", "dbt"],
) as dag:
    load_fred = BashOperator(
        task_id="load_fred",
        bash_command=f"cd {PROJECT} && python -m hmda_lab fred --start 2018-01-01",
        env={"PYTHONPATH": f"{PROJECT}/ingestion"}, append_env=True,
    )
    # Idempotent: reloads the year scope. Snapshot files only change once a year,
    # so in practice this task is triggered manually (dag_run.conf) or skipped.
    load_hmda = BashOperator(
        task_id="load_hmda",
        bash_command=(f"cd {PROJECT} && python -m hmda_lab hmda "
                      "--source {{ dag_run.conf.get('source', 'api') }} "
                      "--years {{ dag_run.conf.get('years', '2024 2025') }} "
                      "--states {{ dag_run.conf.get('states', 'DE') }}"),
        env={"PYTHONPATH": f"{PROJECT}/ingestion"}, append_env=True,
    )
    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=f"cd {PROJECT}/dbt && dbt deps && dbt build --target prod",
    )
    [load_fred, load_hmda] >> dbt_build
