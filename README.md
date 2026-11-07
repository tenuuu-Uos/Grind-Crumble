# Grind & Crumb Operational Intelligence Dashboard
**Software Requirements Specification (SRS-GC-2026-V1.0) Web Application**

A high-performance enterprise web application built with **Python 3.13** and **FastAPI** to eliminate operational blind spots across all 12 Grind & Crumb store locations. The tool synthesizes store-level P&Ls, daily transaction logs, footfall sensor counts, third-party delivery terms, labor rotas, waste logs, and app telemetry into a unified command center.

---

## 🎯 Strategic Objective & Core Paradox
Grind & Crumb grew revenue by +8.4% YoY, but network operating profit failed to translate proportionally. This dashboard empowers leadership to:
1. **Diagnose the Occupancy Trap:** Isolate how high-volume flagship stores like Manchester Piccadilly (S07) burn cash (-£50.3k annual loss) due to fixed occupancy costs devouring 40.2%–41.4% of sales.
2. **Stop Delivery Commission Bleed:** Tackle sub-£8 single-drink orders (29.0% of delivery volume yielding only £0.79 net contribution) while simulating a 15–20% delivery menu markup and £8 minimum basket threshold (+£54,200 annual profit recovery).
3. **Capture Peak-Hour Walkouts:** Fix 11am–2pm lunch staffing bottlenecks (e.g. 3 baristas on shift vs 5 needed at peak), unlocking £84,200 in uncaptured walkaway revenue with a 4.8x labor ROI.
4. **Eliminate Inventory Shrinkage:** Cap Hull Paragon (S10) food waste (20.7% vs 9.0% chain benchmark) via weather and day-adjusted dynamic par recommendations, and fix Spinningfields (S06) sandwich stockouts before 1:30 PM (+£28,250 annual sales).
5. **App Telemetry & Sentiment Recovery:** Monitor the App v3.0 release checkout crash incident (43% volume collapse displacing orders to commission-heavy delivery platforms) and correlate customer rating drops from the £0.40 oat milk charge.
6. **Smart Capital Expansion:** Score candidate sites (CS1–CS7) using weighted criteria (evaluating CS3 Oxford Rd as High Priority vs CS4 York Station as High Risk).

---

## 🏗️ Architecture & Technology Stack
- **Backend Framework:** FastAPI (Python 3) with asynchronous routing and Pydantic schema validation.
- **Data Pipeline & Storage:** SQLite (`grind_and_crumb.db`) with WAL mode, optimized multi-column indexes, and pre-computed views (`vw_store_monthly_pnl`, `vw_delivery_economics`).
- **ETL Auto-Sync:** Automated batch ETL ingesting 21 CSV datasets (143,000+ transaction rows) in < 1.6 seconds.
- **Frontend & UI/UX:**
  - Modern, responsive dashboard styled with Tailwind CSS and Lucide icons.
  - Interactive data visualizations with Chart.js.
  - Dual Layout Modes:
    1. **C-Suite Command Center:** Multi-column strategic review layout with interactive scenario sliders.
    2. **Counter iPad Mode (`/ipad`):** Touch-optimized view for Store Managers behind the counter with large touch targets, daily sales targets, morning par level checklists, rush roster alerts, and delivery packaging queues.
- **Role-Based Access Control (RBAC):**
  - **Executive Leadership (CEO Anna Whitfield, CFO):** Unrestricted chain-wide access across all 12 stores.
  - **Regional Operations (Ops Director):** Full capacity, bottleneck, and waste tracking.
  - **Store Managers (e.g. Ollie Brent S07, Marcus Dyer S10, Grace Okafor S03):** Enforced access restrictions—can view **only** their respective store data and operational alerts.
  - **Digital & Marketing (Head of Digital Rohan Mehta):** App telemetry, sentiment keyword parsing, and delivery mix.

---

## 📂 Repository Structure
```
Grind-Crumble/
├── app/
│   ├── __init__.py
│   ├── config.py              # Chain benchmarks, thresholds, and paths
│   ├── main.py                # FastAPI app initialization, routes, and mounting
│   ├── core/
│   │   ├── __init__.py
│   │   └── rbac.py            # Personas, RBAC dependencies, and store isolation
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py         # SQLite connection manager with WAL mode
│   │   └── etl.py             # Batch ETL pipeline & SQL view builder
│   ├── services/
│   │   ├── __init__.py
│   │   ├── pnl_service.py     # FR-1.1, FR-1.2, FR-1.3 (Heatmap, Occupancy, Cannibalization)
│   │   ├── delivery_service.py# FR-2.1, FR-2.2, FR-2.3 (Waterfall, Sub-£8 Alarm, Markup Simulator)
│   │   ├── labor_service.py   # FR-3.1, FR-3.2, FR-3.3 (Bottleneck Index, Walkouts, Wage Stress)
│   │   ├── waste_service.py   # FR-4.1, FR-4.2, FR-4.3 (Waste Variance, Dynamic Pars, Stockouts)
│   │   ├── digital_service.py # FR-5.1, FR-5.2 (App v3.0 Health, Sentiment & Surcharges)
│   │   └── expansion_service.py# FR-6.1 (Candidate Site Scorer CS1-CS7)
│   ├── api/
│   │   ├── __init__.py
│   │   └── endpoints/         # Modular REST endpoints
│   ├── static/
│   │   ├── css/custom.css     # Bespoke UI styles & animations
│   │   └── js/dashboard.js    # Interactive Chart.js and asynchronous client logic
│   └── templates/
│       ├── base.html          # Global header, persona selector, navigation
│       ├── dashboard.html     # C-Suite Command Center (Modules 1-6)
│       └── ipad_store.html    # Behind-the-counter iPad Mode for Store Managers
├── data/                      # Raw client data pack (21 CSV files)
├── tests/
│   └── test_services.py       # Comprehensive unit test suite (16 tests)
├── grind_and_crumb.db         # SQLite database with indexed tables and views
├── requirements.txt           # Python dependencies
├── run.py                     # Application startup script
└── README.md
```

