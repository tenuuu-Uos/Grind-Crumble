import uvicorn

if __name__ == "__main__":
    print("=" * 65)
    print("  Grind & Crumb Store Health Monitor")
    print("  12-Store Operations Dashboard (Store-First Unit)")
    print("=" * 65)
    print("  Running on: http://127.0.0.1:8000")
    print("  - Home (12 Store Cards Grid): http://127.0.0.1:8000/")
    print("  - Network Overview:           http://127.0.0.1:8000/network")
    print("  - Threshold Settings:         http://127.0.0.1:8000/settings")
    print("  - Upload Monthly CSVs:        http://127.0.0.1:8000/upload")
    print("=" * 65)
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
