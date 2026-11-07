import os
from pathlib import Path
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import APP_TITLE, APP_VERSION, BASE_DIR
from app.core.rbac import get_current_user, UserPersona, PERSONAS
from app.api.endpoints import (
    pnl, delivery, labor, waste, digital, expansion, stores, auth, etl
)

app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description="Enterprise Operational Intelligence Dashboard for Grind & Crumb Ltd."
)

# Static and Templates
STATIC_DIR = BASE_DIR / "app" / "static"
TEMPLATES_DIR = BASE_DIR / "app" / "templates"

STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Include API Routers
app.include_router(pnl.router)
app.include_router(delivery.router)
app.include_router(labor.router)
app.include_router(waste.router)
app.include_router(digital.router)
app.include_router(expansion.router)
app.include_router(stores.router)
app.include_router(auth.router)
app.include_router(etl.router)

@app.get("/health")
def health_check():
    return {"status": "ok", "app": APP_TITLE, "version": APP_VERSION}

@app.get("/", response_class=HTMLResponse)
def get_dashboard(request: Request, user: UserPersona = Depends(get_current_user)):
    """
    Renders main C-Suite & Executive Command Center Dashboard.
    Responsive desktop and tablet layout with interactive FR modules 1-6.
    """
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "personas": list(PERSONAS.values()),
            "title": APP_TITLE
        }
    )

@app.get("/ipad", response_class=HTMLResponse)
def get_ipad_counter_view(request: Request, user: UserPersona = Depends(get_current_user)):
    """
    Renders touch-optimized Counter iPad View for Store Managers.
    Designed for behind-the-counter iPad screens with large action targets.
    """
    return templates.TemplateResponse(
        "ipad_store.html",
        {
            "request": request,
            "user": user,
            "personas": list(PERSONAS.values()),
            "title": f"Store Manager Counter iPad - {user.store_name or 'Store View'}"
        }
    )
