# Startet das Backend mit der TEST-Datenbank (dev.db).
# Diese Datenbank enthält Seed-/Testdaten und wird vom Assistenten für
# Feature-Entwicklung und Tests verwendet – sie darf frei verändert werden.
$env:DATABASE_URL = "sqlite:///c:/Users/tfran/Projects/Abrechnung/backend/dev.db"
c:\Users\tfran\Projects\Abrechnung\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir c:\Users\tfran\Projects\Abrechnung\backend --port 8000
