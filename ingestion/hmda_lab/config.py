"""Settings loaded from environment variables (see .env.example)."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass

try:  # optional, only used locally
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass


def env_flag(name: str, default: bool) -> bool:
    """'1', 'true', 'yes', 'on' (any case) -> True; '0', 'false', 'no', 'off' -> False."""
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    value = raw.strip().lower()
    if value in ("1", "true", "yes", "on"):
        return True
    if value in ("0", "false", "no", "off"):
        return False
    raise ValueError(f"{name} must be true or false, got {raw!r}")


@dataclass(frozen=True)
class Settings:
    gcp_project_id: str | None
    bq_dataset: str
    bq_location: str
    fred_api_key: str | None
    bq_sandbox: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            gcp_project_id=os.getenv("GCP_PROJECT_ID"),
            bq_dataset=os.getenv("BQ_DATASET", "hmda_raw"),
            bq_location=os.getenv("BQ_LOCATION", "US"),
            fred_api_key=os.getenv("FRED_API_KEY"),
            bq_sandbox=env_flag("BQ_SANDBOX", default=True),
        )

    def table_id(self, table: str) -> str:
        if not self.gcp_project_id:
            return f"<GCP_PROJECT_ID>.{self.bq_dataset}.{table}"
        return f"{self.gcp_project_id}.{self.bq_dataset}.{table}"


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
