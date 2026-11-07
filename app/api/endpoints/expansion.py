import sqlite3
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from app.db.session import get_db
from app.core.rbac import get_current_user, UserPersona
from app.services.expansion_service import ExpansionService

router = APIRouter(prefix="/api/expansion", tags=["Module 6: Capital Expansion & Site Evaluator"])

class SiteScoringWeights(BaseModel):
    weight_footfall: float = 0.25
    weight_demographics: float = 0.25
    weight_rent_efficiency: float = 0.20
    weight_fitout_capex: float = 0.15
    weight_cannibalization_risk: float = 0.15

@router.get("/candidate-sites")
def get_candidate_sites(
    user: UserPersona = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    FR-6.1: Candidate Site Scorer.
    Evaluates candidate sites (CS1-CS7) using baseline weights.
    Highlights CS3 Oxford Rd as High Priority vs CS4 York Station as High Risk.
    """
    service = ExpansionService(db)
    return {"status": "success", **service.evaluate_candidate_sites()}

@router.post("/score")
def score_candidate_sites(
    weights: SiteScoringWeights,
    user: UserPersona = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    FR-6.1: Candidate Site Custom Scorer.
    Allows leadership to dynamically adjust weighting factors.
    """
    service = ExpansionService(db)
    return {
        "status": "success",
        **service.evaluate_candidate_sites(
            weight_footfall=weights.weight_footfall,
            weight_demographics=weights.weight_demographics,
            weight_rent_efficiency=weights.weight_rent_efficiency,
            weight_fitout_capex=weights.weight_fitout_capex,
            weight_cannibalization_risk=weights.weight_cannibalization_risk
        )
    }
