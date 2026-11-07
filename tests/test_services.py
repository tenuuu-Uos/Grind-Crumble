import unittest
import sqlite3
from app.config import DB_PATH, CHAIN_BENCHMARKS
from app.db.session import get_db_connection
from app.core.rbac import PERSONAS, verify_store_access
from app.services.pnl_service import PnLService
from app.services.delivery_service import DeliveryService
from app.services.labor_service import LaborService
from app.services.waste_service import WasteService
from app.services.digital_service import DigitalService
from app.services.expansion_service import ExpansionService

class TestServicesDirect(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = get_db_connection()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_module1_pnl_ranking(self):
        service = PnLService(self.db)
        stores = service.get_network_ranking()
        self.assertEqual(len(stores), 12)
        
        # S07 Manchester Piccadilly must be high volume loss maker
        s07 = next((s for s in stores if s["store_id"] == "S07"), None)
        self.assertIsNotNone(s07)
        self.assertTrue(s07["is_high_volume_loss_maker"])
        self.assertLess(s07["net_profit_gbp"], 0)
        self.assertGreater(s07["fixed_occupancy_pct"], 25.0)
        self.assertTrue(s07["occupancy_alert"])

    def test_module1_fixed_occupancy(self):
        service = PnLService(self.db)
        data = service.get_fixed_occupancy_calculator()
        self.assertGreaterEqual(len(data["alerts"]), 1)
        s07 = next((a for a in data["alerts"] if a["store_id"] == "S07"), None)
        self.assertIsNotNone(s07)
        self.assertGreater(s07["occupancy_pct"], 40.0) # S07 at ~40.2% - 41.4%
        self.assertEqual(s07["severity"], "CRITICAL")
        self.assertGreater(data["total_network_drag_gbp"], 100000.0)

    def test_module1_cannibalization(self):
        service = PnLService(self.db)
        data = service.get_cannibalization_audit()
        self.assertIn("timeline", data)
        self.assertIn("metrics", data)
        metrics = data["metrics"]
        self.assertGreater(metrics["s03_monthly_sales_dilution_gbp"], 15000.0) # ~£18k dilution
        self.assertGreater(metrics["net_leeds_market_sales_delta_gbp"], 0) # Net market expanded!

    def test_module2_delivery_waterfall(self):
        service = DeliveryService(self.db)
        data = service.get_channel_margin_waterfall()
        channels = {c["channel_name"]: c for c in data["channels"]}
        self.assertIn("In-Store", channels)
        self.assertIn("Direct App (Click & Collect)", channels)
        self.assertIn("Dashly (Delivery)", channels)
        self.assertIn("RushEats (Delivery)", channels)

        # Commissions checked
        self.assertGreater(channels["Dashly (Delivery)"]["commission_gbp"], 0)
        self.assertEqual(channels["In-Store"]["commission_gbp"], 0)

    def test_module2_sub8_alarm(self):
        service = DeliveryService(self.db)
        data = service.get_sub8_order_alarm()
        self.assertGreater(data["sub8_pct"], 25.0) # ~29% sub-8 orders
        self.assertLess(data["sub8_economics"]["avg_net_contribution_gbp"], 1.50) # Tiny contribution ~£0.79
        self.assertEqual(data["peak_impact"]["alarm_status"], "CRITICAL")

    def test_module2_markup_simulation(self):
        service = DeliveryService(self.db)
        data = service.simulate_delivery_markup(markup_pct=18.0, apply_min_basket_8=True)
        self.assertGreater(data["impact"]["annualized_chain_profit_recovery_gbp"], 30000.0)
        self.assertGreater(data["impact"]["margin_improvement_pts"], 3.0)

    def test_module3_bottleneck_index(self):
        service = LaborService(self.db)
        data = service.get_bottleneck_index()
        s07 = next((s for s in data["stores"] if s["store_id"] == "S07"), None)
        self.assertIsNotNone(s07)
        self.assertEqual(s07["bottleneck_severity"], "CRITICAL")
        self.assertGreater(s07["needed_baristas_lunch"], s07["active_baristas_lunch"])
        self.assertGreater(s07["staffing_deficit"], 1.0) # ~1.8 - 2 staff deficit

    def test_module3_walkouts(self):
        service = LaborService(self.db)
        data = service.get_walkout_revenue_loss()
        self.assertGreater(data["total_annual_lost_revenue_gbp"], 50000.0) # ~£84k lost

    def test_module3_wage_stress(self):
        service = LaborService(self.db)
        data = service.simulate_labor_inflation_stress(wage_increase_pct=6.7, price_offset_pct=2.0)
        self.assertGreater(data["summary"]["total_wage_cost_increase_gbp"], 0)
        self.assertGreater(data["summary"]["chain_avg_splh"], 20.0)

    def test_module4_waste_variance(self):
        service = WasteService(self.db)
        data = service.get_waste_variance()
        s10 = data["highlight_outlier"]
        self.assertIsNotNone(s10)
        self.assertEqual(s10["store_id"], "S10") # Hull Paragon
        self.assertGreater(s10["avg_waste_rate_pct"], 18.0) # ~20.7%
        self.assertEqual(s10["severity"], "CRITICAL")

    def test_module4_dynamic_par(self):
        service = WasteService(self.db)
        data = service.get_dynamic_par_recommendation(store_id="S10", day_of_week="Wednesday", weather_type="Rainy")
        self.assertEqual(len(data["recommendations"]), 3)
        self.assertGreater(data["summary"]["est_daily_waste_savings_gbp"], 0)

    def test_module4_early_stockouts(self):
        service = WasteService(self.db)
        data = service.get_early_stockouts("S06")
        self.assertEqual(data["store_id"], "S06")
        self.assertGreater(data["impact"]["annual_missed_revenue_gbp"], 10000.0)

    def test_module5_digital_health(self):
        service = DigitalService(self.db)
        data = service.get_app_version_health()
        self.assertLess(data["kpis"]["app_volume_collapse_pct"], -30.0)
        self.assertGreater(data["kpis"]["delivery_displacement_surge_pct"], 10.0)
        self.assertGreater(data["kpis"]["total_commission_bleed_gbp"], 10000.0)

    def test_module5_sentiment(self):
        service = DigitalService(self.db)
        data = service.get_sentiment_and_surcharge_tracker()
        self.assertGreater(len(data["keyword_clusters"]), 2)
        # Verify oat surcharge caused rating drop
        oat = data["oat_surcharge_impact"]
        self.assertGreater(oat["sentiment_rating_drop"], 1.5)

    def test_module6_candidate_sites(self):
        service = ExpansionService(self.db)
        data = service.evaluate_candidate_sites()
        sites = {s["site_id"]: s for s in data["candidate_sites"]}
        
        # CS3 Oxford Rd must be High / Priority Go
        self.assertIn("HIGH - PRIORITY", sites["CS3"]["recommendation"])
        # CS4 York Station must be High Risk / Reject
        self.assertIn("HIGH RISK", sites["CS4"]["recommendation"])

    def test_rbac_rules(self):
        ceo = PERSONAS["ceo_anna"]
        s07_mgr = PERSONAS["mgr_s07"]

        self.assertTrue(ceo.can_view_all_stores)
        self.assertFalse(s07_mgr.can_view_all_stores)
        self.assertEqual(s07_mgr.store_id, "S07")

        # Store access checks
        self.assertEqual(verify_store_access(ceo, "S10"), "S10")
        self.assertEqual(verify_store_access(s07_mgr, "S07"), "S07")
        with self.assertRaises(Exception):
            verify_store_access(s07_mgr, "S10")

if __name__ == "__main__":
    unittest.main()
