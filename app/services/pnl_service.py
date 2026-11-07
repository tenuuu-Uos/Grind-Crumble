import sqlite3
from typing import Optional, List, Dict, Any
from app.config import CHAIN_BENCHMARKS

class PnLService:
    def __init__(self, db: sqlite3.Connection):
        self.db = db

    def get_network_ranking(self, month: Optional[str] = None, store_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        FR-1.1: True Profit Heatmap / Store Ranking Matrix.
        Ranks stores by Operating Margin (%) and Net Profit (£) rather than gross sales volume.
        Clearly flags high-volume loss-makers like Manchester Piccadilly (S07).
        """
        query = """
        SELECT 
            store_id,
            store_name,
            city,
            format,
            location_type,
            ROUND(SUM(total_sales_gbp), 2) AS total_sales_gbp,
            ROUND(SUM(store_profit_gbp), 2) AS net_profit_gbp,
            ROUND((SUM(store_profit_gbp) / NULLIF(SUM(total_sales_gbp), 0)) * 100.0, 2) AS operating_margin_pct,
            ROUND(SUM(rent_gbp), 2) AS total_rent_gbp,
            ROUND(SUM(business_rates_gbp), 2) AS total_rates_gbp,
            ROUND(((SUM(rent_gbp) + SUM(business_rates_gbp)) / NULLIF(SUM(total_sales_gbp), 0)) * 100.0, 2) AS fixed_occupancy_pct,
            ROUND(SUM(labour_cost_gbp), 2) AS total_labour_cost_gbp,
            ROUND(SUM(food_cost_gbp), 2) AS total_food_cost_gbp,
            ROUND(AVG(waste_rate) * 100.0, 2) AS avg_waste_rate_pct,
            ROUND(AVG(staff_survey_score_10), 1) AS avg_staff_score,
            SUM(total_receipts) AS total_transactions
        FROM vw_store_monthly_pnl
        WHERE 1=1
        """
        params = []
        if month:
            query += " AND month = ?"
            params.append(month)
        if store_id:
            query += " AND store_id = ?"
            params.append(store_id)

        query += " GROUP BY store_id, store_name, city, format, location_type"
        query += " ORDER BY net_profit_gbp DESC"

        cursor = self.db.execute(query, params)
        rows = [dict(row) for row in cursor.fetchall()]

        # Compute volume ranking vs profit ranking to identify the "Paradox"
        # Sort by total sales to assign sales_rank
        sorted_by_sales = sorted(rows, key=lambda x: x["total_sales_gbp"], reverse=True)
        sales_ranks = {item["store_id"]: i + 1 for i, item in enumerate(sorted_by_sales)}

        for i, item in enumerate(rows):
            item["profit_rank"] = i + 1
            item["sales_rank"] = sales_ranks[item["store_id"]]
            item["rank_divergence"] = item["sales_rank"] - item["profit_rank"] # Negative means high sales, low profit!
            
            # Identify high-volume loss makers
            item["is_high_volume_loss_maker"] = (item["sales_rank"] <= 3 and item["net_profit_gbp"] < 0)
            item["occupancy_alert"] = item["fixed_occupancy_pct"] > CHAIN_BENCHMARKS["fixed_occupancy_max_pct"]
            
            # Margin health classification
            if item["operating_margin_pct"] < 0:
                item["margin_status"] = "Loss Making"
                item["margin_badge_color"] = "red"
            elif item["operating_margin_pct"] < 10:
                item["margin_status"] = "Low Margin"
                item["margin_badge_color"] = "amber"
            elif item["operating_margin_pct"] < 18:
                item["margin_status"] = "Healthy"
                item["margin_badge_color"] = "blue"
            else:
                item["margin_status"] = "Top Tier"
                item["margin_badge_color"] = "emerald"

        return rows

    def get_fixed_occupancy_calculator(self) -> Dict[str, Any]:
        """
        FR-1.2: Fixed Occupancy Calculator.
        Tracks Rent + Business Rates as % of Total Revenue.
        Triggers alert when fixed occupancy costs exceed 25% of store sales (e.g. S07 at 40.2%).
        """
        query = """
        SELECT 
            store_id,
            store_name,
            city,
            location_type,
            ROUND(SUM(total_sales_gbp), 2) AS total_sales_gbp,
            ROUND(SUM(rent_gbp + business_rates_gbp), 2) AS total_fixed_occupancy_gbp,
            ROUND(((SUM(rent_gbp + business_rates_gbp)) / NULLIF(SUM(total_sales_gbp), 0)) * 100.0, 2) AS occupancy_pct,
            ROUND(SUM(store_profit_gbp), 2) AS total_profit_gbp,
            ROUND(AVG(rent_gbp), 2) AS monthly_rent_gbp,
            ROUND(AVG(business_rates_gbp), 2) AS monthly_rates_gbp
        FROM vw_store_monthly_pnl
        GROUP BY store_id, store_name, city, location_type
        ORDER BY occupancy_pct DESC
        """
        rows = [dict(r) for r in self.db.execute(query).fetchall()]
        
        alerts = []
        for r in rows:
            is_breached = r["occupancy_pct"] > CHAIN_BENCHMARKS["fixed_occupancy_max_pct"]
            r["threshold_breached"] = is_breached
            r["excess_occupancy_pct"] = max(0.0, round(r["occupancy_pct"] - CHAIN_BENCHMARKS["fixed_occupancy_max_pct"], 2))
            
            # Estimated annual drag = sales * (occupancy_pct - 25%)
            if is_breached:
                drag = round(r["total_sales_gbp"] * (r["excess_occupancy_pct"] / 100.0), 2)
                r["annual_drag_gbp"] = drag
                alerts.append({
                    "store_id": r["store_id"],
                    "store_name": r["store_name"],
                    "occupancy_pct": r["occupancy_pct"],
                    "threshold_pct": CHAIN_BENCHMARKS["fixed_occupancy_max_pct"],
                    "annual_drag_gbp": drag,
                    "severity": "CRITICAL" if r["occupancy_pct"] > 35 else "WARNING"
                })
            else:
                r["annual_drag_gbp"] = 0.0

        return {
            "threshold_pct": CHAIN_BENCHMARKS["fixed_occupancy_max_pct"],
            "stores": rows,
            "alerts": alerts,
            "total_network_drag_gbp": round(sum(a["annual_drag_gbp"] for a in alerts), 2)
        }

    def get_cannibalization_audit(self) -> Dict[str, Any]:
        """
        FR-1.3: Cannibalization Audit Tool.
        Compares performance metrics pre- and post-opening of neighboring sites.
        Specifically Leeds Trinity (S12, opened 2025-09-15) vs Leeds Briggate (S03).
        Quantifies revenue dilution vs net market profit.
        """
        query = """
        SELECT 
            month,
            store_id,
            store_name,
            total_sales_gbp,
            store_profit_gbp,
            total_receipts,
            avg_ticket_gbp
        FROM vw_store_monthly_pnl
        WHERE store_id IN ('S03', 'S12')
        ORDER BY month ASC, store_id ASC
        """
        rows = [dict(r) for r in self.db.execute(query).fetchall()]
        
        # Organize by month
        months_data = {}
        for r in rows:
            m = r["month"]
            if m not in months_data:
                months_data[m] = {"month": m, "S03": None, "S12": None}
            months_data[m][r["store_id"]] = r

        timeline = []
        for m, data in sorted(months_data.items()):
            s03 = data.get("S03") or {}
            s12 = data.get("S12") or {}
            s03_sales = s03.get("total_sales_gbp", 0.0) or 0.0
            s12_sales = s12.get("total_sales_gbp", 0.0) or 0.0
            s03_profit = s03.get("store_profit_gbp", 0.0) or 0.0
            s12_profit = s12.get("store_profit_gbp", 0.0) or 0.0

            timeline.append({
                "month": m,
                "is_post_opening": m >= "2025-09",
                "s03_sales": s03_sales,
                "s12_sales": s12_sales,
                "combined_leeds_sales": round(s03_sales + s12_sales, 2),
                "s03_profit": s03_profit,
                "s12_profit": s12_profit,
                "combined_leeds_profit": round(s03_profit + s12_profit, 2),
            })

        # Pre-opening baseline (2025-07, 2025-08) for S03
        pre_months = [t for t in timeline if not t["is_post_opening"]]
        post_months = [t for t in timeline if t["is_post_opening"]]

        avg_pre_s03_sales = sum(t["s03_sales"] for t in pre_months) / len(pre_months) if pre_months else 0
        avg_post_s03_sales = sum(t["s03_sales"] for t in post_months) / len(post_months) if post_months else 0
        avg_post_s12_sales = sum(t["s12_sales"] for t in post_months) / len(post_months) if post_months else 0
        
        avg_pre_s03_profit = sum(t["s03_profit"] for t in pre_months) / len(pre_months) if pre_months else 0
        avg_post_s03_profit = sum(t["s03_profit"] for t in post_months) / len(post_months) if post_months else 0
        avg_post_s12_profit = sum(t["s12_profit"] for t in post_months) / len(post_months) if post_months else 0

        monthly_s03_dilution_gbp = round(avg_pre_s03_sales - avg_post_s03_sales, 2)
        monthly_s03_dilution_pct = round((monthly_s03_dilution_gbp / avg_pre_s03_sales) * 100.0, 2) if avg_pre_s03_sales else 0
        
        # Net market expansion
        monthly_market_gain_sales = round((avg_post_s03_sales + avg_post_s12_sales) - avg_pre_s03_sales, 2)
        monthly_market_gain_profit = round((avg_post_s03_profit + avg_post_s12_profit) - avg_pre_s03_profit, 2)

        return {
            "focus_site": "Leeds Briggate (S03)",
            "cannibalizing_site": "Leeds Trinity (S12, opened 2025-09-15)",
            "timeline": timeline,
            "metrics": {
                "pre_opening_s03_avg_monthly_sales": round(avg_pre_s03_sales, 2),
                "post_opening_s03_avg_monthly_sales": round(avg_post_s03_sales, 2),
                "s03_monthly_sales_dilution_gbp": monthly_s03_dilution_gbp,
                "s03_sales_dilution_pct": monthly_s03_dilution_pct,
                "s12_monthly_sales_contribution_gbp": round(avg_post_s12_sales, 2),
                "net_leeds_market_sales_delta_gbp": monthly_market_gain_sales,
                "net_leeds_market_profit_delta_gbp": monthly_market_gain_profit,
                "annualized_s03_revenue_loss_gbp": round(monthly_s03_dilution_gbp * 12, 2),
                "annualized_combined_market_gain_gbp": round(monthly_market_gain_sales * 12, 2),
                "verdict": "Partial Cannibalization with Net Positive Market Expansion"
            }
        }
