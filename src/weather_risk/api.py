"""Retrieve and validate daily historical Open-Meteo API responses."""
from datetime import date, timedelta

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import API_URL, DAILY_VARIABLES, TIMEZONE, City


class WeatherAPIError(ValueError):
    """Raised when the remote API returns an unusable response."""


def create_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.7,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session


def expected_dates(start: date, end: date) -> list[str]:
    if end < start:
        raise ValueError("end date must be on or after start date")
    return [(start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)]


def validate_payload(payload: dict, start: date, end: date) -> None:
    if not isinstance(payload, dict) or payload.get("error"):
        raise WeatherAPIError(f"API reported an error: {str(payload)[:200]}")
    daily = payload.get("daily")
    if not isinstance(daily, dict):
        raise WeatherAPIError("Missing daily metrics in API response")

    dates = daily.get("time")
    expected = expected_dates(start, end)
    if dates != expected:
        raise WeatherAPIError(
            "API returned an incomplete, unexpected, or unordered date range: "
            f"expected {len(expected)} days, received {len(dates) if isinstance(dates, list) else 'none'}"
        )
    for metric in DAILY_VARIABLES:
        series = daily.get(metric)
        if not isinstance(series, list) or len(series) != len(expected):
            raise WeatherAPIError(f"Missing or incomplete metric: {metric}")


def fetch_city_weather(
    city: City, start: date, end: date, session: requests.Session | None = None
) -> dict:
    session = session or create_session()
    params = {
        "latitude": city.latitude,
        "longitude": city.longitude,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": ",".join(DAILY_VARIABLES),
        "timezone": TIMEZONE,
        "models": "era5",  # consistent reanalysis; typically available after a delay
    }
    response = session.get(API_URL, params=params, timeout=(10, 45))
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError as exc:
        raise WeatherAPIError("API returned invalid JSON") from exc
    validate_payload(payload, start, end)
    return payload


def flatten_city(city_name: str, payload: dict, start: date, end: date) -> list[dict]:
    validate_payload(payload, start, end)
    daily = payload["daily"]
    return [
        {
            "city": city_name,
            "record_date": record_date,
            **{metric: daily[metric][i] for metric in DAILY_VARIABLES},
        }
        for i, record_date in enumerate(daily["time"])
    ]
