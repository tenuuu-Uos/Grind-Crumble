import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "grind_and_crumb.db"

# Chain benchmarks and assumptions as defined in SRS & Data Pack
CHAIN_BENCHMARKS = {
    "waste_benchmark_pct": 9.0,           # Chain target 9.0%
    "fixed_occupancy_max_pct": 25.0,      # Alert if Rent + Rates > 25% of sales
    "labor_on_cost_multiplier": 1.13,     # Labour cost = scheduled_hours * avg_hourly_wage * 1.13
    "packaging_cost_per_delivery_gbp": 0.45,
    "delivery_prep_minutes": 4.0,         # 4 minutes labor per delivery order
    "default_nlw_increase_pct": 6.7,      # 6.7% National Living Wage increase
    "sub_8_threshold_gbp": 8.0,           # Sub-£8 delivery order threshold
}

APP_TITLE = "Grind & Crumb Operational Intelligence Dashboard"
APP_VERSION = "1.0.0"
