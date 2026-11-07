import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SETTINGS_FILE = BASE_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "waste_benchmark_pct": 9.0,
    "margin_floor_pct": 10.0,
    "occupancy_ceiling_pct": 25.0,
    "sub8_threshold_gbp": 8.0,
    "drinks_per_barista_hour": 16.5,
    "gemini_api_key": ""
}

def get_settings() -> dict:
    """Load persistent settings from JSON or return defaults."""
    settings = DEFAULT_SETTINGS.copy()
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                settings.update(saved)
        except Exception:
            pass
    # If API key not set in JSON, check environment variables
    if not settings.get("gemini_api_key"):
        settings["gemini_api_key"] = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
    return settings

def update_settings(new_settings: dict) -> dict:
    """Update settings and persist to settings.json."""
    current = get_settings()
    for k, v in new_settings.items():
        if k == "gemini_api_key":
            current[k] = str(v).strip()
        elif k in DEFAULT_SETTINGS:
            try:
                current[k] = float(v)
            except (ValueError, TypeError):
                pass
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2)
    return current
