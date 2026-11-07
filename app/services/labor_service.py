import sqlite3
from typing import Optional, List, Dict, Any
from app.config import CHAIN_BENCHMARKS

class LaborService:
    def __init__(self, db: sqlite3.Connection):
        self.db = db

    def get_bottleneck_index(self, store_id: Optional[str] = None) -> Dict[str, Any]:
        """
        FR-3.1: 11am-2pm Bottleneck Index.
        Overlays footfall sensor data against active barista headcount and
        transaction throughput to detect staffing deficits (e.g. 3 staff vs 5 needed at peak).
        """
        store_filter = "WHERE s.store_id = ?" if store_id else ""
        params = [store_id] if store_id else []

        query = f"""
        WITH lunch_footfall AS (
            SELECT 
                store_id,
                ROUND(AVG(door_count), 1) AS avg_lunch_door_count,
                MAX(door_count) AS peak_lunch_door_count
            FROM footfall
            WHERE daypart = 'Lunch'
            GROUP BY store_id
        ),
        lunch_rota AS (
            SELECT 
                store_id,
                ROUND(AVG(scheduled_hours) / 7.0, 1) AS avg_daily_lunch_hours,
                -- Front-of-counter espresso baristas: deducting ~1.0 FTE for delivery bagging & support
                ROUND(MAX(2.0, (AVG(scheduled_hours) / (7.0 * 3.0)) * 0.70), 1) AS avg_active_headcount, 
                ROUND(AVG(avg_hourly_wage_gbp), 2) AS avg_wage_gbp
            FROM staff_rota_weekly
            WHERE daypart = 'Lunch'
            GROUP BY store_id
        ),
        lunch_tx AS (
            SELECT 
                store_id,
                -- sample is 10%, so multiply count by 10 to get estimated actual daily lunch transactions
                ROUND(COUNT(*) * 10.0 / 365.0, 1) AS avg_daily_lunch_tx,
                ROUND(AVG(net_gbp), 2) AS avg_ticket_gbp
            FROM transactions
            WHERE SUBSTR(timestamp, 12, 2) IN ('11', '12', '13')
            GROUP BY store_id
        )
        SELECT 
            s.store_id,
            s.store_name,
            s.city,
            s.format,
            s.seats,
            COALESCE(lf.avg_lunch_door_count, 0) AS avg_lunch_door_count,
            COALESCE(lf.peak_lunch_door_count, 0) AS peak_lunch_door_count,
            COALESCE(lr.avg_active_headcount, 3.0) AS active_baristas_lunch,
            COALESCE(lr.avg_wage_gbp, 12.40) AS avg_hourly_wage,
            COALESCE(lt.avg_daily_lunch_tx, 0) AS avg_daily_lunch_transactions,
            COALESCE(lt.avg_ticket_gbp, 5.80) AS avg_ticket_gbp
        FROM stores s
        LEFT JOIN lunch_footfall lf ON s.store_id = lf.store_id
        LEFT JOIN lunch_rota lr ON s.store_id = lr.store_id
        LEFT JOIN lunch_tx lt ON s.store_id = lt.store_id
        {store_filter}
        ORDER BY lf.avg_lunch_door_count DESC
        """
        rows = [dict(r) for r in self.db.execute(query, params).fetchall()]

        # Capacity assumptions:
        # Standard sustained throughput per barista: ~16.5 drinks/transactions per hour
        # (accounting for order taking, milk texturing, and delivery packaging interference)
        # Target capture rate of door footfall: ~70%
        for r in rows:
            footfall = r["avg_lunch_door_count"]
            active_staff = r["active_baristas_lunch"]
            
            # Theoretical demand = footfall * 70% conversion
            expected_demand_tx = footfall * 0.70
            
            # Staff capacity across 3-hour window = staff * 16.5 drinks/hour * 3 hours (~50 drinks/staff)
            capacity_tx = active_staff * 16.5 * 3.0
            
            # Needed staff to meet demand without queue walkouts (e.g. 5 staff needed at S07 for ~245 demand)
            needed_staff = round(expected_demand_tx / (16.5 * 3.0), 1)
            staffing_deficit = round(max(0.0, needed_staff - active_staff), 1)
            
            # Bottleneck Index: 100 is balanced. >110 is congested, >125 is critical bottleneck
            bottleneck_index = round((expected_demand_tx / max(1.0, capacity_tx)) * 100.0, 1)
            
            r["expected_demand_tx"] = round(expected_demand_tx, 1)
            r["capacity_tx"] = round(capacity_tx, 1)
            r["needed_baristas_lunch"] = max(active_staff, needed_staff)
            r["staffing_deficit"] = staffing_deficit
            r["bottleneck_index"] = bottleneck_index
            
            if bottleneck_index >= 125 or staffing_deficit >= 1.5:
                r["bottleneck_severity"] = "CRITICAL"
                r["alert_badge"] = "red"
            elif bottleneck_index >= 105 or staffing_deficit >= 0.8:
                r["bottleneck_severity"] = "HIGH"
                r["alert_badge"] = "amber"
            else:
                r["bottleneck_severity"] = "OPTIMAL"
                r["alert_badge"] = "emerald"

        return {
            "stores": rows,
            "critical_bottlenecks": [r for r in rows if r["bottleneck_severity"] == "CRITICAL"]
        }

    def get_walkout_revenue_loss(self, store_id: Optional[str] = None) -> Dict[str, Any]:
        """
        FR-3.2: Walkout Revenue Loss Estimator.
        Estimates uncaptured revenue when door footfall spikes but transaction
        volume caps, flagging lost walkaway revenue during peak rush windows.
        """
        bottleneck_data = self.get_bottleneck_index(store_id)["stores"]

        results = []
        total_daily_loss = 0.0
        total_annual_loss = 0.0

        for s in bottleneck_data:
            footfall = s["avg_lunch_door_count"]
            active_staff = s["active_baristas_lunch"]
            actual_tx = s["avg_daily_lunch_transactions"]
            avg_ticket = s["avg_ticket_gbp"]
            
            # Potential demand if staffed properly
            potential_tx = s["expected_demand_tx"]
            
            # Walkaways = potential customers who left because line > 5 deep
            daily_walkouts = max(0.0, round(potential_tx - actual_tx, 1))
            daily_lost_revenue_gbp = round(daily_walkouts * avg_ticket, 2)
            monthly_lost_revenue_gbp = round(daily_lost_revenue_gbp * 30.0, 2)
            annual_lost_revenue_gbp = round(daily_lost_revenue_gbp * 365.0, 2)

            # Cost to add needed staff for 3 hour lunch rush:
            # extra staff * 3 hours * hourly wage * 1.13 on-cost
            deficit = s["staffing_deficit"]
            hourly_wage = s["avg_hourly_wage"]
            daily_labor_cost_to_fix = round(deficit * 3.0 * hourly_wage * CHAIN_BENCHMARKS["labor_on_cost_multiplier"], 2)
            annual_labor_cost_to_fix = round(daily_labor_cost_to_fix * 365.0, 2)
            
            # Net ROI of fixing the bottleneck
            annual_net_benefit = round(annual_lost_revenue_gbp - annual_labor_cost_to_fix, 2)
            roi_ratio = round(annual_lost_revenue_gbp / annual_labor_cost_to_fix, 1) if annual_labor_cost_to_fix > 0 else 0.0

            total_daily_loss += daily_lost_revenue_gbp
            total_annual_loss += annual_lost_revenue_gbp

            results.append({
                "store_id": s["store_id"],
                "store_name": s["store_name"],
                "city": s["city"],
                "active_staff": active_staff,
                "needed_staff": s["needed_baristas_lunch"],
                "staffing_deficit": deficit,
                "daily_walkouts": daily_walkouts,
                "avg_ticket_gbp": avg_ticket,
                "daily_lost_revenue_gbp": daily_lost_revenue_gbp,
                "monthly_lost_revenue_gbp": monthly_lost_revenue_gbp,
                "annual_lost_revenue_gbp": annual_lost_revenue_gbp,
                "daily_cost_to_fix": daily_labor_cost_to_fix,
                "annual_net_benefit_gbp": annual_net_benefit,
                "roi_ratio": roi_ratio,
                "severity": s["bottleneck_severity"]
            })

        results.sort(key=lambda x: x["annual_lost_revenue_gbp"], reverse=True)

        return {
            "stores": results,
            "total_daily_loss_gbp": round(total_daily_loss, 2),
            "total_annual_lost_revenue_gbp": round(total_annual_loss, 2),
            "top_loss_stores": results[:3]
        }

    def simulate_labor_inflation_stress(
        self, 
        wage_increase_pct: float = 6.7, 
        price_offset_pct: float = 0.0,
        store_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        FR-3.3: Labor Inflation Stress Tester.
        Models store profit impact following mandatory wage increases
        (e.g. 6.7% National Living Wage increase) against current sales per labor hour.
        """
        filter_sql = "WHERE 1=1"
        params = []
        if store_id:
            filter_sql += " AND store_id = ?"
            params.append(store_id)

        query = f"""
        SELECT 
            store_id,
            store_name,
            city,
            ROUND(SUM(total_sales_gbp), 2) AS annual_sales_gbp,
            ROUND(SUM(labour_hours), 1) AS annual_labour_hours,
            ROUND(SUM(labour_cost_gbp), 2) AS current_labour_cost_gbp,
            ROUND(SUM(store_profit_gbp), 2) AS current_profit_gbp,
            ROUND((SUM(store_profit_gbp) / NULLIF(SUM(total_sales_gbp), 0)) * 100.0, 2) AS current_margin_pct,
            ROUND(SUM(total_sales_gbp) / NULLIF(SUM(labour_hours), 0), 2) AS current_splh -- Sales Per Labor Hour
        FROM vw_store_monthly_pnl
        {filter_sql}
        GROUP BY store_id, store_name, city
        ORDER BY current_profit_gbp DESC
        """
        rows = [dict(r) for r in self.db.execute(query, params).fetchall()]

        wage_multiplier = 1.0 + (wage_increase_pct / 100.0)
        price_multiplier = 1.0 + (price_offset_pct / 100.0)

        total_current_profit = 0.0
        total_stressed_profit = 0.0
        total_wage_cost_increase = 0.0

        for r in rows:
            cur_sales = r["annual_sales_gbp"]
            cur_labour = r["current_labour_cost_gbp"]
            cur_profit = r["current_profit_gbp"]

            # Stressed labor cost
            stressed_labour = round(cur_labour * wage_multiplier, 2)
            labour_delta = round(stressed_labour - cur_labour, 2)

            # Potential price offset
            sim_sales = round(cur_sales * price_multiplier, 2)
            sales_delta = round(sim_sales - cur_sales, 2)

            # Stressed profit
            stressed_profit = round(cur_profit - labour_delta + sales_delta, 2)
            stressed_margin = round((stressed_profit / sim_sales) * 100.0, 2) if sim_sales else 0.0

            r["stressed_labour_cost_gbp"] = stressed_labour
            r["labour_cost_delta_gbp"] = labour_delta
            r["simulated_sales_gbp"] = sim_sales
            r["stressed_profit_gbp"] = stressed_profit
            r["stressed_margin_pct"] = stressed_margin
            r["margin_erosion_pts"] = round(r["current_margin_pct"] - stressed_margin, 2)
            
            # Sensitivity: Required menu price increase to fully neutralize the wage hike
            # delta_labour / cur_sales
            r["breakeven_price_rise_pct"] = round((labour_delta / cur_sales) * 100.0, 2) if cur_sales else 0.0

            total_current_profit += cur_profit
            total_stressed_profit += stressed_profit
            total_wage_cost_increase += labour_delta

        return {
            "inputs": {
                "wage_increase_pct": wage_increase_pct,
                "price_offset_pct": price_offset_pct
            },
            "summary": {
                "total_current_profit_gbp": round(total_current_profit, 2),
                "total_stressed_profit_gbp": round(total_stressed_profit, 2),
                "total_profit_erosion_gbp": round(total_current_profit - total_stressed_profit, 2),
                "total_wage_cost_increase_gbp": round(total_wage_cost_increase, 2),
                "chain_avg_splh": round(sum(r["annual_sales_gbp"] for r in rows) / max(1, sum(r["annual_labour_hours"] for r in rows)), 2),
                "chain_breakeven_price_rise_pct": round((total_wage_cost_increase / sum(r["annual_sales_gbp"] for r in rows)) * 100.0, 2)
            },
            "stores": rows
        }

def NULLIF(val, fallback):
    return val if val != 0 else fallback
