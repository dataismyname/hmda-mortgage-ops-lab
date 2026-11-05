import json

from hmda_lab import cli


def test_cli_hmda_dry_run(capsys, monkeypatch):
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    assert cli.main(["--dry-run", "hmda", "--years", "2024", "--states", "DE"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan[0]["year"] == 2024


def test_cli_api_without_states_fails():
    assert cli.main(["--dry-run", "hmda", "--source", "api"]) == 2


def test_cli_bad_year_fails():
    assert cli.main(["--dry-run", "hmda", "--years", "2017", "--states", "DE"]) == 2


def test_cli_requires_project_when_not_dry_run(monkeypatch):
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    assert cli.main(["fred"]) == 2


def test_cli_fred_dry_run(capsys):
    assert cli.main(["--dry-run", "fred", "--series", "UNRATE"]) == 0
    assert json.loads(capsys.readouterr().out)["series"] == ["UNRATE"]
