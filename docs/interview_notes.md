# Interview talking points (only claim what you have actually run)

## 45-second project walkthrough

> I built a historical weather ETL project to explore conditions that could matter to logistics operations across four Danish cities. The ingestion layer requests historical temperature, wind and precipitation from Open-Meteo. I used PySpark for schema validation and a Bronze/Silver/Gold approach, added explainable rule-based weather flags, and stored daily results in a SQL table with a composite primary key. The upsert means the same historical period can be processed again without duplicate records. I also provided SQL analysis queries, a Streamlit dashboard, and tests that run automatically in GitHub Actions. It's historical analytics, not an operational prediction model.

## Good technical questions to be ready for

**Why PySpark when there are only four cities?**
I intentionally used a modest, inspectable dataset to learn and demonstrate the distributed DataFrame API, schemas, aggregations and Parquet formats. I would use plain Python or SQL for a tiny real-world workload to avoid Spark overhead. For growth, I'd parameterize the geography, shard API requests, and use a distributed warehouse/JDBC sink.

**How do you avoid duplicate records?**
The daily analytics table has a `(city, record_date)` primary key. Inserts use `ON CONFLICT DO UPDATE`. This gives idempotent row counts and allows later reanalysis data to replace an older value. The raw source snapshots remain unchanged.

**What happens if the API fails?**
Requests retry transient errors such as HTTP 429 or 503. An incomplete response or invalid weather values makes the run fail before the SQL upsert. Original JSON files are retained as an audit trail for successful fetches.

**Why not call this a production-ready risk predictor?**
The weights and thresholds are illustrative rules. A trustworthy logistics risk product would require actual delay/incident labels, stakeholder-defined thresholds, model validation, and monitoring for false positives and false negatives.

**What's next?**
Use a workflow orchestrator for scheduled daily refreshes; use Delta Lake/Iceberg with atomic snapshots; replace driver-side upsert with distributed writes; include observability metrics and CI validation against a PostgreSQL service.

## Demo order for recruiters

1. Open the project's GitHub README and point to the architecture diagram.
2. Run `weather-risk run --demo --days 30` and explain that the input is **synthetic**.
3. Run `weather-risk summary --db-url sqlite:///data/demo_weather.db`.
4. Run the same demo command again and use a SQL `SELECT COUNT(*)` to prove the PK prevents duplicates.
5. Open the Streamlit dashboard and show city comparisons and flagged days.
6. Run `weather-risk run --days 90` with the actual API before claiming a real-data demonstration.
7. Show the GitHub Actions test results, once they have passed.
