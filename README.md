# Grind & Crumb Store Health Monitor

A minimalist, store-first operational intelligence dashboard for Grind & Crumb café chain, with automated CSV data cleansing and Google Gemini API integration.

---

## 1. Quick Start

### Run the App
```bash
# Windows
.venv\Scripts\Activate.ps1
python run.py

# Mac / Linux
source .venv/bin/activate
python run.py
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)**.

---

## 2. Minimalist Store-First Design

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
5. **Network Overview (`/network`)**:
   - Minimalist comparative ranking table of all 12 locations.

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
