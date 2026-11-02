"""Reproducible SYNTHETIC input, for demonstrations without an API connection."""
from datetime import date
from math import cos, sin, pi

from .api import expected_dates
from .config import DAILY_VARIABLES, City, TIMEZONE


def synthetic_weather(city: City, start: date, end: date) -> dict:
    days = expected_dates(start, end)
    seed = sum(ord(letter) for letter in city.name)
    daily = {"time": days, **{metric: [] for metric in DAILY_VARIABLES}}
    for index, day in enumerate(days):
        day_of_year = date.fromisoformat(day).timetuple().tm_yday
        seasonal = 10 + 10 * sin(2 * pi * (day_of_year - 105) / 365.25)
        temp_max = round(seasonal + (seed % 5) / 3 + 3 * sin(index * 0.65 + seed), 1)
        temp_min = round(temp_max - 4.5 - 1.3 * cos(index * 0.7), 1)
        rain = round(max(0, 9 * sin(index * 0.81 + seed / 12) + 5), 1)
        wind = round(max(1, 34 + 25 * cos(index * 0.31 + seed)), 1)
        for variable, value in zip(
            DAILY_VARIABLES, [temp_max, temp_min, rain, wind], strict=True
        ):
            daily[variable].append(value)
    return {"timezone": TIMEZONE, "daily": daily, "_demo_only": True}
