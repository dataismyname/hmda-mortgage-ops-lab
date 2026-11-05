import csv
from pathlib import Path

import pytest

from hmda_lab import hmda
from hmda_lab.config import Settings


def test_column_dictionary_has_99_fields_and_key_names():
    assert len(hmda.HMDA_COLUMNS) == 99
    for name in ["action_taken", "loan_amount", "denial_reason-1", "derived_msa-md", "lei", "activity_year"]:
        assert name in hmda.HMDA_COLUMNS


@pytest.mark.parametrize("raw,expected", [
    ("denial_reason-1", "denial_reason_1"),
    ("derived_msa-md", "derived_msa_md"),
    ("\ufeffActivity_Year ", "activity_year"),
    ("open-end_line_of_credit", "open_end_line_of_credit"),
])
def test_normalize_column(raw, expected):
    assert hmda.normalize_column(raw) == expected


def test_raw_schema_types():
    schema = dict(hmda.raw_schema())
    assert schema["activity_year"] == "INT64"
    assert schema["loan_amount"] == "STRING"
    assert schema["_ingested_at"] == "TIMESTAMP"
    assert len(schema) == 101


def test_api_url_requires_state_and_builds_query():
    with pytest.raises(ValueError):
        hmda.api_url(2024, None)
    url = hmda.api_url(2025, ["de", "tx"], [1, 3])
    assert url.startswith(hmda.DATA_BROWSER_CSV)
    assert "years=2025" in url and "states=DE,TX" in url and "actions_taken=1,3" in url


def test_year_scope():
    assert hmda.snapshot_url(2024).endswith("/2024/2024_public_lar_csv.zip")
    with pytest.raises(ValueError):
        hmda.snapshot_url(2019)


def test_ddl_is_partitioned_and_clustered():
    ddl = hmda.table_ddl("p.d.hmda_lar")
    assert "PARTITION BY RANGE_BUCKET(activity_year" in ddl
    assert "CLUSTER BY state_code, lei, action_taken" in ddl
    assert "CREATE TABLE IF NOT EXISTS" in ddl


def test_swap_sql_is_scoped_and_transactional():
    sql = hmda.swap_sql("p.d.t", "p.d.s", 2024, ["DE", "x;drop"])
    assert sql.startswith("BEGIN TRANSACTION;") and sql.endswith("COMMIT TRANSACTION;")
    assert "DELETE FROM `p.d.t` WHERE activity_year = 2024 AND state_code IN ('DE')" in sql
    assert "drop" not in sql.lower().replace("delete", "")


def test_transform_fixture(fixtures_dir):
    lines = open(fixtures_dir / "hmda_lar_sample.csv", newline="").read().splitlines(keepends=True)
    rows = list(hmda.transform_rows(lines, source="fixture", ingested_at="2026-01-01 00:00:00"))
    header, data = rows[0], rows[1:]
    assert header[-2:] == ["_source", "_ingested_at"]
    assert "denial_reason_1" in header and "derived_msa_md" in header
    assert len(data) == 6
    assert all(len(r) == len(header) for r in data)
    by = {c: i for i, c in enumerate(header)}
    assert {r[by["action_taken"]] for r in data} == {"1", "3"}
    assert all(r[by["activity_year"]] == "2024" for r in data)


def test_transform_rejects_missing_columns():
    with pytest.raises(ValueError, match="missing columns"):
        list(hmda.transform_rows(["activity_year,lei\n", "2024,ABC\n"], source="x"))


def test_write_clean_csv(tmp_path, fixtures_dir):
    out = tmp_path / "out.csv"
    n = hmda.write_clean_csv(hmda.iter_lines(fixtures_dir / "hmda_lar_sample.csv"), out, source="fixture")
    assert n == 6
    assert next(csv.reader(open(out)))[0] == "activity_year"


def test_iter_lines_reads_zip(tmp_path, fixtures_dir):
    import zipfile
    z = tmp_path / "s.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.write(fixtures_dir / "hmda_lar_sample.csv", "2024_public_lar.csv")
    assert len(list(hmda.iter_lines(z))) == 7


def test_run_dry_run_makes_no_calls(tmp_path):
    s = Settings(gcp_project_id="demo", bq_dataset="hmda_raw", bq_location="US", fred_api_key=None)
    plan = hmda.run(s, [2024, 2025], "api", ["DE"], None, tmp_path, dry_run=True)
    assert [p["year"] for p in plan] == [2024, 2025]
    assert plan[0]["table"] == "demo.hmda_raw.hmda_lar"
    assert not any(tmp_path.iterdir())
