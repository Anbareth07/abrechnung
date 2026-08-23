# Startet das Backend mit der ECHTEN Datenbank (real.db).
# Hier gehören deine realen Nutzerdaten hinein – diese Datei wird nicht von
# den Entwicklungstests des Assistenten verändert.
$env:DATABASE_URL = "sqlite:///c:/Users/tfran/Projects/Abrechnung/backend/real.db"
c:\Users\tfran\Projects\Abrechnung\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir c:\Users\tfran\Projects\Abrechnung\backend --port 8000
