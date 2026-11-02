"""Create an explicitly labeled SYNTHETIC illustration for the README."""
from datetime import date, timedelta
from pathlib import Path
import sys

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from weather_risk.config import CITIES
from weather_risk.demo import synthetic_weather

start = date(2026, 10, 1)
end = start + timedelta(days=29)

fig, axes = plt.subplots(2, 1, figsize=(11.5, 6.6), sharex=True, constrained_layout=True)
for city in CITIES:
    payload = synthetic_weather(city, start, end)
    days = [date.fromisoformat(x) for x in payload["daily"]["time"]]
    axes[0].plot(days, payload["daily"]["temperature_2m_max"], label=city.name, linewidth=1.8)
    axes[1].plot(days, payload["daily"]["precipitation_sum"], label=city.name, linewidth=1.5)
axes[0].set_ylabel("Daily maximum (C)")
axes[1].set_ylabel("Precipitation (mm)")
axes[1].set_xlabel("October 2026")
axes[0].legend(ncol=4, loc="upper center", fontsize=9)
axes[0].grid(alpha=0.2)
axes[1].grid(alpha=0.2)
fig.suptitle("Nordic weather analytics | SYNTHETIC DEMO DATA", fontsize=16, fontweight="bold")
fig.text(0.99, 0.01, "Illustrative synthetic dataset - not actual weather observations", ha="right", fontsize=9)
(ROOT / "assets").mkdir(exist_ok=True)
fig.savefig(ROOT / "assets" / "demo_overview.png", dpi=160, bbox_inches="tight")
print("Wrote assets/demo_overview.png")
