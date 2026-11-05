import json

import pytest

from hmda_lab import fred
from hmda_lab.config import Settings


def test_series_list():
    assert fred.SERIES == ("MORTGAGE30US", "MORTGAGE15US", "FEDFUNDS", "DGS10", "UNRATE")


def test_obs_url_and_redaction():
    url = fred.obs_url("DGS10", "secret123", "2024-01-01", "2025-12-31")
    assert "series_id=DGS10" in url and "file_type=json" in url and "observation_end=2025-12-31" in url
    assert "secret123" not in fred.redact(url)
    with pytest.raises(ValueError):
        fred.obs_url("SP500", "k")


def test_parse_drops_missing(fixtures_dir):
    payload = json.loads((fixtures_dir / "fred_mortgage30us_sample.json").read_text())
    rows = fred.parse_observations("MORTGAGE30US", payload, ingested_at="2026-01-01 00:00:00")
    assert [r["observation_date"] for r in rows] == ["2024-01-04", "2024-01-11", "2024-01-25"]
    assert rows[0]["value"] == "6.62"


def test_write_csv(tmp_path, fixtures_dir):
    payload = json.loads((fixtures_dir / "fred_mortgage30us_sample.json").read_text())
    n = fred.write_csv(fred.parse_observations("MORTGAGE30US", payload), tmp_path / "o.csv")
    assert n == 3
    assert (tmp_path / "o.csv").read_text().splitlines()[0].startswith("series_id,observation_date,value")


def test_sql_and_ddl():
    assert "CLUSTER BY series_id" in fred.table_ddl("p.d.t")
    sql = fred.swap_sql("p.d.t", "p.d.s", ["DGS10", "BAD"])
    assert "series_id IN ('DGS10')" in sql and "BAD" not in sql


def test_dry_run_without_key(tmp_path):
    s = Settings(gcp_project_id=None, bq_dataset="hmda_raw", bq_location="US", fred_api_key=None)
    plan = fred.run(s, list(fred.SERIES), "2018-01-01", None, tmp_path, dry_run=True)
    assert len(plan["urls"]) == 5 and all("api_key=***" in u for u in plan["urls"])
