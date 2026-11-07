import sqlite3
from fastapi import APIRouter, Depends
from app.db.session import get_db
from app.db.etl import run_etl
from app.core.rbac import get_current_user, UserPersona

router = APIRouter(prefix="/api/etl", tags=["Data Pipeline & ETL"])

@router.post("/sync")
def trigger_etl_sync(user: UserPersona = Depends(get_current_user)):
    """
    Triggers batch ETL auto-sync, reloading raw CSVs, updating views, and rebuilding indexes.
    """
    res = run_etl()
    return {
        "status": "success",
        "message": "ETL batch sync completed successfully",
        "details": res
    }

@router.get("/status")
def get_etl_status(db: sqlite3.Connection = Depends(get_db)):
    """
    Reports status and record counts of underlying SQLite tables and views.
    """
    tables = [
        "stores", "products", "transactions", "transaction_lines", 
        "daily_store_sales", "footfall", "waste_log", "staff_rota_weekly",
        "customer_reviews", "customer_survey", "candidate_sites"
    ]
    views = ["vw_store_monthly_pnl", "vw_delivery_economics"]
    
    stats = {}
    for tbl in tables:
        try:
            cnt = db.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            stats[tbl] = cnt
        except Exception as e:
            stats[tbl] = f"Error: {e}"
            
    view_stats = {}
    for vw in views:
        try:
            cnt = db.execute(f"SELECT COUNT(*) FROM {vw}").fetchone()[0]
            view_stats[vw] = cnt
        except Exception as e:
            view_stats[vw] = f"Error: {e}"

    return {
        "status": "online",
        "database": "grind_and_crumb.db",
        "table_row_counts": stats,
        "view_row_counts": view_stats
    }
