"""Streamlit interface for SQL-backed Nordic weather analytics."""
import os

import pandas as pd
import streamlit as st

from weather_risk.storage import get_all_weather

st.set_page_config(page_title="Nordic Weather Risk", page_icon="🌦️", layout="wide")
st.title("Nordic weather risk analytics")
st.caption("Historical weather analytics with transparent, illustrative risk rules")

with st.sidebar:
    st.header("Data source")
    mode = st.radio("Choose database", ["Real API data", "Synthetic demo"], index=0)
    db_url = os.getenv("DATABASE_URL") or (
        "sqlite:///data/demo_weather.db" if mode == "Synthetic demo" else "sqlite:///data/weather.db"
    )
    st.caption(f"Database: `{db_url.split('@')[-1]}`")

try:
    rows = get_all_weather(db_url)
except Exception as exc:
    st.error(f"Could not read database: {exc}")
    st.info("First run `weather-risk run --demo` or `weather-risk run` from the repository root.")
    st.stop()

if not rows:
    st.warning("No weather data yet. Run the pipeline first.")
    st.stop()

data = pd.DataFrame(rows)
data["record_date"] = pd.to_datetime(data["record_date"])
origins = sorted(data["data_origin"].unique().tolist())
with st.sidebar:
    active_origins = st.multiselect("Input origin", origins, default=origins)
    cities = st.multiselect("Cities", sorted(data["city"].unique().tolist()),
                            default=sorted(data["city"].unique().tolist()))

filtered = data[data["city"].isin(cities) & data["data_origin"].isin(active_origins)].copy()
if filtered.empty:
    st.info("Select at least one city and data origin.")
    st.stop()

if "synthetic_demo" in filtered["data_origin"].values:
    st.warning("SYNTHETIC DEMO DATA is included. These numbers are generated examples, not observed weather.")

# Do not count duplicate date-city records across sources as distinct observations.
total_rain = filtered["precipitation_mm"].sum()
high_risk_days = (filtered["risk_level"] == "high").sum()
col1, col2, col3, col4 = st.columns(4)
col1.metric("City-days", f"{len(filtered):,}")
col2.metric("Precipitation total", f"{total_rain:,.0f} mm")
col3.metric("Flagged high-risk days", f"{high_risk_days:,}")
col4.metric("Average daily max", f"{filtered['temp_max_c'].mean():.1f} °C")

st.subheader("Daily maximum temperature by city")
temp = filtered.pivot_table(index="record_date", columns="city", values="temp_max_c", aggfunc="mean")
st.line_chart(temp, height=260)

colA, colB = st.columns(2)
with colA:
    st.subheader("Total precipitation by city")
    rain = filtered.groupby("city", as_index=True)["precipitation_mm"].sum().sort_values()
    st.bar_chart(rain, height=240)
with colB:
    st.subheader("High-risk flagged days")
    high = (
        filtered.assign(high=(filtered["risk_level"] == "high").astype(int))
        .groupby("city")["high"].sum().sort_values()
    )
    st.bar_chart(high, height=240)

st.subheader("Daily records")
st.dataframe(filtered.sort_values(["record_date", "city"], ascending=[False, True]),
             hide_index=True, use_container_width=True)
st.caption(
    "High-risk thresholds are an illustrative rule set, not a validated prediction of "
    "transport disruption. Weather data by Open-Meteo.com (CC BY 4.0), when real data is selected."
)
st.markdown("[Source and API documentation](https://open-meteo.com/en/docs/historical-weather-api)")
