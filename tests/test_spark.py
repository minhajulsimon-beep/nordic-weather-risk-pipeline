from datetime import date

import pytest

from weather_risk.config import CITIES
from weather_risk.demo import synthetic_weather

START = date(2026, 1, 1)
END = date(2026, 1, 5)


def bronze_fixture(spark):
    from weather_risk.transform import make_bronze

    payloads = {city.name: synthetic_weather(city, START, END) for city in CITIES[:2]}
    return make_bronze(spark, payloads, START, END, "2026-11-02T10:00:00+00:00", "synthetic_demo")


def test_spark_bronze_silver_gold(spark):
    from weather_risk.transform import check_bronze, make_silver, make_gold

    bronze = bronze_fixture(spark)
    check_bronze(bronze)
    assert bronze.count() == 10
    silver = make_silver(bronze)
    assert silver.count() == 10
    assert "risk_score" in silver.columns
    assert "year_month" in silver.columns
    assert silver.filter("risk_score < 0 OR risk_score > 5").count() == 0
    assert silver.filter("risk_level NOT IN ('low', 'medium', 'high')").count() == 0
    gold = make_gold(silver)
    assert gold.count() == 2
    assert gold.agg({"days": "sum"}).first()[0] == 10


def test_spark_quality_rejects_missing_metrics_and_duplicates(spark):
    from pyspark.sql import functions as F
    from weather_risk.transform import DataQualityError, check_bronze

    bronze = bronze_fixture(spark)
    bad = bronze.withColumn("precipitation_sum", F.lit(None).cast("double"))
    with pytest.raises(DataQualityError, match="precipitation_sum"):
        check_bronze(bad)

    doubled = bronze.unionByName(bronze.limit(1))
    with pytest.raises(DataQualityError, match="Duplicate"):
        check_bronze(doubled)


def test_risk_thresholds(spark):
    from pyspark.sql import Row
    from weather_risk.transform import make_silver

    row = Row(
        city="Test", record_date="2026-01-01",
        temperature_2m_max=7.0, temperature_2m_min=-1.0,
        precipitation_sum=10.0, wind_speed_10m_max=50.0,
        data_origin="synthetic_demo", ingested_at="2026-11-02T10:00:00+00:00",
    )
    silver = make_silver(spark.createDataFrame([row])).first()
    assert silver["heavy_rain"] == 1
    assert silver["strong_wind"] == 1
    assert silver["frost"] == 1
    assert silver["risk_score"] == 5
    assert silver["risk_level"] == "high"
