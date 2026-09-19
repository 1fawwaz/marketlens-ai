@echo off
setlocal
cd /d "%~dp0.."

echo === MarketLens AI Startup ===

echo [1/5] Installing Python dependencies...
pip install -r requirements.txt -q

echo [2/5] Setting up database schema...
python scripts/setup_db.py

echo [3/5] Loading raw CSV ETL...
python scripts/etl/load_data.py

echo [4/5] Running ML pipeline + RAG ingest...
python -m backend.app.ml.pipeline
python -m backend.app.rag.search

echo [5/5] Running tests...
pytest tests/ -q

echo.
echo Start backend:  uvicorn backend.app.main:app --reload --port 8000
echo Start frontend: cd frontend && npm install && npm run dev
endlocal
