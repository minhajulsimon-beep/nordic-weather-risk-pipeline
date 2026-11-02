from datetime import date

from weather_risk.storage import (
    SILVER_FIELDS, fetch_query, get_city_summary, initialize_database, upsert_records
)


def make_record(city="Aarhus", rain=12.0):
    return {
        "city": city,
        "record_date": date(2026, 7, 1),
        "temp_max_c": 19.0,
        "temp_min_c": 12.0,
        "precipitation_mm": rain,
        "wind_max_kmh": 55.0,
        "heavy_rain": 1,
        "strong_wind": 1,
        "frost": 0,
        "risk_score": 4,
        "risk_level": "high",
        "risk_reasons": "Heavy precipitation, Strong wind",
        "year_month": "2026-07",
        "data_origin": "synthetic_demo",
        "ingested_at": "2026-11-02T10:00:00+00:00",
    }


def test_sql_upsert_is_repeatable_and_replaces_values(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    row = make_record()
    assert set(row) == set(SILVER_FIELDS)
    assert upsert_records(db_url, [row]) == 1
    assert upsert_records(db_url, [row]) == 1
    assert fetch_query(db_url, "SELECT COUNT(*) AS total FROM weather_daily")[0]["total"] == 1

    edited = make_record(rain=20.0)
    upsert_records(db_url, [edited])
    assert fetch_query(db_url, "SELECT precipitation_mm FROM weather_daily")[0]["precipitation_mm"] == 20.0
    assert get_city_summary(db_url)[0]["high_risk_days"] == 1


def test_db_creates_index_and_persists_multiple_cities(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'data' / 'weather.db'}"
    initialize_database(db_url)
    upsert_records(db_url, [make_record("Aarhus"), make_record("Copenhagen")])
    results = get_city_summary(db_url)
    assert len(results) == 2
    assert all(result["days"] == 1 for result in results)
