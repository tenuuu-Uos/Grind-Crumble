import uvicorn
from app.db.etl import run_etl
from app.config import DB_PATH

if __name__ == "__main__":
    if not DB_PATH.exists():
        print("Database not found. Running ETL pipeline to initialize grind_and_crumb.db...")
        run_etl()
        print("Database initialized.")
        
    print("Starting Grind & Crumb Performance Pulse Web Application...")
    print("Open http://127.0.0.1:8000 in your browser.")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
