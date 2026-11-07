import os
from pathlib import Path
from fastapi import FastAPI, Request, Response, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import BASE_DIR, get_settings, update_settings
from app.data_manager import DataManager

app = FastAPI(
    title="Grind & Crumb Store Health Monitor",
    description="Minimalist store-first operations dashboard for Grind & Crumb"
)

STATIC_DIR = BASE_DIR / "app" / "static"
TEMPLATES_DIR = BASE_DIR / "app" / "templates"

STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Filter for integer formatting with commas: e.g. 10000 -> 10,000
def format_number(val):
    try:
        return f"{int(round(float(val))):,}"
    except (ValueError, TypeError):
        return str(val)

templates.env.filters["num"] = format_number

@app.get("/health")
def health_check():
    return {"status": "ok", "app": "Grind & Crumb Store Health Monitor"}

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

@app.get("/", response_class=HTMLResponse)
def home_page(request: Request):
    """12-Store Minimalist Grid Home Screen."""
    settings = get_settings()
    cards = DataManager.get_all_store_cards()

    red_count = sum(1 for c in cards if c["rag_status"] == "red")
    amber_count = sum(1 for c in cards if c["rag_status"] == "amber")
    green_count = sum(1 for c in cards if c["rag_status"] == "green")

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "stores": cards,
            "settings": settings,
            "red_count": red_count,
            "amber_count": amber_count,
            "green_count": green_count,
            "active_page": "home",
            "title": "Grind & Crumb - Store Health Monitor"
        }
    )

@app.get("/store/{store_id}", response_class=HTMLResponse)
def store_detail_page(request: Request, store_id: str):
    """Single-Store Deep Dive: P&L waterfall, waste trend, channel mix, staffing heatmap."""
    store_id = store_id.strip().upper()
    detail = DataManager.get_single_store_detail(store_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Store '{store_id}' not found")

    return templates.TemplateResponse(
        request=request,
        name="store_detail.html",
        context={
            **detail,
            "active_page": "store",
            "title": f"{detail['card']['store_name']} - Store Detail"
        }
    )

@app.get("/network", response_class=HTMLResponse)
def network_page(request: Request):
    """Secondary 12-store comparative ranking table with sortable columns."""
    settings = get_settings()
    cards = DataManager.get_all_store_cards()
    sorted_cards = sorted(cards, key=lambda x: x["margin_this_month"], reverse=True)

    return templates.TemplateResponse(
        request=request,
        name="network.html",
        context={
            "stores": sorted_cards,
            "settings": settings,
            "active_page": "network",
            "title": "Network Scoreboard - Grind & Crumb"
        }
    )

@app.get("/stores/new", response_class=HTMLResponse)
def new_store_page(request: Request, msg: str = None, error: str = None):
    """Form to register a new store location in the chain."""
    settings = get_settings()
    existing_cards = DataManager.get_all_store_cards()
    # Suggest next store id (e.g. S13 or S14)
    existing_nums = [
        int(c["store_id"][1:]) for c in existing_cards if c["store_id"].startswith("S") and c["store_id"][1:].isdigit()
    ]
    next_id = f"S{max(existing_nums, default=12) + 1:02d}"

    return templates.TemplateResponse(
        request=request,
        name="new_store.html",
        context={
            "settings": settings,
            "next_id": next_id,
            "message": msg,
            "error": error,
            "active_page": "new_store",
            "title": "Add New Store - Grind & Crumb"
        }
    )

@app.post("/stores/new")
def create_new_store(
    store_id: str = Form(...),
    store_name: str = Form(...),
    city: str = Form(...),
    format: str = Form("Standard"),
    location_type: str = Form("High street"),
    monthly_rent_gbp: float = Form(7500.0),
    manager: str = Form("Store Manager"),
    target_sales_gbp: float = Form(60000.0)
):
    """Handles adding a new store to stores.csv and seeding baseline P&L data."""
    try:
        new_store = DataManager.add_new_store({
            "store_id": store_id.strip().upper(),
            "store_name": store_name.strip(),
            "city": city.strip(),
            "format": format.strip(),
            "location_type": location_type.strip(),
            "monthly_rent_gbp": monthly_rent_gbp,
            "manager": manager.strip(),
            "target_sales_gbp": target_sales_gbp
        })
        return RedirectResponse(
            url=f"/?added={new_store['store_id']}",
            status_code=303
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/stores/new?error={str(e)}",
            status_code=303
        )

@app.get("/api/explain-store/{store_id}")
def api_explain_store(store_id: str):
    """Feature 1: Returns plain-English diagnosis and recommended actions for a store."""
    explanation = DataManager.explain_store(store_id)
    return explanation

@app.post("/api/ask")
async def api_ask_question(request: Request):
    """Answers any operational store question using Google Gemini AI with deep contextual data."""
    try:
        body = await request.json()
        question = body.get("question", "")
    except Exception:
        question = ""
    result = DataManager.ask_data_question(question)
    return result

@app.get("/instructions", response_class=HTMLResponse)
def instructions_page(request: Request):
    """Staff and store managers user manual with metric definitions and daily routines."""
    settings = get_settings()
    return templates.TemplateResponse(
        request=request,
        name="instructions.html",
        context={
            "settings": settings,
            "active_page": "instructions",
            "title": "Staff & Ops Instructions - Grind & Crumb"
        }
    )

@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, saved: bool = False):
    """Editable alert thresholds & Gemini API key configuration."""
    settings = get_settings()
    msg = "Settings saved successfully!" if saved else None

    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "settings": settings,
            "message": msg,
            "active_page": "settings",
            "title": "Settings - Store Health Monitor"
        }
    )

@app.post("/settings")
def update_settings_form(
    waste_benchmark_pct: float = Form(9.0),
    margin_floor_pct: float = Form(10.0),
    occupancy_ceiling_pct: float = Form(25.0),
    gemini_api_key: str = Form("")
):
    """Saves thresholds & Gemini API key to settings.json."""
    update_settings({
        "waste_benchmark_pct": waste_benchmark_pct,
        "margin_floor_pct": margin_floor_pct,
        "occupancy_ceiling_pct": occupancy_ceiling_pct,
        "gemini_api_key": gemini_api_key.strip()
    })
    DataManager.invalidate_cache()
    return RedirectResponse(url="/settings?saved=true", status_code=303)

@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request, msg: str = None):
    """Ops CSV upload page with Gemini API analysis integration."""
    settings = get_settings()
    return templates.TemplateResponse(
        request=request,
        name="upload.html",
        context={
            "settings": settings,
            "message": msg,
            "active_page": "upload",
            "title": "Upload & AI Analysis - Store Health Monitor"
        }
    )

@app.post("/upload")
async def handle_csv_upload(
    dataset_type: str = Form(...),
    csv_file: UploadFile = File(...),
    gemini_key: str = Form("")
):
    """Cleanses uploaded CSV and invokes Gemini API to update store insights."""
    try:
        content = await csv_file.read()
        res = DataManager.process_upload_with_gemini(
            file_content=content,
            filename=dataset_type,
            api_key=gemini_key.strip()
        )
        gemini_info = res["gemini"]
        msg = f"Cleansed {res['cleaned_rows']} rows for {res['filename']} ({res['duplicates_removed']} duplicates removed). {gemini_info['message']}"
    except Exception as e:
        msg = f"Error processing {dataset_type}: {str(e)}"

    return RedirectResponse(url=f"/upload?msg={msg}", status_code=303)
