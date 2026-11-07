# Grind & Crumb Store Health Monitor

A minimalist, store-first operational intelligence dashboard for Grind & Crumb café chain, with automated CSV data cleansing and Google Gemini API integration.

---

## 1. Quick Start

### Prerequisites & Installation

Create and activate a virtual environment, then install the required packages:

```bash
# 1. Create a virtual environment
python -m venv .venv

# 2. Activate the virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (cmd.exe):
.venv\Scripts\activate.bat
# macOS / Linux:
source .venv/bin/activate

# 3. Install requirements
pip install -r requirements.txt
```

### Requirements (`requirements.txt`)
```text
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
jinja2>=3.1.4
python-multipart>=0.0.9
httpx>=0.27.0
pandas>=2.2.0
python-dotenv>=1.0.1
```

### Run the App
```bash
python run.py
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser.

---

## 2. Project File Structure

```text
Grind-Crumble/
├── app/
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css            # Custom typography & tooltip styles
│   │   └── sample/
│   │       └── test_monthly_pnl_july2026.csv   # Sample upload data for testing
│   ├── templates/
│   │   ├── base.html                # Main layout, nav bar, and footer
│   │   ├── home.html                # Store grid cards with quick sort/filter
│   │   ├── store_detail.html        # P&L waterfall, waste trend, channel mix
│   │   ├── network.html             # Sortable comparative network scoreboard
│   │   ├── new_store.html           # Add new store location form
│   │   ├── instructions.html        # Staff & store operations guide
│   │   ├── upload.html              # CSV upload with Gemini AI cleansing
│   │   └── settings.html            # Alert thresholds & API key settings
│   ├── config.py                    # App configuration & settings loader
│   ├── data_manager.py              # Data cleansing, CSV parsers & Gemini client
│   └── main.py                      # FastAPI application routes
├── data/
│   ├── stores.csv                   # Store registry (ID, location, format, rent)
│   ├── starter_store_monthly_pnl.csv# Monthly store P&L records
│   ├── test_monthly_pnl_july2026.csv# Sample test batch with S13 Liverpool
│   └── ai_store_insights.json       # Persisted AI-generated action alerts
├── tests/
│   └── test_store_monitor.py        # 12 automated unit & route tests
├── .gitignore                       # Clean Git exclusion rules
├── Home.py                          # Startup entrypoint (python Home.py)
├── run.py                           # Alternative startup entrypoint
├── requirements.txt                 # Pip dependencies
├── settings.json                    # Persisted operational thresholds
└── README.md                        # Documentation & Ops Handover Guide
```

---

## 3. Minimalist Store-First Design

1. **Home Screen (`/`)**:
   - 12 Store Cards Grid.
   - Shows for each store:
     - Margin this month vs. last month
     - Waste % vs. chain benchmark (target &le; 9%)
     - Delivery share of sales
     - Peak lunch rush staffing gap
     - Action / Watch / Optimal RAG status badge
     - Plain-language operational alert (e.g. *"Hull Paragon waste is 2.4× the chain benchmark"* or *"Fixed rent devours 37.3% of sales (£30,500/mo)"*)
2. **Store Detail View (`/store/{store_id}`)**:
   - P&L Waterfall (Sales, Food cost, Waste, Labour, Delivery commissions, Rent, Net profit)
   - 12-Month Waste Trend line chart vs. benchmark
   - Sales Channel Mix donut chart
   - 11:00–14:00 Lunchtime Staffing & Queue Heatmap
3. **Upload & Gemini AI Integration (`/upload`)**:
   - Drop in any updated monthly CSV export.
   - Automatic cleansing pipeline: deduplicates rows, standardizes dates (`YYYY-MM-DD`), and validates store IDs.
   - Connects to **Gemini API** (`gemini-1.5-flash`) to analyze store anomalies and generate actionable, plain-language alerts.
   - If no Gemini API key is supplied, intelligent local operational rules are applied automatically.
4. **Settings (`/settings`)**:
   - Easily edit operational alert thresholds (Waste limit, Margin floor, Occupancy ceiling).
   - Enter your `gemini_api_key`.
   - Settings persist in `settings.json` without modifying any code.
5. **Network Scoreboard (`/network`)**:
   - Comparative ranking table with interactive column sorting across all locations.
6. **Ask Gemini AI Operational Q&A (`/`)**:
   - Natural language AI assistant powered by Google Gemini (with comprehensive chain datasets and operational records) to answer any question given by managers (delivery loss breakdown, waste analysis, cannibalisation, app shock, or staffing).
7. **“Explain This Store” Operational Diagnosis (`/store/{store_id}`)**:
   - One-click diagnosis button on each store's page that explains margin shifts, waste multiples, and delivery impacts in plain English with likely root causes and recommended manager actions.
8. **Staff & Operations Guide (`/instructions`)**:
   - Staff user manual with daily 3-step routines, RAG badge definitions, metric calculation guides, and upload tutorials.

---

## 3. Data Dictionary

| Metric | Definition | Benchmark / Rule |
| :--- | :--- | :--- |
| **Store Margin** | Operating profit divided by total net revenue. | Floor &ge; 10.0% |
| **Waste Rate** | Cost of discarded food prep divided by food revenue. | Limit &le; 9.0% (Hull is 21.5%) |
| **Delivery Share** | Percentage of monthly revenue from delivery apps. | Typically 12%–15% |
| **Fixed Occupancy** | Monthly (Rent + Business Rates) divided by sales. | Ceiling &le; 25.0% (Piccadilly is 37.3%) |
| **Peak Staff Gap** | Baristas on counter minus baristas needed at 11am–2pm rush. | Balanced (0 gap) |

---

## 4. How to Refresh Data

1. Open **[http://127.0.0.1:8000/upload](http://127.0.0.1:8000/upload)**.
2. Select your CSV type (e.g. *Monthly Store P&L*).
3. Select the file and click **Cleanse & Analyze with Gemini**.
4. The dashboard automatically cleanses the data, updates the store metrics, and applies AI-generated insights.
