"""Command-line interface for reproducible historical backfills."""
import argparse
from datetime import date, timedelta
import os

from .config import date_window
from .pipeline import run_pipeline
from .storage import get_city_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="weather-risk", description="Nordic weather risk ETL and analytics"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Fetch, transform, and load historical data")
    run.add_argument("--start", type=date.fromisoformat, help="YYYY-MM-DD")
    run.add_argument("--end", type=date.fromisoformat, help="YYYY-MM-DD")
    run.add_argument("--days", type=int, default=90, help="Days including end (default 90)")
    run.add_argument("--demo", action="store_true", help="Use synthetic input; NO API call")
    run.add_argument("--db-url", default=None)
    run.add_argument("--data-dir", default=os.getenv("DATA_DIR", "data"))

    summary = sub.add_parser("summary", help="Show aggregated records from SQL")
    summary.add_argument("--db-url", default=os.getenv("DATABASE_URL", "sqlite:///data/weather.db"))
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == "summary":
        print_summary(get_city_summary(args.db_url))
        return
    if args.days <= 0:
        raise SystemExit("--days must be positive")
    _, default_end = date_window(args.days)
    end = args.end or default_end
    start = args.start or (end - timedelta(days=args.days - 1))
    if start > end:
        raise SystemExit("--start cannot be after --end")
    print(f"Running {start} to {end}; input={'SYNTHETIC DEMO' if args.demo else 'Open-Meteo ERA5'}")
    db_url = args.db_url or os.getenv("DATABASE_URL") or (
        "sqlite:///data/demo_weather.db" if args.demo else "sqlite:///data/weather.db"
    )
    result = run_pipeline(
        start=start, end=end, db_url=db_url, data_dir=args.data_dir, demo=args.demo
    )
    print(f"Upserted {result['processed_rows']} rows; source={result['origin']}")
    print(f"Raw JSON: {result['raw_path']}")
    print(f"Silver snapshot: {result['silver_path']}")
    print_summary(result["summary"])


def print_summary(rows):
    if not rows:
        print("No records found. Run 'weather-risk run' first.")
        return
    print("\nCity            Source                 Days   Rain (mm)   High-risk days")
    print("-" * 76)
    for row in rows:
        print(
            f"{row['city']:<15} {row['data_origin']:<22} "
            f"{row['days']:>4} {row['total_precipitation_mm']:>12} "
            f"{row['high_risk_days']:>12}"
        )


if __name__ == "__main__":
    main()
