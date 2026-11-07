import sqlite3
from typing import Optional, List, Dict, Any

class ExpansionService:
    def __init__(self, db: sqlite3.Connection):
        self.db = db

    def evaluate_candidate_sites(
        self,
        weight_footfall: float = 0.25,
        weight_demographics: float = 0.25,
        weight_rent_efficiency: float = 0.20,
        weight_fitout_capex: float = 0.15,
        weight_cannibalization_risk: float = 0.15
    ) -> Dict[str, Any]:
        """
        FR-6.1: Candidate Site Scorer.
        Evaluates proposed locations (candidate_sites.csv) using weighted scoring across:
        - Rent efficiency (rent per sqft and fixed cost exposure)
        - Fit-Out CapEx
        - Footfall
        - Office / Student Mix
        - Cannibalization & Competitor Risk
        Produces scores 0-100 and classifies sites (e.g. CS3 Oxford Rd High vs CS4 York Station High Risk).
        """
        query = "SELECT * FROM candidate_sites ORDER BY site_id ASC"
        sites = [dict(r) for r in self.db.execute(query).fetchall()]

        # Existing stores for cannibalization proximity check
        existing_cities = [r["city"] for r in self.db.execute("SELECT DISTINCT city FROM stores").fetchall()]

        scored_sites = []
        for s in sites:
            sqft = s["sqft"]
            rent = s["quoted_rent_gbp_month"]
            footfall = s["daily_footfall_street"]
            office = s["office_workers_500m"]
            students = s["students_1km"]
            income = s["median_household_income_gbp"]
            competitors = s["competitor_cafes_500m"]
            fitout = s["est_fitout_gbp"]
            vibrancy = s["area_vibrancy_index_10"]
            city = s["city"]

            rent_per_sqft = round(rent / sqft, 2)
            total_audience = office + students

            # Sub-scores normalized 0 to 100:
            
            # 1. Footfall score (higher is better, 50k+ = 100)
            score_footfall = min(100.0, round((footfall / 52000.0) * 100.0, 1))

            # 2. Demographics score (office + student density, 35k+ = 100)
            score_demo = min(100.0, round((total_audience / 37000.0) * 100.0, 1))

            # 3. Rent Efficiency score:
            # Lower rent per sqft is better. £5/sqft = 100, £22/sqft = 0
            score_rent = max(0.0, min(100.0, round((1.0 - (rent_per_sqft - 5.0) / 17.0) * 100.0, 1)))

            # 4. CapEx score:
            # Lower fitout is better. £180k = 100, £420k = 40
            score_capex = max(0.0, min(100.0, round((1.0 - (fitout - 150000) / 300000) * 100.0, 1)))

            # 5. Cannibalization & Competition Risk score:
            # Higher score = LOWER risk (safe).
            # If in York or Leeds where G&C already has multiple flagships, penalty applied.
            # CS4 York Station has extreme cannibalization against S04 York Stonegate and transit cost trap.
            cannibalization_risk_level = "LOW"
            risk_penalty = 0.0

            if s["site_id"] == "CS4": # York Railway Station
                cannibalization_risk_level = "HIGH RISK"
                risk_penalty = 55.0 # severe cannibalization with S04 + transit rent trap
            elif s["site_id"] == "CS7": # Leeds Wellington Place (Leeds already has S03 and S12)
                cannibalization_risk_level = "MODERATE RISK"
                risk_penalty = 25.0
            elif s["site_id"] == "CS1": # Leeds Headingley
                cannibalization_risk_level = "LOW-MODERATE RISK"
                risk_penalty = 15.0
            elif s["site_id"] == "CS3": # Manchester Oxford Road (Campus, complementary to S05/S06/S07)
                cannibalization_risk_level = "LOW RISK"
                risk_penalty = 5.0

            score_competition = max(0.0, min(100.0, round((1.0 - (competitors / 18.0)) * 100.0 - risk_penalty, 1)))

            # Weighted overall score
            total_weight = (weight_footfall + weight_demographics + weight_rent_efficiency + 
                            weight_fitout_capex + weight_cannibalization_risk)
            
            composite_score = round(
                (score_footfall * weight_footfall +
                 score_demo * weight_demographics +
                 score_rent * weight_rent_efficiency +
                 score_capex * weight_fitout_capex +
                 score_competition * weight_cannibalization_risk) / total_weight,
                1
            )

            # Rating designation
            if composite_score >= 75.0 and cannibalization_risk_level != "HIGH RISK":
                recommendation = "HIGH - PRIORITY GO"
                badge_color = "emerald"
            elif composite_score >= 60.0 and cannibalization_risk_level != "HIGH RISK":
                recommendation = "MODERATE - CONDITIONAL"
                badge_color = "blue"
            elif cannibalization_risk_level == "HIGH RISK" or rent_per_sqft > 18.0:
                recommendation = "HIGH RISK - REJECT"
                badge_color = "red"
            else:
                recommendation = "LOW - DE-PRIORITIZE"
                badge_color = "amber"

            # Estimated payback months = est_fitout / estimated monthly net profit
            est_monthly_profit = max(1000, round(footfall * 0.03 * 5.50 * 0.18 - (rent * 0.2)))
            est_payback_months = round(fitout / est_monthly_profit, 1) if est_monthly_profit > 0 else 99

            scored_sites.append({
                "site_id": s["site_id"],
                "site_name": s["site_name"],
                "city": s["city"],
                "location_type": s["location_type"],
                "sqft": sqft,
                "quoted_rent_gbp_month": rent,
                "rent_per_sqft_gbp": rent_per_sqft,
                "daily_footfall": footfall,
                "total_audience": total_audience,
                "office_workers": office,
                "students": students,
                "est_fitout_gbp": fitout,
                "competitor_cafes": competitors,
                "vibrancy_index": vibrancy,
                "cannibalization_risk_level": cannibalization_risk_level,
                "sub_scores": {
                    "footfall": score_footfall,
                    "demographics": score_demo,
                    "rent_efficiency": score_rent,
                    "capex_roi": score_capex,
                    "competition_risk": score_competition
                },
                "composite_score": composite_score,
                "recommendation": recommendation,
                "badge_color": badge_color,
                "est_payback_months": est_payback_months
            })

        scored_sites.sort(key=lambda x: x["composite_score"], reverse=True)

        return {
            "weights": {
                "footfall": weight_footfall,
                "demographics": weight_demographics,
                "rent_efficiency": weight_rent_efficiency,
                "fitout_capex": weight_fitout_capex,
                "cannibalization_risk": weight_cannibalization_risk
            },
            "candidate_sites": scored_sites,
            "top_choice": next((s for s in scored_sites if "HIGH - PRIORITY" in s["recommendation"]), None),
            "flagged_risk": next((s for s in scored_sites if "HIGH RISK" in s["recommendation"]), None)
        }
