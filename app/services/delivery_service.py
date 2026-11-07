import sqlite3
from typing import Optional, List, Dict, Any
from app.config import CHAIN_BENCHMARKS

class DeliveryService:
    def __init__(self, db: sqlite3.Connection):
        self.db = db

    def get_channel_margin_waterfall(self, store_id: Optional[str] = None) -> Dict[str, Any]:
        """
        FR-2.1: Channel Margin Waterfall.
        Breaks down contribution margins per ticket across:
        - In-Store
        - Direct App (Click & Collect)
        - Dashly (Delivery)
        - RushEats (Delivery)
        Nets out platform commissions (27%-33%), packaging (£0.45), 
        and 4 min staff packing labor (~£0.93 per order).
        """
        store_filter_tx = "WHERE store_id = ?" if store_id else ""
        params = [store_id] if store_id else []

        # 1. In-Store & Direct App from transactions
        query_channels = f"""
        SELECT 
            channel,
            COUNT(*) AS order_count,
            ROUND(AVG(net_gbp), 2) AS avg_ticket_gbp,
            ROUND(SUM(net_gbp), 2) AS total_sales_gbp
        FROM transactions
        {store_filter_tx}
        GROUP BY channel
        """
        ch_rows = {r["channel"]: dict(r) for r in self.db.execute(query_channels, params).fetchall()}

        # 2. Delivery partners from vw_delivery_economics
        store_filter_deliv = "WHERE store_id = ?" if store_id else ""
        query_deliv = f"""
        SELECT 
            delivery_partner,
            COUNT(*) AS order_count,
            ROUND(AVG(net_gbp), 2) AS avg_ticket_gbp,
            ROUND(AVG(commission_gbp), 2) AS avg_commission_gbp,
            ROUND(AVG(commission_rate) * 100.0, 1) AS avg_commission_pct,
            0.45 AS packaging_cost_gbp,
            0.93 AS labor_packing_cost_gbp,
            ROUND(AVG(est_food_cost_gbp), 2) AS avg_food_cost_gbp,
            ROUND(AVG(net_contribution_gbp), 2) AS avg_net_contribution_gbp,
            ROUND(AVG(net_contribution_gbp / NULLIF(net_gbp, 0)) * 100.0, 2) AS contribution_margin_pct,
            ROUND(SUM(net_gbp), 2) AS total_sales_gbp,
            ROUND(SUM(net_contribution_gbp), 2) AS total_contribution_gbp
        FROM vw_delivery_economics
        {store_filter_deliv}
        GROUP BY delivery_partner
        """
        deliv_rows = {r["delivery_partner"]: dict(r) for r in self.db.execute(query_deliv, params).fetchall()}

        # Construct unified channels breakdown
        channels_breakdown = []
        
        # In-store
        instore = ch_rows.get("In-store", {"avg_ticket_gbp": 5.82, "order_count": 0, "total_sales_gbp": 0.0})
        instore_ticket = instore.get("avg_ticket_gbp", 5.82)
        instore_food = round(instore_ticket * 0.28, 2)
        instore_pack = 0.05  # minimal napkin/cup
        instore_labor = 0.50 # quick handover
        instore_comm = 0.0
        instore_contrib = round(instore_ticket - instore_food - instore_pack - instore_labor, 2)
        
        channels_breakdown.append({
            "channel_name": "In-Store",
            "order_count": instore["order_count"],
            "avg_ticket_gbp": instore_ticket,
            "commission_rate_pct": 0.0,
            "commission_gbp": 0.0,
            "packaging_cost_gbp": instore_pack,
            "labor_packing_cost_gbp": instore_labor,
            "food_cost_gbp": instore_food,
            "net_contribution_gbp": instore_contrib,
            "contribution_margin_pct": round((instore_contrib / instore_ticket) * 100, 1) if instore_ticket else 0,
            "notes": "Direct walk-in. High conversion, zero third-party commission."
        })

        # Direct App Click & Collect
        app_order = ch_rows.get("App Click & Collect", {"avg_ticket_gbp": 6.10, "order_count": 0, "total_sales_gbp": 0.0})
        app_ticket = app_order.get("avg_ticket_gbp", 6.10)
        app_food = round(app_ticket * 0.28, 2)
        app_pack = 0.15  # cup tray/bag
        app_labor = 0.45
        app_comm = 0.0   # Owned channel (card processing ~1.5% absorbed)
        app_contrib = round(app_ticket - app_food - app_pack - app_labor, 2)
        
        channels_breakdown.append({
            "channel_name": "Direct App (Click & Collect)",
            "order_count": app_order["order_count"],
            "avg_ticket_gbp": app_ticket,
            "commission_rate_pct": 0.0,
            "commission_gbp": 0.0,
            "packaging_cost_gbp": app_pack,
            "labor_packing_cost_gbp": app_labor,
            "food_cost_gbp": app_food,
            "net_contribution_gbp": app_contrib,
            "contribution_margin_pct": round((app_contrib / app_ticket) * 100, 1) if app_ticket else 0,
            "notes": "Proprietary channel. Highest margin per ticket, customer loyalty captured."
        })

        # Dashly
        dashly = deliv_rows.get("Dashly", {
            "avg_ticket_gbp": 12.73, "order_count": 0, "avg_commission_gbp": 3.73, "avg_commission_pct": 29.3,
            "packaging_cost_gbp": 0.45, "labor_packing_cost_gbp": 0.93, "avg_food_cost_gbp": 3.56,
            "avg_net_contribution_gbp": 4.10, "contribution_margin_pct": 32.2
        })
        channels_breakdown.append({
            "channel_name": "Dashly (Delivery)",
            "order_count": dashly["order_count"],
            "avg_ticket_gbp": dashly["avg_ticket_gbp"],
            "commission_rate_pct": dashly["avg_commission_pct"],
            "commission_gbp": dashly["avg_commission_gbp"],
            "packaging_cost_gbp": 0.45,
            "labor_packing_cost_gbp": 0.93,
            "food_cost_gbp": dashly["avg_food_cost_gbp"],
            "net_contribution_gbp": dashly["avg_net_contribution_gbp"],
            "contribution_margin_pct": dashly["contribution_margin_pct"],
            "notes": "27% commission until Mar 2026, increased to 33% from Apr 2026."
        })

        # RushEats
        rusheats = deliv_rows.get("RushEats", {
            "avg_ticket_gbp": 12.64, "order_count": 0, "avg_commission_gbp": 3.79, "avg_commission_pct": 30.0,
            "packaging_cost_gbp": 0.45, "labor_packing_cost_gbp": 0.93, "avg_food_cost_gbp": 3.54,
            "avg_net_contribution_gbp": 3.93, "contribution_margin_pct": 31.1
        })
        channels_breakdown.append({
            "channel_name": "RushEats (Delivery)",
            "order_count": rusheats["order_count"],
            "avg_ticket_gbp": rusheats["avg_ticket_gbp"],
            "commission_rate_pct": rusheats["avg_commission_pct"],
            "commission_gbp": rusheats["avg_commission_gbp"],
            "packaging_cost_gbp": 0.45,
            "labor_packing_cost_gbp": 0.93,
            "food_cost_gbp": rusheats["avg_food_cost_gbp"],
            "net_contribution_gbp": rusheats["avg_net_contribution_gbp"],
            "contribution_margin_pct": rusheats["contribution_margin_pct"],
            "notes": "Fixed 30% commission. 29.3% of volume is sub-£8 orders."
        })

        return {
            "channels": channels_breakdown,
            "benchmarks": {
                "packaging_standard_gbp": 0.45,
                "labor_minutes_standard": 4.0,
                "labor_packing_cost_gbp": 0.93
            }
        }

    def get_sub8_order_alarm(self, store_id: Optional[str] = None) -> Dict[str, Any]:
        """
        FR-2.2: Sub-£8 Order Alarm.
        Filters delivery volume to highlight single-drink / sub-£8 orders.
        Calculates net margin per order (e.g. £0.79 contribution) and displays
        capacity impact during peak hours.
        """
        filter_sql = "WHERE 1=1"
        params = []
        if store_id:
            filter_sql += " AND store_id = ?"
            params.append(store_id)

        # Overview of sub-8 vs non-sub-8 orders
        query = f"""
        SELECT 
            is_sub_8,
            COUNT(*) AS order_count,
            ROUND(AVG(net_gbp), 2) AS avg_ticket_gbp,
            ROUND(AVG(commission_gbp), 2) AS avg_commission_gbp,
            ROUND(AVG(est_food_cost_gbp), 2) AS avg_food_cost_gbp,
            0.45 AS packaging_cost_gbp,
            0.93 AS labor_packing_cost_gbp,
            ROUND(AVG(net_contribution_gbp), 2) AS avg_net_contribution_gbp,
            ROUND(AVG(net_contribution_gbp / NULLIF(net_gbp, 0)) * 100.0, 2) AS margin_pct,
            ROUND(SUM(net_gbp), 2) AS total_revenue_gbp,
            ROUND(SUM(net_contribution_gbp), 2) AS total_contribution_gbp
        FROM vw_delivery_economics
        {filter_sql}
        GROUP BY is_sub_8
        """
        rows = [dict(r) for r in self.db.execute(query, params).fetchall()]

        sub8_stats = next((r for r in rows if r["is_sub_8"] == 1), {})
        normal_stats = next((r for r in rows if r["is_sub_8"] == 0), {})

        total_orders = (sub8_stats.get("order_count", 0) + normal_stats.get("order_count", 0))
        sub8_count = sub8_stats.get("order_count", 0)
        sub8_pct = round((sub8_count / total_orders) * 100.0, 1) if total_orders else 0

        # Hourly distribution during peak rush (11:00 - 14:00)
        hourly_query = f"""
        SELECT 
            order_hour,
            COUNT(*) AS total_orders,
            SUM(is_sub_8) AS sub8_orders,
            ROUND(SUM(is_sub_8) * 100.0 / COUNT(*), 1) AS sub8_share_pct,
            ROUND(SUM(is_sub_8) * 4.0 / 60.0, 1) AS sub8_staff_hours_consumed
        FROM vw_delivery_economics
        {filter_sql}
        GROUP BY order_hour
        ORDER BY order_hour ASC
        """
        hourly_distribution = [dict(r) for r in self.db.execute(hourly_query, params).fetchall()]

        # Peak hours analysis (11am to 2pm)
        peak_hours = [h for h in hourly_distribution if h["order_hour"] in ["11", "12", "13"]]
        peak_sub8_orders = sum(h["sub8_orders"] for h in peak_hours)
        peak_staff_hours_lost = round(sum(h["sub8_staff_hours_consumed"] for h in peak_hours), 1)

        # By store breakdown (to see who is hit hardest, e.g. S07 Manchester Piccadilly)
        store_query = f"""
        SELECT 
            store_id,
            COUNT(*) AS total_delivery_orders,
            SUM(is_sub_8) AS sub8_orders,
            ROUND(SUM(is_sub_8) * 100.0 / COUNT(*), 1) AS sub8_pct,
            ROUND(AVG(CASE WHEN is_sub_8 = 1 THEN net_contribution_gbp ELSE NULL END), 2) AS avg_sub8_contribution_gbp,
            ROUND(SUM(CASE WHEN is_sub_8 = 1 THEN 4.0 ELSE 0 END) / 60.0, 1) AS total_hours_packing_sub8
        FROM vw_delivery_economics
        {filter_sql}
        GROUP BY store_id
        ORDER BY sub8_orders DESC
        """
        store_breakdown = [dict(r) for r in self.db.execute(store_query, params).fetchall()]

        return {
            "sub8_count": sub8_count,
            "total_delivery_orders": total_orders,
            "sub8_pct": sub8_pct,
            "sub8_economics": sub8_stats,
            "normal_economics": normal_stats,
            "peak_impact": {
                "peak_sub8_orders": peak_sub8_orders,
                "peak_staff_hours_lost": peak_staff_hours_lost,
                "alarm_status": "CRITICAL" if sub8_pct > 25 else "NORMAL",
                "recommendation": "Institute £8 minimum basket threshold or £1.50 small order surcharge to eliminate single-coffee delivery friction."
            },
            "hourly_distribution": hourly_distribution,
            "store_breakdown": store_breakdown
        }

    def simulate_delivery_markup(
        self, 
        markup_pct: float = 15.0, 
        apply_min_basket_8: bool = False,
        volume_elasticity: float = -0.3,
        store_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        FR-2.3: Delivery Markup Simulator.
        Scenario modeling tool allowing executives to simulate the net profit impact
        of applying a 15%-20% menu markup or an £8 minimum basket threshold on delivery apps.
        
        volume_elasticity: e.g. -0.3 means for a 15% price increase, delivery volume drops by 4.5%.
        """
        filter_sql = "WHERE 1=1"
        params = []
        if store_id:
            filter_sql += " AND store_id = ?"
            params.append(store_id)

        # Baseline metrics from vw_delivery_economics
        query = f"""
        SELECT 
            COUNT(*) AS total_orders,
            SUM(is_sub_8) AS sub8_orders,
            ROUND(SUM(net_gbp), 2) AS current_revenue_gbp,
            ROUND(AVG(net_gbp), 2) AS current_avg_ticket_gbp,
            ROUND(SUM(commission_gbp), 2) AS current_commission_gbp,
            ROUND(SUM(packaging_cost_gbp), 2) AS current_packaging_gbp,
            ROUND(SUM(labor_packing_cost_gbp), 2) AS current_labor_packing_gbp,
            ROUND(SUM(est_food_cost_gbp), 2) AS current_food_cost_gbp,
            ROUND(SUM(net_contribution_gbp), 2) AS current_contribution_gbp
        FROM vw_delivery_economics
        {filter_sql}
        """
        curr = dict(self.db.execute(query, params).fetchone())
        
        current_orders = curr["total_orders"]
        current_revenue = curr["current_revenue_gbp"]
        current_contrib = curr["current_contribution_gbp"]
        avg_commission_rate = curr["current_commission_gbp"] / current_revenue if current_revenue else 0.30

        # Scenario calculations
        # 1. Markup impact on ticket
        price_multiplier = 1.0 + (markup_pct / 100.0)
        # Volume impact due to elasticity
        volume_multiplier = 1.0 + (volume_elasticity * (markup_pct / 100.0))
        
        simulated_orders = round(current_orders * volume_multiplier)
        
        # If minimum basket of £8 applied, sub-8 orders either get bumped to £8 or dropped
        if apply_min_basket_8:
            # Partners who switched saw AOV rise by 18-25% with small drop in order count (from RushEats email)
            # Assume 65% of sub-8 orders add an item to hit £8, 35% drop
            sub8_count = curr["sub8_orders"]
            dropped_sub8 = round(sub8_count * 0.30)
            bumped_sub8 = sub8_count - dropped_sub8
            simulated_orders = max(1, simulated_orders - dropped_sub8)
            new_avg_ticket = max(8.50, round(curr["current_avg_ticket_gbp"] * price_multiplier * 1.08, 2))
        else:
            new_avg_ticket = round(curr["current_avg_ticket_gbp"] * price_multiplier, 2)

        simulated_revenue = round(simulated_orders * new_avg_ticket, 2)
        simulated_commission = round(simulated_revenue * avg_commission_rate, 2)
        simulated_packaging = round(simulated_orders * 0.45, 2)
        simulated_labor = round(simulated_orders * 0.93, 2)
        simulated_food_cost = round(simulated_orders * (curr["current_food_cost_gbp"] / current_orders), 2)
        
        simulated_contribution = round(
            simulated_revenue - (simulated_commission + simulated_packaging + simulated_labor + simulated_food_cost), 
            2
        )
        
        annualized_profit_delta = round((simulated_contribution - current_contrib) * 10, 2) # Sample is 10%

        return {
            "inputs": {
                "markup_pct": markup_pct,
                "apply_min_basket_8": apply_min_basket_8,
                "volume_elasticity": volume_elasticity
            },
            "baseline": {
                "orders": current_orders,
                "avg_ticket_gbp": curr["current_avg_ticket_gbp"],
                "total_revenue_gbp": current_revenue,
                "total_contribution_gbp": current_contrib,
                "contribution_margin_pct": round((current_contrib / current_revenue) * 100, 2)
            },
            "simulated": {
                "orders": simulated_orders,
                "avg_ticket_gbp": new_avg_ticket,
                "total_revenue_gbp": simulated_revenue,
                "total_contribution_gbp": simulated_contribution,
                "contribution_margin_pct": round((simulated_contribution / simulated_revenue) * 100, 2)
            },
            "impact": {
                "contribution_gain_gbp": round(simulated_contribution - current_contrib, 2),
                "margin_improvement_pts": round((simulated_contribution / simulated_revenue * 100) - (current_contrib / current_revenue * 100), 2),
                "annualized_chain_profit_recovery_gbp": annualized_profit_delta,
                "hours_saved_from_small_orders": round((current_orders - simulated_orders) * 4.0 / 60.0, 1)
            }
        }
