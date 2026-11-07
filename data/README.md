# Grind & Crumb data pack

Fictional data for a 12-store café chain, 1 July 2025 to 30 June 2026. Read the client brief first.

**Important:** `transactions.csv` and `transaction_lines.csv` are a random 10% sample of all receipts. Use `daily_store_sales.csv` for total sales. Money is in GBP, net of VAT.

## Keys
`store_id` (S01-S12) · `product_id` (P01-P38) · `receipt_id` · `customer_id` · `date` · `city`

## Files and columns

**stores.csv** — store_id, store_name, city, format (Flagship/Standard/Kiosk), location_type, opened_date, sqft, seats, rent_gbp_month, store_manager, refit_year (blank = never refitted)

**products.csv** — product_id, product_name, category, menu_price_gbp (in-store/app), unit_cost_gbp (ingredients + packaging), milk_based (1 = milk choice applies), delivery_price_gbp, available_from / available_to (blank = all year)

**transactions.csv** (10% sample) — receipt_id, store_id, timestamp, channel (In-store / App Click & Collect / Delivery), delivery_partner, customer_id (blank = not a loyalty member or not scanned), payment_method, n_lines, gross_gbp, discount_gbp, net_gbp

**transaction_lines.csv** (10% sample) — receipt_id, line_no, product_id (`MEALDEAL` = meal deal bundle discount line), qty, unit_price_gbp (delivery orders use delivery prices), milk_option (Dairy/Oat/Skimmed, blank if not milk-based), modifier_gbp (e.g. oat surcharge), line_discount_gbp, line_total_gbp

**daily_store_sales.csv** (full totals) — date, store_id, receipts_instore, receipts_app, receipts_delivery, net_sales_instore_gbp, net_sales_app_gbp, net_sales_delivery_gbp

**footfall.csv** — date, store_id, daypart (Morning 07-11, Lunch 11-14, Afternoon 14-18), door_count (people entering)

**weather.csv** — date, city, temp_max_c, temp_min_c, rainfall_mm

**loyalty_customers.csv** — customer_id, signup_date, home_store_id, age_band, signup_channel, marketing_opt_in

**staff_rota_weekly.csv** — week_start (Monday), store_id, daypart, scheduled_hours, avg_hourly_wage_gbp

**staff_monthly.csv** — month, store_id, headcount, leavers, new_starters, staff_survey_score_10

**waste_log.csv** — date, store_id, category, units_prepared, units_wasted, est_cost_wasted_gbp

**store_costs_monthly.csv** — month, store_id, rent_gbp, business_rates_gbp, utilities_gbp, repairs_maintenance_gbp, other_opex_gbp (labour is in the rota; food cost comes from products)

**capex.csv** — store_id, month, description, capex_gbp

**promotions.csv** — promo_id, promo_name, mechanic, start_date, end_date, stores (semicolon-separated, or All), category, marketing_spend_gbp

**delivery_partner_terms.csv** — partner, valid_from, valid_to, commission_rate (share of order value), packaging_cost_per_order_gbp, notes

**customer_reviews.csv** — review_id, review_date, source, store_name_raw (as typed by the reviewer, no store_id), rating (1-5), review_text

**store_catchment.csv** — store_id, daily_footfall_street, office_workers_500m, students_1km, median_household_income_gbp, competitor_cafes_500m, area_vibrancy_index_10

**candidate_sites.csv** — site_id, site_name, city, location_type, sqft, quoted_rent_gbp_month, same catchment fields as above, est_fitout_gbp

**business_events.csv** — event, date, description

## Cost assumptions (use these)
- Labour cost = scheduled_hours × avg_hourly_wage_gbp × 1.13
- Delivery: platform commission on order value, plus packaging cost per order, plus ~4 minutes of staff time per order
- Ignore head office costs and tax
