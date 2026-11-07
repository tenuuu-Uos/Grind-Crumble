import unittest
from starlette.requests import Request
from app.main import app, home_page, store_detail_page, network_page, settings_page, upload_page
from app.data_manager import DataManager
from app.config import get_settings, update_settings

def make_request(path: str = "/"):
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [],
        "query_string": b"",
        "app": app
    }
    return Request(scope)

class TestStoreHealthMonitor(unittest.TestCase):

    def test_12_stores_cards_generated(self):
        cards = DataManager.get_all_store_cards()
        self.assertEqual(len(cards), 12)
        store_ids = {c["store_id"] for c in cards}
        self.assertIn("S01", store_ids)
        self.assertIn("S07", store_ids)
        self.assertIn("S10", store_ids)

    def test_s07_manchester_piccadilly_card(self):
        cards = DataManager.get_all_store_cards()
        s07 = next((c for c in cards if c["store_id"] == "S07"), None)
        self.assertIsNotNone(s07)
        self.assertEqual(s07["rag_status"], "red")
        self.assertGreater(s07["occupancy_pct"], 35.0)
        self.assertIn("rent", s07["plain_alert"].lower())

    def test_s10_hull_paragon_card(self):
        cards = DataManager.get_all_store_cards()
        s10 = next((c for c in cards if c["store_id"] == "S10"), None)
        self.assertIsNotNone(s10)
        self.assertEqual(s10["rag_status"], "red")
        self.assertGreater(s10["waste_pct"], 18.0) # Hull Paragon ~20.9% - 21.5%
        self.assertIn("waste", s10["plain_alert"].lower())

    def test_single_store_detail(self):
        detail = DataManager.get_single_store_detail("S07")
        self.assertIsNotNone(detail)
        self.assertIn("pnl_waterfall", detail)
        self.assertIn("waste_trend", detail)
        self.assertIn("channel_mix", detail)
        self.assertIn("staffing_hours", detail)

        # Check P&L waterfall structure
        waterfall_labels = [item["label"] for item in detail["pnl_waterfall"]]
        self.assertIn("Total Sales (Net)", waterfall_labels)
        self.assertIn("Rent & Business Rates", waterfall_labels)
        self.assertIn("Net Store Operating Profit", waterfall_labels)

        # Check 12-month waste trend
        self.assertEqual(len(detail["waste_trend"]), 12)

        # Check Channel Mix
        self.assertEqual(len(detail["channel_mix"]["labels"]), 3)

        # Check Staffing hours
        self.assertEqual(len(detail["staffing_hours"]), 3)

    def test_settings_persistence(self):
        original = get_settings()["waste_benchmark_pct"]
        update_settings({"waste_benchmark_pct": 8.8})
        self.assertEqual(get_settings()["waste_benchmark_pct"], 8.8)
        # Restore
        update_settings({"waste_benchmark_pct": original})

    def test_home_page_template(self):
        req = make_request("/")
        resp = home_page(req)
        self.assertEqual(resp.status_code, 200)
        body = resp.body.decode("utf-8")
        self.assertIn("Store Locations", body)
        self.assertIn("Manchester Piccadilly", body)
        self.assertIn("Hull Paragon", body)

    def test_store_detail_template(self):
        req = make_request("/store/S07")
        resp = store_detail_page(req, "S07")
        self.assertEqual(resp.status_code, 200)
        body = resp.body.decode("utf-8")
        self.assertIn("Store Profit Breakdown", body)
        self.assertIn("Lunchtime Staffing", body)

    def test_network_page_template(self):
        req = make_request("/network")
        resp = network_page(req)
        self.assertEqual(resp.status_code, 200)
        body = resp.body.decode("utf-8")
        self.assertIn("Network Scoreboard", body)
        self.assertIn("scoreboardTable", body)

    def test_new_store_page_and_creation(self):
        from app.main import new_store_page
        req = make_request("/stores/new")
        resp = new_store_page(req)
        self.assertEqual(resp.status_code, 200)
        body = resp.body.decode("utf-8")
        self.assertIn("Add New Store Location", body)

    def test_settings_page_template(self):
        req = make_request("/settings")
        resp = settings_page(req)
        self.assertEqual(resp.status_code, 200)
        body = resp.body.decode("utf-8")
        self.assertIn("Threshold Settings", body)

    def test_upload_page_template(self):
        req = make_request("/upload")
        resp = upload_page(req)
        self.assertEqual(resp.status_code, 200)
        body = resp.body.decode("utf-8")
        self.assertIn("Upload Data &amp; AI Analysis", body)

if __name__ == "__main__":
    unittest.main()
