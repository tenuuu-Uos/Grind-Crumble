import sqlite3
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query
from app.db.session import get_db
from app.core.rbac import get_current_user, verify_store_access, UserPersona
from app.services.labor_service import LaborService

router = APIRouter(prefix="/api/labor", tags=["Module 3: Labor & Throughput Command Center"])

class WageStressRequest(BaseModel):
    wage_increase_pct: float = 6.7
    price_offset_pct: float = 0.0
    store_id: Optional[str] = None

@router.get("/bottlenecks")
def get_bottlenecks(
    store_id: Optional[str] = Query(None),
    user: UserPersona = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    FR-3.1: 11am-2pm Bottleneck Index.
    Overlays footfall sensor data against active barista headcount and transactions.
    """
    effective_store_id = verify_store_access(user, store_id)
    service = LaborService(db)
    return {"status": "success", **service.get_bottleneck_index(store_id=effective_store_id)}

@router.get("/walkouts")
def get_walkouts(
    store_id: Optional[str] = Query(None),
    user: UserPersona = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    FR-3.2: Walkout Revenue Loss Estimator.
    Calculates uncaptured walkway revenue during peak rush hours.
    """
    effective_store_id = verify_store_access(user, store_id)
    service = LaborService(db)
    return {"status": "success", **service.get_walkout_revenue_loss(store_id=effective_store_id)}

@router.post("/wage-stress")
def test_wage_stress(
    req: WageStressRequest,
    user: UserPersona = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    FR-3.3: Labor Inflation Stress Tester.
    Models profit impact of mandatory wage increases against sales per labor hour.
    """
    effective_store_id = verify_store_access(user, req.store_id)
    service = LaborService(db)
    return {
        "status": "success",
        **service.simulate_labor_inflation_stress(
            wage_increase_pct=req.wage_increase_pct,
            price_offset_pct=req.price_offset_pct,
            store_id=effective_store_id
        )
    }
