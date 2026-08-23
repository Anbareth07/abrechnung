# Nebenkostenabrechnung

Web-App zur automatisierten Erstellung von Nebenkostenabrechnungen für zwei Immobilien:

- **Objekt 1** – verbrauchsbasierte Wasserabrechnung über Zählerstände
- **Objekt 2** – flächenbasierte Abrechnung + Techem-Datenaufbereitung (Heizkosten separat)

## Stack

- Backend: Python 3.12+, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2
- Datenbank: PostgreSQL 16 (Docker Compose)
- Frontend: React + Vite + TypeScript
- PDF: WeasyPrint (Phase 5)

## Projektstruktur

```
docker-compose.yml     # PostgreSQL
backend/               # FastAPI-App (Models, Services, API, Alembic, Tests)
frontend/              # React-SPA (Phase 4)
```

## Schnellstart (Backend)

```powershell
# 1. Datenbank starten
docker compose up -d db

# 2. Umgebung vorbereiten (im Ordner backend/)
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

# 3. Konfiguration
Copy-Item ..\.env.example .env        # ggf. DSN anpassen

# 4. Migrationen anwenden
alembic upgrade head

# 5. Seed-Daten laden (Objekte, Kostenarten, Umlageschlüssel, Mieter)
python -m seed

# 6. API starten
uvicorn app.main:app --reload
```

API-Doku: http://localhost:8000/docs

## Tests

```powershell
cd backend
pytest
```

Die Tests laufen ohne PostgreSQL (SQLite in-memory für Modell-/Engine-Tests).
