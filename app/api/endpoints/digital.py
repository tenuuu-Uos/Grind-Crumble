import sqlite3
from fastapi import APIRouter, Depends
from app.db.session import get_db
from app.core.rbac import get_current_user, UserPersona
from app.services.digital_service import DigitalService

router = APIRouter(prefix="/api/digital", tags=["Module 5: Digital App & Customer Sentiment"])

@router.get("/health")
def get_app_health(
    user: UserPersona = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    FR-5.1: App Version Health Monitor.
    Tracks v3.0 release crash spike on 2 March 2026, order displacement, and v3.1 hotfix recovery.
    """
    service = DigitalService(db)
    return {"status": "success", **service.get_app_version_health()}

@router.get("/sentiment")
def get_sentiment(
    user: UserPersona = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    FR-5.2: Sentiment & Surcharge Tracker.
    Parses reviews for 'oat milk charge', 'long queue', 'broken app' and correlates rating drops.
    """
    service = DigitalService(db)
    return {"status": "success", **service.get_sentiment_and_surcharge_tracker()}
