@echo off
cd /d "%~dp0"
echo Memasang kebutuhan (sekali saja, butuh internet)...
python -m pip install -q -r requirements.txt
echo.
echo Klaira berjalan di http://localhost:8000  (tutup jendela ini untuk berhenti)
start "" http://localhost:8000
python -m uvicorn klaira.main:app --port 8000
pause