---

## 🚀 Getting Started

### 1. Prerequisites & Virtual Environment
Ensure Python 3.10+ (or Python 3.13) is installed:
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Initialize Database & Run ETL Pipeline
The ETL pipeline ingests all CSV files from `data/`, creates high-speed indexes, and builds the required database views:
```bash
python -m app.db.etl
```

### 3. Launch the Web Application
```bash
python run.py
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser:
- **C-Suite Command Center:** `http://127.0.0.1:8000/`
- **Store Manager iPad Mode:** `http://127.0.0.1:8000/ipad`
- **Interactive OpenAPI Docs:** `http://127.0.0.1:8000/docs`

### 4. Run Automated Tests
```bash
python -m unittest -v tests/test_services.py
```
*(All 16 tests pass in ~1.1 seconds).*

---

## 🔍 Key Functional Modules (SRS Alignment)

### Module 1: Store Network Profitability & Occupancy Engine
- **FR-1.1 True Profit Heatmap:** Ranks stores by operating margin (%) and net profit (£) rather than gross volume, spotlighting high-volume loss-makers (S07 Manchester Piccadilly).
- **FR-1.2 Fixed Occupancy Calculator:** Enforces the 25% rent + business rates ceiling, flagging S07 (40.2%–41.4% fixed occupancy cost).
- **FR-1.3 Cannibalization Audit Tool:** Compares Leeds Briggate (S03) performance pre- and post-opening of Leeds Trinity (S12, opened 15 Sept 2025). Quantifies -£18,453/mo dilution vs +£28,500/mo net Leeds territory expansion.

### Module 2: Channel Arbitrage & Delivery Economics
- **FR-2.1 Channel Margin Waterfall:** Deconstructs ticket margins across In-Store, Direct App, Dashly, and RushEats, accounting for commissions (up to 33%), £0.45 packaging, and 4 min labor packing (~£0.93/order).
- **FR-2.2 Sub-£8 Order Alarm:** Flags that 29.0% of delivery orders are single drinks under £8 yielding £0.79 net contribution while congesting peak lunch counters.
- **FR-2.3 Delivery Markup Simulator:** Interactive scenario slider modeling a 15%–20% menu price markup and £8 minimum basket threshold, recovering £54,200 in annual profit.

### Module 3: Peak-Hour Labor & Throughput
- **FR-3.1 11am–2pm Bottleneck Index:** Overlays door footfall (351 avg at S07) against barista throughput (3 staff on shift vs 5 needed at peak).
- **FR-3.2 Walkout Revenue Loss Estimator:** Calculates £84,200 in uncaptured walkaway revenue when queues exceed 5 deep.
- **FR-3.3 Labor Inflation Stress Tester:** Models mandatory 6.7% National Living Wage increases against sales per labor hour (SPLH) to determine breakeven menu price adjustments (~2.1%).

### Module 4: Inventory Shrinkage & Par Levels
- **FR-4.1 Waste Rate Variance Tracker:** Monitors itemized food prep waste against the 9.0% chain benchmark, flagging Hull Paragon (S10) at 20.7%.
- **FR-4.2 Dynamic Par Recommendation:** Dynamic daily prep par levels adjusted for weather forecasts (Rainy/Sunny) and day-of-week demand.
- **FR-4.3 Early Stockout Monitor:** Detects Manchester Spinningfields (S06) sandwich stockouts before 1:30 PM (often 13:18 PM), capturing ~£28,250 in missed afternoon trade.

### Module 5: Digital App & Customer Sentiment
- **FR-5.1 App Version Health Monitor:** Analyzes the 2 March 2026 App v3.0 release incident (43% drop in app checkouts displacing volume to third-party delivery) and the 13 April 2026 v3.1 recovery.
- **FR-5.2 Sentiment & Surcharge Tracker:** NLP key phrase parsing across 3,030 reviews correlating the -2.06 star drop on milk-related reviews following the £0.40 oat milk charge.

### Module 6: Capital Expansion & Candidate Sites
- **FR-6.1 Candidate Site Scorer:** Weighted multi-criteria evaluation of CS1–CS7 across Footfall, Demographics, Rent Efficiency, CapEx, and Cannibalization Risk. Rates **CS3 Manchester Oxford Road** as *High - Priority Go* and **CS4 York Railway Station** as *High Risk - Reject* (preventing another S07 lease trap).
