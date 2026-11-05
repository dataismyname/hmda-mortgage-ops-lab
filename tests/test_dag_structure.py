"""Static check of the DAG without installing Airflow."""
import ast
from pathlib import Path

DAG = Path(__file__).parents[1] / "airflow" / "dags" / "hmda_lab_dag.py"


def test_dag_parses_and_has_tasks():
    tree = ast.parse(DAG.read_text())
    task_ids = {
        kw.value.value
        for node in ast.walk(tree) if isinstance(node, ast.Call)
        for kw in node.keywords if kw.arg == "task_id"
    }
    assert task_ids == {"load_fred", "load_hmda", "dbt_build"}
    assert "hmda_lab_ingest_and_transform" in DAG.read_text()
