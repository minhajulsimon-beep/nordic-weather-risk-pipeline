"""Stable geography and API configuration for Denmark."""
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class City:
    name: str
    latitude: float
    longitude: float


CITIES = (
    City("Aarhus", 56.1629, 10.2039),
    City("Copenhagen", 55.6761, 12.5683),
    City("Odense", 55.4038, 10.4024),
    City("Aalborg", 57.0488, 9.9217),
)

API_URL = "https://archive-api.open-meteo.com/v1/archive"
DAILY_VARIABLES = (
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "wind_speed_10m_max",
)
TIMEZONE = "Europe/Copenhagen"

# Illustrative operational flags, NOT a validated disruption model.
HEAVY_PRECIPITATION_MM = 10.0
STRONG_WIND_KMH = 50.0
FROST_C = 0.0


def date_window(days: int = 90, lag_days: int = 7, today: date | None = None):
    if days <= 0:
        raise ValueError("days must be positive")
    if lag_days < 0:
        raise ValueError("lag_days must be non-negative")
    end = (today or date.today()) - timedelta(days=lag_days)
    start = end - timedelta(days=days - 1)
    return start, end
