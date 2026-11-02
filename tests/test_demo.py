from datetime import date

from weather_risk.config import CITIES, date_window
from weather_risk.demo import synthetic_weather


def test_default_window_uses_lag_to_avoid_recent_unavailable_era5():
    start, end = date_window(days=30, lag_days=7, today=date(2026, 11, 2))
    assert end == date(2026, 10, 26)
    assert start == date(2026, 9, 27)


def test_demo_is_deterministic_and_explicitly_labeled():
    start, end = date(2026, 9, 1), date(2026, 9, 10)
    a = synthetic_weather(CITIES[0], start, end)
    b = synthetic_weather(CITIES[0], start, end)
    assert a == b
    assert a["_demo_only"] is True
    assert len(a["daily"]["time"]) == 10
