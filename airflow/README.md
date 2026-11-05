# Airflow (skeleton)

Phase 1 ships only the DAG file. Phase 3 adds a Docker Compose stack.
Install Airflow with its official constraints file, for example:

```bash
pip install "apache-airflow==2.10.5" --constraint \
  "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.5/constraints-3.12.txt"
```

The DAG only shells out to the same CLI used locally (`python -m hmda_lab ...`) and to `dbt build`.
