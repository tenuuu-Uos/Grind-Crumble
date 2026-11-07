"""
Grind & Crumb Performance Pulse Dashboard Entry Point.
Run `python run.py` or `python Home.py` to start the application.
"""
from run import main if __name__ == '__main__' else None

if __name__ == "__main__":
    import uvicorn
    from app.db.etl import run_etl
    from app.config import DB_PATH

    if not DB_PATH.exists():
        run_etl()
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
