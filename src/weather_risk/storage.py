"""Idempotent SQL sink: SQLite by default, PostgreSQL via optional dependency."""
from contextlib import contextmanager
from pathlib import Path
from datetime import date, datetime
import sqlite3


SILVER_FIELDS = (
    "city", "record_date", "temp_max_c", "temp_min_c", "precipitation_mm",
    "wind_max_kmh", "heavy_rain", "strong_wind", "frost", "risk_score",
    "risk_level", "risk_reasons", "year_month", "data_origin", "ingested_at",
)


@contextmanager
def connection(db_url: str):
    if db_url.startswith("sqlite:///"):
        path = Path(db_url[len("sqlite:///"):])
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        dialect = "sqlite"
    elif db_url.startswith(("postgresql://", "postgres://")):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError('For PostgreSQL run: pip install -e ".[postgres]"') from exc
        conn = psycopg.connect(db_url, row_factory=dict_row, connect_timeout=15)
        dialect = "postgres"
    else:
        raise ValueError("DATABASE_URL must start with sqlite:/// or postgresql://")

    try:
        yield conn, dialect
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize_database(db_url: str) -> None:
    with connection(db_url) as (conn, dialect):
        date_type = "TEXT" if dialect == "sqlite" else "DATE"
        number_type = "REAL" if dialect == "sqlite" else "DOUBLE PRECISION"
        timestamp_type = "TEXT" if dialect == "sqlite" else "TIMESTAMPTZ"
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS weather_daily (
                city TEXT NOT NULL,
                record_date {date_type} NOT NULL,
                temp_max_c {number_type} NOT NULL,
                temp_min_c {number_type} NOT NULL,
                precipitation_mm {number_type} NOT NULL,
                wind_max_kmh {number_type} NOT NULL,
                heavy_rain INTEGER NOT NULL,
                strong_wind INTEGER NOT NULL,
                frost INTEGER NOT NULL,
                risk_score INTEGER NOT NULL,
                risk_level TEXT NOT NULL,
                risk_reasons TEXT NOT NULL,
                year_month TEXT NOT NULL,
                data_origin TEXT NOT NULL,
                ingested_at {timestamp_type} NOT NULL,
                PRIMARY KEY (city, record_date)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_weather_month
            ON weather_daily (year_month, city)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_weather_risk
            ON weather_daily (risk_level, record_date)
        """)


def _prepare_rows(records, dialect: str):
    """Accept Spark Rows or dictionaries; adapt date/timestamp values per SQL driver."""
    for record in records:
        values = []
        for key in SILVER_FIELDS:
            value = record[key]
            if key == "record_date":
                if dialect == "sqlite" and hasattr(value, "isoformat"):
                    value = value.isoformat()
                elif dialect == "postgres" and isinstance(value, str):
                    value = date.fromisoformat(value)
            if key == "ingested_at" and dialect == "postgres" and isinstance(value, str):
                value = datetime.fromisoformat(value)
            values.append(value)
        yield tuple(values)


def upsert_records(db_url: str, records) -> int:
    """Small bounded batch sink; use distributed JDBC for large workloads."""
    initialize_database(db_url)
    count = 0
    with connection(db_url) as (conn, dialect):
        placeholder = "?" if dialect == "sqlite" else "%s"
        fields = ", ".join(SILVER_FIELDS)
        values = ", ".join([placeholder] * len(SILVER_FIELDS))
        updates = ", ".join(
            f"{name} = EXCLUDED.{name}" for name in SILVER_FIELDS if name not in ("city", "record_date")
        )
        statement = f"""
            INSERT INTO weather_daily ({fields}) VALUES ({values})
            ON CONFLICT (city, record_date) DO UPDATE SET {updates}
        """
        cursor = conn.cursor()
        batch = []
        for row in _prepare_rows(records, dialect):
            batch.append(row)
            if len(batch) == 200:
                cursor.executemany(statement, batch)
                count += len(batch)
                batch = []
        if batch:
            cursor.executemany(statement, batch)
            count += len(batch)
        cursor.close()
    return count


def fetch_query(db_url: str, sql: str) -> list[dict]:
    with connection(db_url) as (conn, _):
        cursor = conn.execute(sql)
        column_names = [description[0] for description in cursor.description]
        result = [dict(row) if isinstance(row, dict) else dict(zip(column_names, row))
                  for row in cursor.fetchall()]
        cursor.close()
        return result


def get_city_summary(db_url: str) -> list[dict]:
    initialize_database(db_url)
    return fetch_query(db_url, """
        SELECT city, data_origin, COUNT(*) AS days,
               ROUND(AVG(temp_max_c), 1) AS avg_daily_max_c,
               ROUND(SUM(precipitation_mm), 1) AS total_precipitation_mm,
               SUM(CASE WHEN risk_level = 'high' THEN 1 ELSE 0 END) AS high_risk_days
        FROM weather_daily
        GROUP BY city, data_origin
        ORDER BY city, data_origin
    """)


def get_all_weather(db_url: str) -> list[dict]:
    initialize_database(db_url)
    return fetch_query(db_url, """
        SELECT city, record_date, temp_max_c, temp_min_c, precipitation_mm,
               wind_max_kmh, risk_score, risk_level, risk_reasons, data_origin
        FROM weather_daily
        ORDER BY record_date, city
    """)
