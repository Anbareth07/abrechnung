# Backend-Container für den Raspberry Pi (32-bit ARMv7)
FROM python:3.13-slim

WORKDIR /app

# Build-Abhängigkeiten für native Pakete (Pillow via reportlab; auf ARMv7 gibt
# es dafür keine Wheels, daher Quell-Build mit libjpeg/zlib/freetype)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc build-essential libjpeg-dev zlib1g-dev libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

# Backend-Quellcode kopieren (inkl. pyproject.toml, alembic, app)
COPY . .

# Paket + Abhängigkeiten installieren (openpyxl, reportlab, fastapi, ...)
RUN pip install --no-cache-dir .

# Beim Start: DB-Migrationen anwenden, dann uvicorn starten.
# DATABASE_URL kommt aus der docker-compose.yml (persistente SQLite-Datei auf dem Volume).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
