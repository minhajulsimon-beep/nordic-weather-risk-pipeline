"""Bronze -> Silver -> Gold transformations using native PySpark expressions."""
from datetime import date

from pyspark.sql import DataFrame, SparkSession, functions as F, types as T

from .api import flatten_city
from .config import (
    DAILY_VARIABLES,
    FROST_C,
    HEAVY_PRECIPITATION_MM,
    STRONG_WIND_KMH,
)


class DataQualityError(ValueError):
    """Raised before bad data reaches the analytics database."""


BRONZE_SCHEMA = T.StructType(
    [
        T.StructField("city", T.StringType(), False),
        T.StructField("record_date", T.StringType(), False),
        *[T.StructField(variable, T.DoubleType(), True) for variable in DAILY_VARIABLES],
        T.StructField("data_origin", T.StringType(), False),
        T.StructField("ingested_at", T.StringType(), False),
    ]
)


def make_bronze(
    spark: SparkSession,
    city_payloads: dict[str, dict],
    start: date,
    end: date,
    ingested_at: str,
    origin: str,
) -> DataFrame:
    records = []
    for city_name, payload in city_payloads.items():
        for record in flatten_city(city_name, payload, start, end):
            try:
                values = [
                    float(record[metric]) if record[metric] is not None else None
                    for metric in DAILY_VARIABLES
                ]
            except (ValueError, TypeError) as exc:
                raise DataQualityError(f"Non-numeric weather field for {city_name}") from exc
            records.append(
                (
                    city_name,
                    record["record_date"],
                    *values,
                    origin,
                    ingested_at,
                )
            )
    return spark.createDataFrame(records, schema=BRONZE_SCHEMA)


def check_bronze(bronze: DataFrame) -> None:
    if bronze.limit(1).count() == 0:
        raise DataQualityError("No weather records were returned")

    required_columns = ["city", "record_date", *DAILY_VARIABLES]
    for column in required_columns:
        invalid = F.col(column).isNull()
        if column in DAILY_VARIABLES:
            invalid = invalid | F.isnan(F.col(column))
        if bronze.filter(invalid).limit(1).count():
            raise DataQualityError(f"Missing or NaN mandatory value in {column}")

    if bronze.filter(F.to_date("record_date").isNull()).limit(1).count():
        raise DataQualityError("Unparseable record_date")

    if bronze.filter(
        (F.col("temperature_2m_min") > F.col("temperature_2m_max"))
        | (F.col("precipitation_sum") < 0)
        | (F.col("wind_speed_10m_max") < 0)
    ).limit(1).count():
        raise DataQualityError("Impossible temperature range, negative rain, or negative wind")

    if bronze.groupBy("city", "record_date").count().filter("count > 1").limit(1).count():
        raise DataQualityError("Duplicate (city, date) found in API batch")


def make_silver(bronze: DataFrame) -> DataFrame:
    checked = (
        bronze.select(
            "city",
            F.to_date("record_date").alias("record_date"),
            F.col("temperature_2m_max").alias("temp_max_c"),
            F.col("temperature_2m_min").alias("temp_min_c"),
            F.col("precipitation_sum").alias("precipitation_mm"),
            F.col("wind_speed_10m_max").alias("wind_max_kmh"),
            "data_origin",
            "ingested_at",
        )
        .withColumn("heavy_rain", (F.col("precipitation_mm") >= HEAVY_PRECIPITATION_MM).cast("int"))
        .withColumn("strong_wind", (F.col("wind_max_kmh") >= STRONG_WIND_KMH).cast("int"))
        .withColumn("frost", (F.col("temp_min_c") <= FROST_C).cast("int"))
        .withColumn(
            "risk_score", F.col("heavy_rain") * 2 + F.col("strong_wind") * 2 + F.col("frost")
        )
        .withColumn(
            "risk_level",
            F.when(F.col("risk_score") >= 3, "high")
            .when(F.col("risk_score") >= 1, "medium")
            .otherwise("low"),
        )
        .withColumn(
            "risk_reasons",
            F.when(F.col("risk_score") == 0, F.lit("None")).otherwise(
                F.concat_ws(
                    ", ",
                    F.when(F.col("heavy_rain") == 1, F.lit("Heavy precipitation")),
                    F.when(F.col("strong_wind") == 1, F.lit("Strong wind")),
                    F.when(F.col("frost") == 1, F.lit("Frost")),
                )
            ),
        )
        .withColumn("year_month", F.date_format("record_date", "yyyy-MM"))
    )
    return checked


def make_gold(silver: DataFrame) -> DataFrame:
    return (
        silver.groupBy("city", "year_month", "data_origin")
        .agg(
            F.count("*").alias("days"),
            F.round(F.avg("temp_max_c"), 1).alias("avg_daily_max_c"),
            F.round(F.sum("precipitation_mm"), 1).alias("total_precipitation_mm"),
            F.sum("heavy_rain").alias("heavy_rain_days"),
            F.sum("strong_wind").alias("strong_wind_days"),
            F.sum("frost").alias("frost_days"),
            F.sum(F.when(F.col("risk_level") == "high", 1).otherwise(0)).alias("high_risk_days"),
        )
        .orderBy("city", "year_month")
    )
