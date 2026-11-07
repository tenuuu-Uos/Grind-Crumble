import sqlite3
from typing import Optional
from fastapi import APIRouter, Depends, Query
from app.db.session import get_db
from app.core.rbac import get_current_user, verify_store_access, UserPersona
from app.services.pnl_service import PnLService

router = APIRouter(prefix="/api/pnl", tags=["Module 1: Profitability & Occupancy"])

@router.get("/ranking")
def get_store_ranking(
    month: Optional[str] = Query(None, description="Month in YYYY-MM format, e.g. 2025-07"),
    store_id: Optional[str] = Query(None, description="Optional store filter"),
    user: UserPersona = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    FR-1.1: True Profit Heatmap.
    Ranks stores by Operating Margin (%) and Net Profit (£) rather than gross volume.
    Enforces RBAC: Store managers see only their assigned store.
    """
    effective_store_id = verify_store_access(user, store_id)
    service = PnLService(db)
    stores = service.get_network_ranking(month=month, store_id=effective_store_id)
    return {
        "status": "success",
        "user_role": user.role,
        "is_restricted_view": not user.can_view_all_stores,
        "stores": stores
    }

@router.get("/occupancy-alerts")
def get_occupancy_alerts(
    user: UserPersona = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    FR-1.2: Fixed Occupancy Calculator.
    Tracks Rent + Rates as % of sales. Alerts when > 25% (e.g. S07 Piccadilly at 40.2%).
    """
    service = PnLService(db)
    data = service.get_fixed_occupancy_calculator()
    if not user.can_view_all_stores:
        data["stores"] = [s for s in data["stores"] if s["store_id"] == user.store_id]
        data["alerts"] = [a for a in data["alerts"] if a["store_id"] == user.store_id]
    return {"status": "success", **data}

@router.get("/cannibalization")
def get_cannibalization(
    user: UserPersona = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    FR-1.3: Cannibalization Audit Tool.
    Compares pre- and post-opening metrics for Leeds Trinity (S12) vs Leeds Briggate (S03).
    """
    service = PnLService(db)
    return {"status": "success", **service.get_cannibalization_audit()}
