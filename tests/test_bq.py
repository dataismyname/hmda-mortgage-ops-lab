"""Sandbox-safe load flow with a fake BigQuery client (no GCP, no network)."""
from pathlib import Path

import pytest

from hmda_lab import bq, config, fred, hmda


class FakeJob:
    def result(self):
        return None


class FakeTable:
    num_rows = 6


class FakeClient:
    def __init__(self, fail_on_rebuild=False):
        self.calls = []
        self.fail_on_rebuild = fail_on_rebuild

    def query(self, sql):
        self.calls.append(("query", sql))
        if self.fail_on_rebuild and sql.startswith("CREATE OR REPLACE"):
            raise RuntimeError("boom")
        return FakeJob()

    def load_table_from_file(self, fh, table_id, job_config=None):
        self.calls.append(("load", table_id, job_config.write_disposition))
        return FakeJob()

    def get_table(self, table_id):
        return FakeTable()

    def delete_table(self, table_id, not_found_ok=False):
        self.calls.append(("delete", table_id))


@pytest.fixture
def fake_bigquery(monkeypatch):
    """Minimal stand-in for google.cloud.bigquery so load_csv_to_staging runs offline."""
    import sys
    import types

    mod = types.ModuleType("google.cloud.bigquery")

    class LoadJobConfig:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    mod.LoadJobConfig = LoadJobConfig
    mod.SourceFormat = types.SimpleNamespace(CSV="CSV")
    mod.WriteDisposition = types.SimpleNamespace(WRITE_TRUNCATE="WRITE_TRUNCATE")
    mod.SchemaField = lambda name, typ, mode=None: (name, typ, mode)
    google = sys.modules.get("google") or types.ModuleType("google")
    cloud = types.ModuleType("google.cloud")
    cloud.bigquery = mod
    monkeypatch.setitem(sys.modules, "google", google)
    monkeypatch.setitem(sys.modules, "google.cloud", cloud)
    monkeypatch.setitem(sys.modules, "google.cloud.bigquery", mod)
    return mod


@pytest.mark.parametrize("sql", [
    "INSERT INTO t SELECT 1", "DELETE FROM t WHERE true", "MERGE t USING s ON false",
    "UPDATE t SET a = 1 WHERE true", "BEGIN TRANSACTION; SELECT 1;", "TRUNCATE TABLE t",
])
def test_assert_no_dml_blocks_dml(sql):
    with pytest.raises(ValueError, match="DML"):
        bq.assert_no_dml(sql)


def test_assert_no_dml_allows_ddl():
    for sql in (hmda.table_ddl("p.d.t"), hmda.swap_sql("p.d.t", "p.d.s", 2025, ["DE"]),
                fred.table_ddl("p.d.f"), fred.swap_sql("p.d.f", "p.d.s", list(fred.SERIES))):
        assert bq.assert_no_dml(sql) == sql


def test_rebuild_sql_keeps_null_scope_rows():
    sql = bq.rebuild_sql("p.d.t", "p.d.s", ["a", "b"], "(a = 1)", None, "b", "x")
    assert "WHERE NOT COALESCE((a = 1), FALSE)" in sql
    assert "PARTITION BY" not in sql and "CLUSTER BY b" in sql


def test_load_scope_order_and_cleanup(tmp_path, fake_bigquery):
    csv_path = tmp_path / "x.csv"
    csv_path.write_text("a\n1\n")
    client = FakeClient()
    rows = bq.load_scope(client, table_id="p.d.t", staging_id="p.d.s", csv_path=csv_path,
                         fields=[("a", "STRING")], create_ddl=hmda.table_ddl("p.d.t"),
                         rebuild=hmda.swap_sql("p.d.t", "p.d.s", 2025, ["DE"]))
    assert rows == 6
    kinds = [c[0] for c in client.calls]
    assert kinds == ["query", "load", "query", "delete"]
    assert client.calls[0][1].startswith("CREATE TABLE IF NOT EXISTS")
    assert client.calls[1] == ("load", "p.d.s", "WRITE_TRUNCATE")
    assert client.calls[2][1].startswith("CREATE OR REPLACE TABLE")
    assert client.calls[3] == ("delete", "p.d.s")


def test_load_scope_drops_staging_on_failure(tmp_path, fake_bigquery):
    csv_path = tmp_path / "x.csv"
    csv_path.write_text("a\n1\n")
    client = FakeClient(fail_on_rebuild=True)
    with pytest.raises(RuntimeError):
        bq.load_scope(client, table_id="p.d.t", staging_id="p.d.s", csv_path=csv_path,
                      fields=[("a", "STRING")], create_ddl="CREATE TABLE IF NOT EXISTS `p.d.t` (a STRING)",
                      rebuild="CREATE OR REPLACE TABLE `p.d.t` AS SELECT 1")
    assert client.calls[-1] == ("delete", "p.d.s")


@pytest.mark.parametrize("raw,expected", [
    (None, True), ("", True), ("true", True), ("1", True), ("FALSE", False), ("0", False), ("off", False),
])
def test_bq_sandbox_flag(monkeypatch, raw, expected):
    if raw is None:
        monkeypatch.delenv("BQ_SANDBOX", raising=False)
    else:
        monkeypatch.setenv("BQ_SANDBOX", raw)
    assert config.Settings.from_env().bq_sandbox is expected
