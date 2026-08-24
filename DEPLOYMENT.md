# Deployment auf einem Raspberry Pi (Docker + SQLite)

Die App läuft auf dem Raspberry Pi als **zwei Container** (Backend, Frontend) und
wird mit `docker-compose.yml` gestartet. Das Backend nutzt **SQLite** als
Datenbank (kein DB-Container – ideal für den 1-GB-Pi); die Daten liegen dauerhaft
im Docker-Volume `abrechnung-data`.

> **Warum SQLite statt PostgreSQL?** Der Pi läuft mit 32-bit (ARMv7); das
> offizielle `postgres:16`-Image gibt es dafür nicht. SQLite wird von der App
> vollständig unterstützt (alle Tests laufen auf SQLite) und verbraucht deutlich
> weniger RAM – wichtig auf einem 1-GB-Pi.

## Voraussetzungen

- Raspberry Pi (hier: Pi 4 mit 1 GB, Raspbian Bullseye 32-bit)
- SSH-Zugang als Benutzer mit sudo-Rechten (z. B. `admin`)
- Docker installiert (siehe Schritt 1)

## Schritt 0: SSH-Zugang (falls unbekannt)

Falls keine Zugangsdaten bekannt sind: SD-Karte ausbauen, am PC per WSL2
+ USB/IP einbinden und einen Benutzer mit bekanntem Passwort + SSH-Key anlegen
(so durchgeführt: Benutzer `admin`, UID 1001, sudo-Gruppe, Key in
`/home/admin/.ssh/authorized_keys`).

## Schritt 1: Docker installieren

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker admin
# danach neu anmelden, damit die docker-Gruppe greift
```

## Schritt 2: Projekt auf den Pi kopieren

```bash
scp -r backend frontend docker-compose.yml .env.example \
  admin@192.168.0.126:/home/admin/abrechnung/
```

## Schritt 3: .env anlegen

```bash
cd /home/admin/abrechnung
cp .env.example .env
# VITE_API_URL muss die vom Browser erreichbare Backend-URL sein:
#   VITE_API_URL=http://192.168.0.126:8000
```

## Schritt 4: Container bauen und starten

```bash
cd /home/admin/abrechnung
docker compose up -d --build
```

> Tipp für 1-GB-Pi: Vor dem ersten Build den Swap vergrößern, damit der
> Frontend-Build nicht an Speichermangel scheitert, z. B.:
> `sudo dphys-swapfile swapoff && sudo sed -i 's/^CONF_SWAPSIZE=.*/CONF_SWAPSIZE=1024/' /etc/dphys-swapfile && sudo dphys-swapfile setup && sudo dphys-swapfile swapon`

## Zugriff

| Komponente | URL |
|---|---|
| Frontend (Web-App) | `http://192.168.0.126:8080` |
| Backend-API | `http://192.168.0.126:8000` |

## Wichtige Hinweise

- **Datenbank:** SQLite-Datei `/data/abrechnung.db` im Volume `abrechnung-data`.
  Für ein Backup:
  ```bash
  docker cp abrechnung-backend:/data/abrechnung.db ./abrechnung_backup.db
  ```
- **Migration:** Der Backend-Container führt beim Start automatisch
  `alembic upgrade head` aus – ein Update der App migriert die DB selbst.
- **Updates:** Neuen Stand per `git pull`/Kopie einspielen, dann
  `docker compose up -d --build`.
- **emlog unberührt:** Der Pi läuft weiter auf Port 80 (lighttpd/emlog); Backend
  (8000) und Frontend (8080) kollidieren damit nicht.
- **Strom-/Wasser-/Rechnungs-Referenz-Excel-Dateien** (`*.xlsx` im Projektordner)
  werden nicht mit deployt/versioniert.

## Fehlerbehebung

- **Frontend findet API nicht:** `VITE_API_URL` in `.env` prüfen und Frontend neu
  bauen (`docker compose build frontend`).
- **Backend startet nicht / DB-Fehler:** Logs ansehen:
  ```bash
  docker compose logs backend
  ```
- **Container bauen ist langsam/abbruch:** Swap vergrößern (siehe Schritt 4) und
  erneut `docker compose build frontend` ausführen.
