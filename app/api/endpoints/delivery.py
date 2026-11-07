import sqlite3
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query
from app.db.session import get_db
from app.core.rbac import get_current_user, verify_store_access, UserPersona
from app.services.delivery_service import DeliveryService

router = APIRouter(prefix="/api/delivery", tags=["Module 2: Channel Arbitrage & Delivery"])

class DeliverySimulationRequest(BaseModel):
    markup_pct: float = 15.0
    apply_min_basket_8: bool = False
    volume_elasticity: float = -0.3
    store_id: Optional[str] = None

@router.get("/waterfall")
def get_channel_waterfall(
    store_id: Optional[str] = Query(None),
    user: UserPersona = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    FR-2.1: Channel Margin Waterfall.
    Nets out commission (27-33%), packaging (£0.45), and 4 min labor packing costs.
    """
    effective_store_id = verify_store_access(user, store_id)
    service = DeliveryService(db)
    return {"status": "success", **service.get_channel_margin_waterfall(store_id=effective_store_id)}

@router.get("/sub8-alarm")
def get_sub8_alarm(
    store_id: Optional[str] = Query(None),
    user: UserPersona = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    FR-2.2: Sub-£8 Order Alarm.
    Highlights single-drink delivery orders, margin collapse (£0.79 contribution), and peak hour jamming.
    """
    effective_store_id = verify_store_access(user, store_id)
    service = DeliveryService(db)
    return {"status": "success", **service.get_sub8_order_alarm(store_id=effective_store_id)}

@router.post("/simulate")
def simulate_delivery(
    req: DeliverySimulationRequest,
    user: UserPersona = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    FR-2.3: Delivery Markup Simulator.
    Simulates applying a 15-20% menu markup or £8 minimum basket threshold.
    """
    effective_store_id = verify_store_access(user, req.store_id)
    service = DeliveryService(db)
    return {
        "status": "success",
        **service.simulate_delivery_markup(
            markup_pct=req.markup_pct,
            apply_min_basket_8=req.apply_min_basket_8,
            volume_elasticity=req.volume_elasticity,
            store_id=effective_store_id
        )
    }
