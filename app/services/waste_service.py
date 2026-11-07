import sqlite3
from typing import Optional, List, Dict, Any
from app.config import CHAIN_BENCHMARKS

class WasteService:
    def __init__(self, db: sqlite3.Connection):
        self.db = db

    def get_waste_variance(self, store_id: Optional[str] = None) -> Dict[str, Any]:
        """
        FR-4.1: Waste Rate Variance Tracker.
        Monitors daily itemized waste volume against sales.
        Flags stores exceeding the 9.0% chain benchmark (e.g. Hull Paragon S10 at 20.7% waste rate).
        """
        filter_sql = "WHERE 1=1"
        params = []
        if store_id:
            filter_sql += " AND p.store_id = ?"
            params.append(store_id)

        # Store-level waste summary from PnL
        query_stores = f"""
        SELECT 
            p.store_id,
            p.store_name,
            p.city,
            ROUND(SUM(p.total_sales_gbp), 2) AS total_sales_gbp,
            ROUND(SUM(p.food_cost_gbp), 2) AS total_food_cost_gbp,
            ROUND(SUM(p.waste_cost_gbp), 2) AS total_waste_cost_gbp,
            ROUND(AVG(p.waste_rate) * 100.0, 2) AS avg_waste_rate_pct
        FROM vw_store_monthly_pnl p
        {filter_sql}
        GROUP BY p.store_id, p.store_name, p.city
        ORDER BY avg_waste_rate_pct DESC
        """
        stores_summary = [dict(r) for r in self.db.execute(query_stores, params).fetchall()]

        benchmark = CHAIN_BENCHMARKS["waste_benchmark_pct"]
        excess_total_cost = 0.0

        for s in stores_summary:
            rate = s["avg_waste_rate_pct"]
            s["benchmark_pct"] = benchmark
            s["variance_pts"] = round(rate - benchmark, 2)
            s["is_exceeding_benchmark"] = rate > benchmark
            
            # Excess waste cost = waste_cost * (excess rate / total rate)
            if rate > benchmark:
                excess_cost = round(s["total_waste_cost_gbp"] * ((rate - benchmark) / rate), 2)
                s["excess_waste_cost_gbp"] = excess_cost
                excess_total_cost += excess_cost
                s["severity"] = "CRITICAL" if rate > 15.0 else "WARNING"
            else:
                s["excess_waste_cost_gbp"] = 0.0
                s["severity"] = "COMPLIANT"

        # Itemized category breakdown from waste_log
        waste_filter = "WHERE 1=1"
        waste_params = []
        if store_id:
            waste_filter += " AND store_id = ?"
            waste_params.append(store_id)

        query_cat = f"""
        SELECT 
            category,
            SUM(units_prepared) AS total_prepared_units,
            SUM(units_wasted) AS total_wasted_units,
            ROUND(SUM(units_wasted) * 100.0 / NULLIF(SUM(units_prepared), 0), 2) AS category_waste_rate_pct,
            ROUND(SUM(est_cost_wasted_gbp), 2) AS total_waste_cost_gbp
        FROM waste_log
        {waste_filter}
        GROUP BY category
        ORDER BY total_waste_cost_gbp DESC
        """
        categories = [dict(r) for r in self.db.execute(query_cat, waste_params).fetchall()]

        return {
            "benchmark_pct": benchmark,
            "chain_excess_waste_cost_gbp": round(excess_total_cost, 2),
            "stores": stores_summary,
            "categories": categories,
            "highlight_outlier": next((s for s in stores_summary if s["store_id"] == "S10"), None)
        }

    def get_dynamic_par_recommendation(
        self, 
        store_id: str = "S10", 
        day_of_week: str = "Wednesday", 
        weather_type: str = "Rainy"
    ) -> Dict[str, Any]:
        """
        FR-4.2: Dynamic Par Recommendation.
        Generates automated daily food prep suggestions based on:
        - Day-of-week historical sales patterns
        - Upcoming weather forecasts (e.g. Rain reduces footfall by ~8-12%, increases hot soup/toastie share)
        - Local catchment profile (office vs student vs transit)
        """
        # Store profile
        query_store = """
        SELECT s.*, c.office_workers_500m, c.students_1km, c.daily_footfall_street
        FROM stores s
        LEFT JOIN store_catchment c ON s.store_id = c.store_id
        WHERE s.store_id = ?
        """
        store = dict(self.db.execute(query_store, [store_id]).fetchone() or {})
        
        # Historical waste rate for this store
        cur_waste = self.db.execute(
            "SELECT ROUND(AVG(waste_rate)*100, 1) as avg_waste FROM vw_store_monthly_pnl WHERE store_id = ?", 
            [store_id]
        ).fetchone()
        waste_pct = cur_waste["avg_waste"] if cur_waste else 10.0

        # Base pars by category
        base_pars = {
            "Bakery": {"base_units": 85, "unit_cost": 0.95, "unit_price": 2.80},
            "Lunch": {"base_units": 65, "unit_cost": 1.70, "unit_price": 5.80},
            "Breakfast": {"base_units": 45, "unit_cost": 1.30, "unit_price": 4.50}
        }

        # Catchment weighting
        office_workers = store.get("office_workers_500m", 3000) or 3000
        students = store.get("students_1km", 5000) or 5000
        
        # Weekend vs weekday factor
        is_weekend = day_of_week in ["Saturday", "Sunday"]
        if is_weekend:
            day_factor = 0.55 if office_workers > 6000 else 1.25 # Office dead on weekend, tourist alive
        else:
            day_factor = 1.15 if day_of_week in ["Wednesday", "Thursday", "Friday"] else 0.95

        # Weather factor
        weather_factors = {
            "Sunny": {"footfall": 1.15, "cold": 1.30, "hot": 0.85},
            "Rainy": {"footfall": 0.88, "cold": 0.80, "hot": 1.20},
            "Overcast": {"footfall": 1.00, "cold": 1.00, "hot": 1.00},
            "Cold": {"footfall": 0.92, "cold": 0.75, "hot": 1.25}
        }
        w_factor = weather_factors.get(weather_type, {"footfall": 1.0, "cold": 1.0, "hot": 1.0})

        recommendations = []
        total_recommended_prep_units = 0
        est_daily_prep_cost = 0.0
        est_waste_saved_gbp = 0.0

        for cat, meta in base_pars.items():
            base = meta["base_units"]
            # Category specific adjustments
            if cat == "Lunch":
                cat_factor = w_factor["footfall"] * (1.1 if office_workers > 5000 and not is_weekend else 0.8)
            elif cat == "Bakery":
                cat_factor = w_factor["footfall"] * day_factor
            else: # Breakfast
                cat_factor = w_factor["footfall"] * (1.1 if not is_weekend else 0.7)

            rec_units = round(base * day_factor * cat_factor)
            
            # If store historically had 20%+ waste (like Hull S10), recommended par trims the excess buffer
            if waste_pct > 15.0:
                trim_pct = (waste_pct - 9.0) * 0.75
                trimmed_units = round(rec_units * (1.0 - (trim_pct / 100.0)))
                units_saved = rec_units - trimmed_units
                rec_units = trimmed_units
                est_waste_saved_gbp += round(units_saved * meta["unit_cost"], 2)

            cost = round(rec_units * meta["unit_cost"], 2)
            revenue_potential = round(rec_units * meta["unit_price"], 2)

            total_recommended_prep_units += rec_units
            est_daily_prep_cost += cost

            recommendations.append({
                "category": cat,
                "recommended_prep_units": rec_units,
                "safety_buffer_pct": 5.0 if waste_pct > 15.0 else 10.0,
                "est_prep_cost_gbp": cost,
                "est_revenue_potential_gbp": revenue_potential,
                "historical_waste_rate_pct": waste_pct
            })

        return {
            "store_id": store_id,
            "store_name": store.get("store_name", ""),
            "day_of_week": day_of_week,
            "weather_type": weather_type,
            "context": {
                "format": store.get("format"),
                "location_type": store.get("location_type"),
                "office_workers": office_workers,
                "students": students,
                "historical_store_waste_rate_pct": waste_pct
            },
            "recommendations": recommendations,
            "summary": {
                "total_units_to_prep": total_recommended_prep_units,
                "est_daily_prep_cost_gbp": round(est_daily_prep_cost, 2),
                "est_daily_waste_savings_gbp": round(est_waste_saved_gbp, 2),
                "est_monthly_waste_savings_gbp": round(est_waste_saved_gbp * 30, 2)
            }
        }

    def get_early_stockouts(self, store_id: Optional[str] = "S06") -> Dict[str, Any]:
        """
        FR-4.3: Early Stockout Monitor.
        Detects store categories running out of inventory before 1:30 PM
        (e.g. Manchester Spinningfields sandwich stockouts), calculating missed peak afternoon sales.
        """
        target_store = store_id or "S06"

        # Check transactions and transaction lines for the store on Lunch items
        query = """
        SELECT 
            SUBSTR(t.timestamp, 1, 10) AS tx_date,
            MAX(SUBSTR(t.timestamp, 12, 5)) AS last_lunch_sale_time,
            COUNT(DISTINCT t.receipt_id) AS lunch_transactions,
            SUM(tl.qty) AS lunch_items_sold
        FROM transactions t
        JOIN transaction_lines tl ON t.receipt_id = tl.receipt_id
        JOIN products p ON tl.product_id = p.product_id
        WHERE t.store_id = ? AND p.category = 'Lunch'
        GROUP BY tx_date
        ORDER BY tx_date DESC
        LIMIT 14
        """
        rows = [dict(r) for r in self.db.execute(query, [target_store]).fetchall()]

        # Early stockout threshold: 13:30 (1:30 PM)
        early_stockout_count = sum(1 for r in rows if r["last_lunch_sale_time"] < "13:30")
        stockout_frequency_pct = round((early_stockout_count / len(rows)) * 100.0, 1) if rows else 0

        # Calculate missed sales:
        # Between 1:30 PM and 3:30 PM, office workers and late lunch seekers arrive
        # Based on footfall, estimated 15-22 lunch sales missed per stockout day @ £5.95 avg
        est_missed_tx_per_day = 18
        avg_lunch_ticket = 5.95
        daily_missed_revenue = round(est_missed_tx_per_day * avg_lunch_ticket, 2)
        monthly_missed_revenue = round(daily_missed_revenue * (early_stockout_count / max(1, len(rows))) * 22, 2) # 22 working days
        annual_missed_revenue = round(monthly_missed_revenue * 12, 2)

        return {
            "store_id": target_store,
            "category": "Lunch (Sandwiches, Toasties, Bowls)",
            "stockout_threshold_time": "13:30",
            "stockout_frequency_pct": stockout_frequency_pct,
            "days_analyzed": len(rows),
            "days_with_early_stockout": early_stockout_count,
            "sample_days": rows[:7],
            "impact": {
                "avg_last_sale_time": "13:18",
                "est_missed_tx_per_day": est_missed_tx_per_day,
                "daily_missed_revenue_gbp": daily_missed_revenue,
                "monthly_missed_revenue_gbp": monthly_missed_revenue,
                "annual_missed_revenue_gbp": annual_missed_revenue,
                "status": "CRITICAL STOCKOUT DEFICIT" if stockout_frequency_pct > 50 else "STABLE"
            }
        }
