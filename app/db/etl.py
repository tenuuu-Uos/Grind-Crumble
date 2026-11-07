import os
import time
import sqlite3
import pandas as pd
from pathlib import Path
from app.config import DATA_DIR, DB_PATH, CHAIN_BENCHMARKS

def run_etl(db_path: Path = DB_PATH, data_dir: Path = DATA_DIR, force: bool = False) -> dict:
    """
    Ingests all raw CSVs into SQLite database and builds optimized views and indexes.
    Returns metadata about the ETL process (row counts, duration, status).
    """
    start_time = time.time()
    results = {}
    
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found at {data_dir}")
        
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    
    csv_mappings = [
        ("stores.csv", "stores"),
        ("products.csv", "products"),
        ("starter_store_monthly_pnl.csv", "store_monthly_pnl_raw"),
        ("daily_store_sales.csv", "daily_store_sales"),
        ("store_costs_monthly.csv", "store_costs_monthly"),
        ("store_catchment.csv", "store_catchment"),
        ("candidate_sites.csv", "candidate_sites"),
        ("footfall.csv", "footfall"),
        ("staff_rota_weekly.csv", "staff_rota_weekly"),
        ("staff_monthly.csv", "staff_monthly"),
        ("staff_exit_survey.csv", "staff_exit_survey"),
        ("waste_log.csv", "waste_log"),
        ("weather.csv", "weather"),
        ("customer_reviews.csv", "customer_reviews"),
        ("customer_survey.csv", "customer_survey"),
        ("promotions.csv", "promotions"),
        ("business_events.csv", "business_events"),
        ("delivery_partner_terms.csv", "delivery_partner_terms"),
        ("capex.csv", "capex"),
        ("transactions.csv", "transactions"),
        ("transaction_lines.csv", "transaction_lines"),
    ]
    
    for filename, table_name in csv_mappings:
        file_path = data_dir / filename
        if not file_path.exists():
            continue
            
        t0 = time.time()
        # Read CSV with pandas
        df = pd.read_csv(file_path)
        
        # Save into SQLite
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        results[table_name] = {
            "rows": len(df),
            "columns": list(df.columns),
            "load_time_sec": round(time.time() - t0, 3)
        }

    # Create Indexes for lightning fast queries (<800ms SRS requirement)
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_tx_store_time ON transactions (store_id, timestamp);",
        "CREATE INDEX IF NOT EXISTS idx_tx_channel ON transactions (channel);",
        "CREATE INDEX IF NOT EXISTS idx_tx_partner ON transactions (delivery_partner);",
        "CREATE INDEX IF NOT EXISTS idx_tx_net_gbp ON transactions (net_gbp);",
        "CREATE INDEX IF NOT EXISTS idx_tx_lines_receipt ON transaction_lines (receipt_id);",
        "CREATE INDEX IF NOT EXISTS idx_tx_lines_prod ON transaction_lines (product_id);",
        "CREATE INDEX IF NOT EXISTS idx_waste_date_store ON waste_log (date, store_id);",
        "CREATE INDEX IF NOT EXISTS idx_waste_category ON waste_log (category);",
        "CREATE INDEX IF NOT EXISTS idx_footfall_date_store ON footfall (date, store_id, daypart);",
        "CREATE INDEX IF NOT EXISTS idx_sales_date_store ON daily_store_sales (date, store_id);",
        "CREATE INDEX IF NOT EXISTS idx_reviews_date ON customer_reviews (review_date);",
        "CREATE INDEX IF NOT EXISTS idx_pnl_store_month ON store_monthly_pnl_raw (store_id, month);"
    ]
    
    for idx_sql in indexes:
        conn.execute(idx_sql)
        
    # Create required SQL Views
    # 1. vw_store_monthly_pnl: enriched with fixed occupancy %, alert flags, and prime costs
    conn.execute("DROP VIEW IF EXISTS vw_store_monthly_pnl;")
    conn.execute("""
    CREATE VIEW vw_store_monthly_pnl AS
    SELECT 
        p.*,
        (p.rent_gbp + p.business_rates_gbp) AS fixed_occupancy_cost_gbp,
        ROUND(((p.rent_gbp + p.business_rates_gbp) / NULLIF(p.total_sales_gbp, 0)) * 100.0, 2) AS fixed_occupancy_pct,
        CASE 
            WHEN ((p.rent_gbp + p.business_rates_gbp) / NULLIF(p.total_sales_gbp, 0)) > 0.25 THEN 1 
            ELSE 0 
        END AS fixed_occupancy_alert,
        (p.food_cost_gbp + p.labour_cost_gbp) AS prime_cost_gbp,
        ROUND(((p.food_cost_gbp + p.labour_cost_gbp) / NULLIF(p.total_sales_gbp, 0)) * 100.0, 2) AS prime_cost_pct,
        CASE 
            WHEN p.waste_rate > 0.09 THEN 1 
            ELSE 0 
        END AS waste_rate_alert
    FROM store_monthly_pnl_raw p;
    """)

    # 2. vw_delivery_economics: detailed delivery economics view
    conn.execute("DROP VIEW IF EXISTS vw_delivery_economics;")
    conn.execute("""
    CREATE VIEW vw_delivery_economics AS
    SELECT 
        t.receipt_id,
        t.store_id,
        t.timestamp,
        SUBSTR(t.timestamp, 1, 10) AS order_date,
        SUBSTR(t.timestamp, 1, 7) AS order_month,
        SUBSTR(t.timestamp, 12, 2) AS order_hour,
        t.delivery_partner,
        t.gross_gbp,
        t.discount_gbp,
        t.net_gbp,
        CASE WHEN t.net_gbp < 8.0 THEN 1 ELSE 0 END AS is_sub_8,
        CASE 
            WHEN t.delivery_partner = 'RushEats' THEN 0.30
            WHEN t.delivery_partner = 'Dashly' AND t.timestamp < '2026-04-01' THEN 0.27
            WHEN t.delivery_partner = 'Dashly' AND t.timestamp >= '2026-04-01' THEN 0.33
            ELSE 0.30
        END AS commission_rate,
        ROUND(t.net_gbp * (
            CASE 
                WHEN t.delivery_partner = 'RushEats' THEN 0.30
                WHEN t.delivery_partner = 'Dashly' AND t.timestamp < '2026-04-01' THEN 0.27
                WHEN t.delivery_partner = 'Dashly' AND t.timestamp >= '2026-04-01' THEN 0.33
                ELSE 0.30
            END
        ), 2) AS commission_gbp,
        0.45 AS packaging_cost_gbp,
        -- 4 min labor @ approx £12.40/hr * 1.13 = ~£0.93 per order
        0.93 AS labor_packing_cost_gbp,
        ROUND(t.net_gbp * 0.28, 2) AS est_food_cost_gbp,
        ROUND(t.net_gbp - (
            t.net_gbp * (
                CASE 
                    WHEN t.delivery_partner = 'RushEats' THEN 0.30
                    WHEN t.delivery_partner = 'Dashly' AND t.timestamp < '2026-04-01' THEN 0.27
                    WHEN t.delivery_partner = 'Dashly' AND t.timestamp >= '2026-04-01' THEN 0.33
                    ELSE 0.30
                END
            ) + 0.45 + 0.93 + (t.net_gbp * 0.28)
        ), 2) AS net_contribution_gbp
    FROM transactions t
    WHERE t.channel = 'Delivery';
    """)

    conn.commit()
    conn.close()
    
    total_duration = round(time.time() - start_time, 2)
    return {
        "status": "success",
        "duration_seconds": total_duration,
        "tables": results
    }

if __name__ == "__main__":
    print("Running ETL pipeline...")
    res = run_etl()
    print(f"ETL completed in {res['duration_seconds']}s")
    for tbl, meta in res["tables"].items():
        print(f"  - {tbl}: {meta['rows']} rows loaded in {meta['load_time_sec']}s")
