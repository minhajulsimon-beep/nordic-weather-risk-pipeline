# Nordic Weather Risk Pipeline

[![Python / Spark CI](https://github.com/minhajulsimon-beep/nordic-weather-risk-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/minhajulsimon-beep/nordic-weather-risk-pipeline/actions/workflows/ci.yml)

A Python and PySpark pipeline for analyzing historical weather across Aarhus, Copenhagen, Odense and Aalborg. It retrieves daily data from Open-Meteo's ERA5 archive, processes it into Parquet datasets, loads the cleaned records into SQL, and displays the results in Streamlit.

## How it works

```text
Open-Meteo ERA5 API
       |
       v
  Raw JSON snapshots
       |
       v
  PySpark Bronze (typed data)
       |
       v
  Validation + Silver (daily weather and condition flags)
       |                                |
       v                                v
  Gold (monthly Parquet)          SQLite / PostgreSQL
                                        |
                                        v
                                Streamlit dashboard
```

The pipeline stores a copy of each API response before processing it. The API response is checked for missing dates and fields. PySpark then validates the daily values, including duplicate city/date records and invalid temperature, precipitation or wind readings. The Silver dataset contains the cleaned daily records and weather-condition flags; Gold contains monthly summaries by city.

SQL loads use `ON CONFLICT DO UPDATE` with `(city, record_date)` as the primary key, so rerunning a date range updates existing records rather than creating duplicates.

## Dashboard

![Nordic Weather Risk Analytics Dashboard](assets/dashboard-real-data.png)

Interactive Streamlit dashboard displaying 90 days of historical
ERA5 weather data across Aarhus, Copenhagen, Odense, and Aalborg.

## Run the project

Requires Python 3.11 or 3.12 and Java 17. The commands below work in a Linux environment such as GitHub Codespaces with Python 3.12 available.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,dashboard]'

weather-risk run --days 90
weather-risk summary
streamlit run dashboard/app.py
```

Open port `8501` to view the dashboard. It reads from `data/weather.db` by default; select **Real API data** in the sidebar.

For a run without external API requests:

```bash
weather-risk run --demo --days 30
weather-risk summary --db-url sqlite:///data/demo_weather.db
```

The demo uses generated data and writes to a separate database.

You can also request a fixed historical window:

```bash
weather-risk run --start 2026-07-01 --end 2026-09-30
```

With no dates specified, the pipeline requests the most recent 90-day window ending seven days before the current date to account for ERA5 availability.

## Example results

A 90-day ERA5 backfill run on 2 November 2026 loaded 360 daily records across the four cities.

| City | Total precipitation | Days flagged high |
| --- | ---: | ---: |
| Aalborg | 210.8 mm | 0 |
| Aarhus | 181.9 mm | 0 |
| Copenhagen | 226.1 mm | 0 |
| Odense | 181.6 mm | 1 |

These are results for that historical window, not forecasts. The weather flags are simple configurable rules: at least 10 mm of daily precipitation adds 2 points, wind of at least 50 km/h adds 2, and a minimum temperature of 0°C or below adds 1. A score of 3 or more is labeled `high`. The labels have not been validated against actual transport disruptions.

## Files and storage

```text
src/weather_risk/       API client, Spark transformations, storage and CLI
dashboard/app.py        Streamlit dashboard
tests/                  Unit and integration tests
sql/insights.sql        SQL analysis queries
.github/workflows/      CI workflow
data/raw/<run-id>/      API responses saved per run
data/lake/bronze/       Typed Parquet records per run
data/lake/silver/latest/  Clean daily Parquet snapshot
data/lake/gold/latest/    Monthly Parquet snapshot
data/weather.db         SQLite database for real data
```

The `data/` directory is generated at runtime and excluded from Git. Silver and Gold `latest` directories are replaced each run; the SQL table keeps records across multiple backfills.

SQLite is the default database. PostgreSQL is supported as an alternative for local development:

```bash
docker compose up -d
python -m pip install -e '.[postgres]'
weather-risk run --days 90 --db-url 'postgresql://weather:weather@localhost:5432/weather'
```

The connection values above belong to the local Docker Compose setup, not a hosted database.

## Tests

```bash
python -m pytest -v
```

Tests cover API response validation, transformation rules, data-quality checks, SQLite upserts, and an offline Spark-to-SQLite run. GitHub Actions runs the test suite on pushes and pull requests.

## Data source and license

Weather data: [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api), using ERA5 reanalysis. Reanalysis is model-based historical data and may differ from individual weather-station readings. Weather data by [Open-Meteo.com](https://open-meteo.com/) is attributed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); use of the hosted API is subject to Open-Meteo's terms.

Project code: [MIT License](LICENSE).
