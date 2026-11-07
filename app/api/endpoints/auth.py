from fastapi import APIRouter, Response, Depends, Request
from pydantic import BaseModel
from app.core.rbac import PERSONAS, get_current_user, UserPersona

router = APIRouter(prefix="/api/auth", tags=["Authentication & RBAC"])

class SwitchUserRequest(BaseModel):
    user_id: str

@router.get("/personas")
def get_all_personas():
    """Returns all available user personas for testing & role demonstration."""
    return {
        "status": "success",
        "personas": [persona.dict() for persona in PERSONAS.values()]
    }

@router.get("/current")
def get_active_user(user: UserPersona = Depends(get_current_user)):
    """Returns currently authenticated persona and permissions."""
    return {
        "status": "success",
        "user": user.dict()
    }

@router.post("/switch")
def switch_active_persona(req: SwitchUserRequest, response: Response):
    """
    Sets session cookie to switch personas seamlessly in the web browser.
    """
    if req.user_id not in PERSONAS:
        return {"status": "error", "message": f"Unknown user_id '{req.user_id}'"}
    
    response.set_cookie(
        key="gc_user_id",
        value=req.user_id,
        httponly=False,
        samesite="lax",
        max_age=86400
    )
    return {
        "status": "success",
        "switched_to": PERSONAS[req.user_id].dict()
    }
