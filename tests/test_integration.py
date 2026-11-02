"""True offline end-to-end Spark + SQLite test, runs in GitHub Actions."""
from datetime import date

from weather_risk.config import CITIES
from weather_risk.storage import fetch_query


def test_demo_pipeline_and_rerun_idempotence(tmp_path):
    import pytest
    pytest.importorskip("pyspark")
    from weather_risk.pipeline import run_pipeline

    start, end = date(2026, 7, 1), date(2026, 7, 6)
    db_url = f"sqlite:///{tmp_path / 'weather.db'}"
    data_dir = str(tmp_path / "lakehouse")

    first = run_pipeline(start, end, db_url=db_url, data_dir=data_dir, demo=True)
    assert first["processed_rows"] == len(CITIES) * 6
    second = run_pipeline(start, end, db_url=db_url, data_dir=data_dir, demo=True)
    assert second["processed_rows"] == len(CITIES) * 6
    count = fetch_query(db_url, "SELECT COUNT(*) AS n FROM weather_daily")[0]["n"]
    assert count == len(CITIES) * 6
    assert second["origin"] == "synthetic_demo"
    assert (tmp_path / "lakehouse" / "lake" / "silver" / "latest").is_dir()
    assert (tmp_path / "lakehouse" / "lake" / "gold" / "latest").is_dir()
