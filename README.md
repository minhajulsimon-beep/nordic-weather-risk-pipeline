# Nordic Weather Risk Pipeline

[![Python / Spark CI](https://github.com/minhajulsimon-beep/nordic-weather-risk-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/minhajulsimon-beep/nordic-weather-risk-pipeline/actions/workflows/ci.yml)

**Portfolio data engineering project** | Python · PySpark · Parquet · SQL (SQLite/PostgreSQL) · Streamlit · GitHub Actions

> **Business question:** How can a logistics analyst compare historical precipitation, wind and frost conditions across Aarhus, Copenhagen, Odense and Aalborg?
>
> This is an **analysis of historical weather**, not a forecast, nor a validated prediction of transportation disruption.

![Synthetic demo: weather overview across four Danish cities](assets/demo_overview.png)

*Screenshot: deterministic **synthetic demo data** generated for this repository. It does not show actual measured or reanalyzed weather.*

## What this demonstrates

- **API integration:** Historical weather pulled from Open-Meteo's ERA5 reanalysis (no API key for non-commercial use); HTTP retry/backoff and response validation.
- **Medallion architecture:** Timestamped raw JSON snapshots, typed Bronze Parquet, cleaned Silver Parquet with explainable flags, and monthly Gold Parquet aggregations.
- **Data quality:** Reject incomplete date windows, missing/NaN readings, impossible min/max temperatures, negative rain/wind and duplicate city/date keys.
- **Idempotent loads:** SQL primary key `(city, record_date)` and `ON CONFLICT ... DO UPDATE`. Re-run backfills safely without duplicate SQL records.
- **Analytics:** SQL questions about flagged days and monthly weather patterns, plus an interactive Streamlit dashboard.
- **Engineering hygiene:** Tested transformations and SQL sink, offline Spark integration test, GitHub Actions CI, type hints, source attribution, and `.gitignore` excluding generated datasets and credentials.

## Pipeline architecture

```mermaid
flowchart TD
    A[Open-Meteo ERA5 historical API] --> B[Raw JSON per run]
    Z[Synthetic demo input] -. Offline testing .-> B
    B --> C[PySpark Bronze table]
    C --> D{Data quality checks}
    D -- Invalid --> E[Fail without SQL write]
    D -- Valid --> F[PySpark Silver: cleaned daily records and flags]
    F --> G[PySpark Gold: monthly summary]
    F --> H[(SQLite or PostgreSQL: daily weather UPSERT)]
    H --> I[SQL analytics queries]
    H --> J[Streamlit dashboard]
```

## Quick start on macOS/Linux

**Prerequisites:** Python 3.11+ and a JDK 17+ installed (`java -version`). Java is required for running local PySpark. No API credentials or Docker are needed for the SQLite path.

```bash
# From the extracted project folder
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,dashboard]'

# 1. Offline trial with obviously SYNTHETIC weather; creates data/demo_weather.db
weather-risk run --demo --days 30

# 2. Look at the SQL summaries from that demo
weather-risk summary --db-url sqlite:///data/demo_weather.db

# 3. View the interactive dashboard (choose Synthetic demo in its sidebar)
streamlit run dashboard/app.py
```

When you're ready, run the **real historical API**:

```bash
# Default = 90 days, ending seven days before today to allow ERA5 processing
weather-risk run --days 90
weather-risk summary

# Choose Real API data in the dashboard (stop/restart Streamlit if needed)
streamlit run dashboard/app.py
```

Your `data/` folder contains the original JSON, Bronze/Silver/Gold Parquet outputs, and SQLite databases. `data/` is ignored by Git. The two input modes default to **separate databases** to prevent mixing synthetic and historical data.

If the local Spark process cannot start on macOS, verify that `java -version` works and that you installed a supported JDK; set `JAVA_HOME` to that JDK if necessary.

### Reproducible historical backfill

```bash
weather-risk run --start 2026-07-01 --end 2026-09-30
```

You can run the same dates repeatedly: the SQL record count for those dates will not increase. API fetches are repeated (there is no automatic cache reuse). Raw per-run JSON remains available for auditing. The Silver and Gold Parquet folders named `latest` are **snapshots of the most recent requested window**; the SQL table accumulates records across different runs.

### Optional PostgreSQL

If Docker Compose is available:

```bash
docker compose up -d
python -m pip install -e '.[postgres]'
weather-risk run --days 90 --db-url 'postgresql://weather:weather@localhost:5432/weather'
```

To view the PostgreSQL database in Streamlit:

```bash
export DATABASE_URL='postgresql://weather:weather@localhost:5432/weather'
streamlit run dashboard/app.py
```

The Compose password is for **local development only**. Never publish real passwords in Git or commit a local `.env` file. For this small four-city batch, the SQL sink streams transformed rows through the driver; production-scale workloads should use a distributed JDBC/warehouse sink.

## Data model

One SQL record = **one city and one calendar day**.

| Column | Meaning |
|---|---|
| `city`, `record_date` | Composite primary key for idempotent loads |
| `temp_max_c`, `temp_min_c` | Daily 2-meter min/max temperatures in Celsius |
| `precipitation_mm`, `wind_max_kmh` | Daily precipitation (mm) and max wind speed at 10 m (km/h) |
| `heavy_rain`, `strong_wind`, `frost` | Explainable binary conditions |
| `risk_score`, `risk_level`, `risk_reasons` | **Demonstration-only** heuristic and reasons |
| `year_month` | Portable SQL aggregation column (`YYYY-MM`) |
| `data_origin`, `ingested_at` | Source label and last ingested timestamp |

### How risk is calculated

| Flag | Threshold | Added score |
|---|---|---:|
| Heavy precipitation | `precipitation_mm >= 10` | +2 |
| Strong wind | `wind_max_kmh >= 50` | +2 |
| Frost | `temp_min_c <= 0` | +1 |

`low` = score 0, `medium` = scores 1–2, `high` = scores 3–5. These thresholds are **arbitrary educational examples**, not operational safety rules. An actual logistics warning model would require input from shipping operators, historical disruption labels, validation, and more fine-grained forecasts.

## Insights you can demonstrate in an interview

- Which city has the highest **percentage** of flagged high-risk days in the date window?
- Do heavy-precipitation and strong-wind flags occur together?
- Which months have the most precipitation or frost days?
- Does rerunning the same backfill duplicate any SQL records? **No**, because of the primary key and upsert.

The ready-to-run SQL queries are in [`sql/insights.sql`](sql/insights.sql). Run them independently in SQLite or PostgreSQL.

## Testing and continuous integration

```bash
python -m pytest -v
```

The test suite includes API format checks with mocked network access, deterministic synthetic input, SQLite upsert tests, Spark transformation/quality tests, and a full **offline Spark → SQLite integration test** run twice to verify idempotency. `.github/workflows/ci.yml` runs tests on each push and pull request with Java 17 and Python 3.11.

> **Validation status:** Source and lightweight tests were checked while preparing this repository. The live API, a real Spark job, and PostgreSQL were **not executed** in the authoring environment because external package downloads and API network access were unavailable. Run the above tests and live backfill on your own machine; GitHub Actions will also run the Spark tests after the repository is published. Do not represent those steps as verified until they pass.

## Repository layout

```text
nordic-weather-risk-pipeline/
├── .github/workflows/ci.yml    # Tests on every push / PR
├── src/weather_risk/
│   ├── api.py                  # Request retries, payload checks
│   ├── config.py               # Danish cities and thresholds
│   ├── demo.py                 # Synthetic offline input
│   ├── transform.py            # Spark Bronze / Silver / Gold
│   ├── storage.py              # SQL schema and upserts
│   ├── pipeline.py             # End-to-end orchestration
│   └── cli.py                  # `weather-risk` commands
├── tests/                       # Unit + offline Spark integration tests
├── dashboard/app.py            # Streamlit dashboard
├── sql/insights.sql             # Analyst-facing SQL queries
├── assets/demo_overview.png    # Clearly labeled synthetic visual
├── docs/decisions.md           # Engineering tradeoffs and limitations
├── docker-compose.yml          # Optional local PostgreSQL
├── pyproject.toml              # Package + dependency extras
└── .env.example                # Environment variable reference
```

## Data sources, limits and attribution

Real weather data comes from [Open-Meteo's Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api), using the **ERA5 historical reanalysis model**. Reanalysis combines measurements with numerical modeling: a queried location reflects model/grid data, not necessarily readings at a weather station in the city center. ERA5 availability usually lags several days; this is why the CLI defaults to an end date seven days ago.

**Weather data by [Open-Meteo.com](https://open-meteo.com/)**, provided under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). This repository processes and visualizes the data and adds its own illustrative risk flags. Open-Meteo's no-key hosted tier is intended for non-commercial use, subject to usage policies; commercial use may require a subscription. Source code in this repository is MIT licensed.

For design and production caveats see [`docs/decisions.md`](docs/decisions.md).

## Explain it to recruiters

A short project walkthrough and the engineering tradeoffs you should be ready to discuss are in [`docs/interview_notes.md`](docs/interview_notes.md). The strongest honest answer to **"Why Spark for such a small dataset?"** is that this is a scoped learning-and-portfolio implementation; Spark adds overhead at this scale, but using its native transformations demonstrates skills that generalize to larger pipelines.
