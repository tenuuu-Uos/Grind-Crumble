import sys
import unittest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestGrindAndCrumbApp(unittest.TestCase):

    def test_health_check(self):
        res = client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")

    def test_dashboard_ui(self):
        res = client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Grind & Crumb", res.text)
        self.assertIn("Pulse Intelligence", res.text)

    def test_ipad_counter_ui(self):
        res = client.get("/ipad")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Shift Command Terminal", res.text)

    def test_pnl_ranking_module1(self):
        res = client.get("/api/pnl/ranking")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        stores = data["stores"]
        self.assertGreaterEqual(len(stores), 12)
        
        # Check Manchester Piccadilly S07 is identified as high volume loss maker
        s07 = next((s for s in stores if s["store_id"] == "S07"), None)
        self.assertIsNotNone(s07)
        self.assertTrue(s07["is_high_volume_loss_maker"])
        self.assertLess(s07["net_profit_gbp"], 0)
        self.assertGreater(s07["fixed_occupancy_pct"], 25.0)

    def test_fixed_occupancy_alerts(self):
        res = client.get("/api/pnl/occupancy-alerts")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(len(data["alerts"]), 1)
        # S07 should have critical alert
        s07_alert = next((a for a in data["alerts"] if a["store_id"] == "S07"), None)
        self.assertIsNotNone(s07_alert)
        self.assertGreater(s07_alert["occupancy_pct"], 40.0)

    def test_cannibalization_audit(self):
        res = client.get("/api/pnl/cannibalization")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("timeline", data)
        self.assertIn("metrics", data)
        self.assertGreater(data["metrics"]["s03_monthly_sales_dilution_gbp"], 0)

    def test_delivery_waterfall_module2(self):
        res = client.get("/api/delivery/waterfall")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(len(data["channels"]), 4)

    def test_delivery_sub8_alarm(self):
        res = client.get("/api/delivery/sub8-alarm")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreater(data["sub8_pct"], 25.0)
        self.assertEqual(data["peak_impact"]["alarm_status"], "CRITICAL")

    def test_delivery_simulation(self):
        res = client.post("/api/delivery/simulate", json={
            "markup_pct": 18.0,
            "apply_min_basket_8": True,
            "volume_elasticity": -0.3
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreater(data["impact"]["annualized_chain_profit_recovery_gbp"], 0)

    def test_labor_bottlenecks_module3(self):
        res = client.get("/api/labor/bottlenecks")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(len(data["stores"]), 12)
        s07 = next((s for s in data["stores"] if s["store_id"] == "S07"), None)
        self.assertEqual(s07["bottleneck_severity"], "CRITICAL")
        self.assertGreater(s07["staffing_deficit"], 1.0)

    def test_labor_walkout_loss(self):
        res = client.get("/api/labor/walkouts")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreater(data["total_annual_lost_revenue_gbp"], 50000.0)

    def test_waste_variance_module4(self):
        res = client.get("/api/waste/variance")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        s10 = next((s for s in data["stores"] if s["store_id"] == "S10"), None)
        self.assertIsNotNone(s10)
        self.assertGreater(s10["avg_waste_rate_pct"], 18.0) # Hull Paragon ~20.7%

    def test_dynamic_par(self):
        res = client.get("/api/waste/dynamic-par?store_id=S10&day_of_week=Wednesday&weather=Rainy")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(len(data["recommendations"]), 3)

    def test_stockout_monitor(self):
        res = client.get("/api/waste/stockouts?store_id=S06")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["store_id"], "S06")
        self.assertEqual(data["stockout_threshold_time"], "13:30")

    def test_digital_app_health_module5(self):
        res = client.get("/api/digital/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("timeline", data)
        self.assertIn("kpis", data)
        self.assertLess(data["kpis"]["app_volume_collapse_pct"], -30.0) # ~43% collapse

    def test_digital_sentiment(self):
        res = client.get("/api/digital/sentiment")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("keyword_clusters", data)
        self.assertIn("oat_surcharge_impact", data)

    def test_candidate_site_scorer_module6(self):
        res = client.get("/api/expansion/candidate-sites")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        sites = data["candidate_sites"]
        self.assertEqual(len(sites), 7)
        
        # Verify CS3 is top choice & CS4 is high risk
        cs3 = next((s for s in sites if s["site_id"] == "CS3"), None)
        cs4 = next((s for s in sites if s["site_id"] == "CS4"), None)
        self.assertIsNotNone(cs3)
        self.assertIsNotNone(cs4)
        self.assertIn("HIGH - PRIORITY", cs3["recommendation"])
        self.assertIn("HIGH RISK", cs4["recommendation"])

    def test_rbac_store_manager_restriction(self):
        # Switching to Ollie Brent (Store Manager S07)
        res = client.get("/api/pnl/ranking?user_id=mgr_s07")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["is_restricted_view"])
        self.assertEqual(len(data["stores"]), 1)
        self.assertEqual(data["stores"][0]["store_id"], "S07")

        # Attempt to access S10 data as S07 manager should be forbidden 403
        forbidden_res = client.get("/api/pnl/ranking?user_id=mgr_s07&store_id=S10")
        self.assertEqual(forbidden_res.status_code, 403)

if __name__ == "__main__":
    unittest.main()
