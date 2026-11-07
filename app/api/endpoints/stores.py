import sqlite3
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from app.db.session import get_db
from app.core.rbac import get_current_user, UserPersona

router = APIRouter(prefix="/api/stores", tags=["Stores"])

@router.get("/")
def list_stores(
    user: UserPersona = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Returns list of stores.
    If user is a Store Manager, returns only their assigned store.
    """
    if not user.can_view_all_stores:
        query = "SELECT * FROM stores WHERE store_id = ?"
        rows = [dict(r) for r in db.execute(query, [user.store_id]).fetchall()]
    else:
        query = "SELECT * FROM stores ORDER BY store_id ASC"
        rows = [dict(r) for r in db.execute(query).fetchall()]
        
    return {"status": "success", "stores": rows}

@router.get("/{store_id}")
def get_store(
    store_id: str,
    user: UserPersona = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Returns specific store profile and catchment details.
    """
    if not user.can_view_all_stores and user.store_id != store_id:
        raise HTTPException(status_code=403, detail="Forbidden: You cannot access other stores.")
        
    query = """
    SELECT s.*, c.daily_footfall_street, c.office_workers_500m, c.students_1km, 
           c.median_household_income_gbp, c.competitor_cafes_500m, c.area_vibrancy_index_10
    FROM stores s
    LEFT JOIN store_catchment c ON s.store_id = c.store_id
    WHERE s.store_id = ?
    """
    row = db.execute(query, [store_id]).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Store not found")
    return {"status": "success", "store": dict(row)}
