from typing import Optional, List, Dict
from pydantic import BaseModel
from fastapi import Request, HTTPException, Depends

class UserPersona(BaseModel):
    user_id: str
    name: str
    title: str
    role: str  # "executive", "regional_ops", "store_manager", "digital_marketing"
    store_id: Optional[str] = None
    store_name: Optional[str] = None
    allowed_stores: List[str] = []
    can_view_all_stores: bool = True
    description: str

# Defined personas according to Section 2 of SRS
PERSONAS: Dict[str, UserPersona] = {
    "ceo_anna": UserPersona(
        user_id="ceo_anna",
        name="Anna Whitfield",
        title="Chief Executive Officer",
        role="executive",
        store_id=None,
        allowed_stores=["*"],
        can_view_all_stores=True,
        description="Full chain-wide visibility, network margins, store rankings, M&A expansion models."
    ),
    "cfo_lead": UserPersona(
        user_id="cfo_lead",
        name="Marcus Vance",
        title="Chief Financial Officer",
        role="executive",
        store_id=None,
        allowed_stores=["*"],
        can_view_all_stores=True,
        description="P&L audit, occupancy costs, channel margin waterfall, inflation modeling."
    ),
    "ops_director": UserPersona(
        user_id="ops_director",
        name="Elena Rostova",
        title="Operations Director",
        role="regional_ops",
        store_id=None,
        allowed_stores=["*"],
        can_view_all_stores=True,
        description="Peak-hour labor capacity, 11am-2pm bottlenecks, waste variance, rota compliance."
    ),
    "mgr_s07": UserPersona(
        user_id="mgr_s07",
        name="Ollie Brent",
        title="Store Manager - Manchester Piccadilly (S07)",
        role="store_manager",
        store_id="S07",
        store_name="Manchester Piccadilly",
        allowed_stores=["S07"],
        can_view_all_stores=False,
        description="Restricted to Manchester Piccadilly (S07): daily targets, peak rush roster, packaging alerts."
    ),
    "mgr_s10": UserPersona(
        user_id="mgr_s10",
        name="Marcus Dyer",
        title="Store Manager - Hull Paragon (S10)",
        role="store_manager",
        store_id="S10",
        store_name="Hull Paragon",
        allowed_stores=["S10"],
        can_view_all_stores=False,
        description="Restricted to Hull Paragon (S10): food waste tracking, daily par level prep suggestions."
    ),
    "mgr_s06": UserPersona(
        user_id="mgr_s06",
        name="Sam Kowalski",
        title="Store Manager - Manchester Spinningfields (S06)",
        role="store_manager",
        store_id="S06",
        store_name="Manchester Spinningfields",
        allowed_stores=["S06"],
        can_view_all_stores=False,
        description="Restricted to Manchester Spinningfields (S06): lunch stockout alerts, queue walkouts."
    ),
    "mgr_s03": UserPersona(
        user_id="mgr_s03",
        name="Grace Okafor",
        title="Store Manager - Leeds Briggate (S03)",
        role="store_manager",
        store_id="S03",
        store_name="Leeds Briggate",
        allowed_stores=["S03"],
        can_view_all_stores=False,
        description="Restricted to Leeds Briggate (S03): cannibalization impact, daily par recommendations."
    ),
    "head_digital": UserPersona(
        user_id="head_digital",
        name="Rohan Mehta",
        title="Head of Digital & Marketing",
        role="digital_marketing",
        store_id=None,
        allowed_stores=["*"],
        can_view_all_stores=True,
        description="App conversion vs crash rate, delivery partner mix, sentiment and surcharge analysis."
    ),
}

def get_current_user(request: Request) -> UserPersona:
    """
    Extracts active user persona from:
    1. Query param: ?user_id=...
    2. Header: X-User-ID: ...
    3. Cookie: gc_user_id=...
    Defaults to CEO Anna Whitfield (Executive).
    """
    user_id = request.query_params.get("user_id") or request.headers.get("X-User-ID") or request.cookies.get("gc_user_id")
    if user_id and user_id in PERSONAS:
        return PERSONAS[user_id]
    return PERSONAS["ceo_anna"]

def verify_store_access(user: UserPersona, target_store_id: Optional[str]) -> Optional[str]:
    """
    RBAC enforcement:
    If user is a store manager, enforces they can only access their assigned store.
    If target_store_id is specified and user is restricted to a different store, raises 403.
    Returns the effective store_id.
    """
    if user.can_view_all_stores:
        return target_store_id
    
    # User is restricted (Store Manager)
    if target_store_id and target_store_id != user.store_id:
        raise HTTPException(
            status_code=403, 
            detail=f"Access Denied: As {user.title}, you are restricted to store {user.store_id}."
        )
    return user.store_id
