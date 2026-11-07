import sqlite3
from typing import Optional
from fastapi import APIRouter, Depends, Query
from app.db.session import get_db
from app.core.rbac import get_current_user, verify_store_access, UserPersona
from app.services.waste_service import WasteService

router = APIRouter(prefix="/api/waste", tags=["Module 4: Inventory Shrinkage & Par Optimizer"])

@router.get("/variance")
def get_waste_variance(
    store_id: Optional[str] = Query(None),
    user: UserPersona = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    FR-4.1: Waste Rate Variance Tracker.
    Flags stores exceeding 9.0% benchmark (e.g. Hull Paragon S10 at 20.7%).
    """
    effective_store_id = verify_store_access(user, store_id)
    service = WasteService(db)
    return {"status": "success", **service.get_waste_variance(store_id=effective_store_id)}

@router.get("/dynamic-par")
def get_dynamic_par(
    store_id: Optional[str] = Query("S10"),
    day_of_week: Optional[str] = Query("Wednesday"),
    weather: Optional[str] = Query("Rainy"),
    user: UserPersona = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    FR-4.2: Dynamic Par Recommendation.
    Generates prep recommendations based on day-of-week, weather forecasts, and student/office density.
    """
    effective_store_id = verify_store_access(user, store_id) or "S10"
    service = WasteService(db)
    return {
        "status": "success",
        **service.get_dynamic_par_recommendation(
            store_id=effective_store_id,
            day_of_week=day_of_week or "Wednesday",
            weather_type=weather or "Rainy"
        )
    }

@router.get("/stockouts")
def get_stockouts(
    store_id: Optional[str] = Query("S06"),
    user: UserPersona = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    FR-4.3: Early Stockout Monitor.
    Detects categories running out of inventory before 1:30 PM (e.g. Spinningfields S06 sandwiches).
    """
    effective_store_id = verify_store_access(user, store_id) or "S06"
    service = WasteService(db)
    return {"status": "success", **service.get_early_stockouts(store_id=effective_store_id)}
