from copy import deepcopy
from datetime import date

import pytest
import requests

from weather_risk.api import (
    WeatherAPIError, expected_dates, fetch_city_weather, flatten_city,
    validate_payload,
)
from weather_risk.config import CITIES, DAILY_VARIABLES
from weather_risk.demo import synthetic_weather


START = date(2026, 6, 1)
END = date(2026, 6, 4)


def test_expected_dates_inclusive_and_order():
    assert expected_dates(START, END) == [
        "2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04"
    ]
    with pytest.raises(ValueError):
        expected_dates(END, START)


def test_api_fixture_shapes_and_flatten():
    payload = synthetic_weather(CITIES[0], START, END)
    validate_payload(payload, START, END)
    flattened = flatten_city("Aarhus", payload, START, END)
    assert len(flattened) == 4
    assert flattened[0]["city"] == "Aarhus"
    assert set(DAILY_VARIABLES).issubset(flattened[0])


def test_missing_date_or_metric_is_rejected():
    payload = synthetic_weather(CITIES[0], START, END)
    missing_date = deepcopy(payload)
    missing_date["daily"]["time"].pop()
    with pytest.raises(WeatherAPIError, match="date range"):
        validate_payload(missing_date, START, END)

    bad_metric = deepcopy(payload)
    bad_metric["daily"]["precipitation_sum"].pop()
    with pytest.raises(WeatherAPIError, match="metric"):
        validate_payload(bad_metric, START, END)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.params = None

    def get(self, url, params, timeout):
        self.params = params
        assert url.endswith("/v1/archive")
        assert timeout == (10, 45)
        return FakeResponse(self.payload)


def test_fetch_constructs_era5_request_without_network():
    fake = FakeSession(synthetic_weather(CITIES[0], START, END))
    payload = fetch_city_weather(CITIES[0], START, END, session=fake)
    assert payload["daily"]["time"][0] == "2026-06-01"
    assert fake.params["models"] == "era5"
    assert fake.params["timezone"] == "Europe/Copenhagen"
