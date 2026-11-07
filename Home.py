"""
Grind & Crumb Store Health Monitor
Run `python run.py` or `python Home.py` to start the web dashboard.
"""
import uvicorn

if __name__ == "__main__":
    print("Starting Grind & Crumb Store Health Monitor on http://127.0.0.1:8000 ...")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
