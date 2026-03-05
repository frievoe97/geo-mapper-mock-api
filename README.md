# Geo Mapper Mock API

Einfache Demo-API, die Dateien aus `geodata_clean` als Download bereitstellt.

Die API unterscheidet:
- Typen: `nuts`, `lau`, `lor`
- Formate: `csv`, `geojson`
- Versionen: z. B. `2003`, `2010`, `2024`
- Level (falls vorhanden, z. B. bei NUTS): `0`, `1`, `2`, `3`

## Projektstruktur

```text
.
├── app/
│   ├── __init__.py
│   ├── catalog.py
│   └── main.py
├── geodata_clean/
└── requirements.txt
```

## API-Endpunkte

1. `GET /health`
Status + Anzahl indexierter Dateien.

2. `GET /api/v1/meta`
Metadaten zu verfuegbaren Typen/Formaten/Versionen.

3. `GET /api/v1/catalog`
Liefert alle Dateien als Katalog (JSON), optional gefiltert:
- `type` (`nuts|lau|lor`)
- `format` (`csv|geojson`)
- `version` (z. B. `2024`)
- `level` (z. B. `2`)
- `filename` (exakter Dateiname)

4. `GET /api/v1/versions/<type>/<format>`
Zeigt verfuegbare Versionen + Levels fuer eine Kombination.

5. `GET /api/v1/data/<type>/<format>/<version>`
Laedt genau eine Datei herunter.
Optionale Query-Parameter:
- `level` (wichtig bei NUTS)
- `filename`

Wenn mehrere Dateien matchen (z. B. NUTS ohne `level`), liefert die API `409` mit einer Trefferliste.

## Lokal starten

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
HOST=0.0.0.0 PORT=8080 python3 -m app.main
```

Danach ist die API unter `http://<server-ip>:8080` erreichbar.

## Beispiele mit curl

```bash
# Healthcheck
curl http://127.0.0.1:8080/health

# Verfuegbare NUTS-CSV-Versionen
curl http://127.0.0.1:8080/api/v1/versions/nuts/csv

# Katalog: NUTS GeoJSON 2024
curl "http://127.0.0.1:8080/api/v1/catalog?type=nuts&format=geojson&version=2024"

# Datei herunterladen (NUTS, CSV, Version 2024, Level 2)
curl -L "http://127.0.0.1:8080/api/v1/data/nuts/csv/2024?level=2" -o nuts_2024_level_2.csv

# Datei herunterladen (LAU, GeoJSON, Version 2024)
curl -L "http://127.0.0.1:8080/api/v1/data/lau/geojson/2024" -o lau_2024.geojson
```

## Deployment auf Debian VM

### 1. Pakete installieren

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
```

### 2. Projekt auf die VM bringen

Zum Beispiel per `git clone` oder `scp` in:

```text
/opt/geo-mapper-mock-api
```

### 3. Virtuelle Umgebung + Abhaengigkeiten

```bash
cd /opt/geo-mapper-mock-api
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Manuell testen

```bash
HOST=0.0.0.0 PORT=8080 .venv/bin/python -m app.main
```

In einer zweiten Shell:

```bash
curl http://127.0.0.1:8080/health
```

### 5. Als systemd-Service betreiben

Datei erstellen: `/etc/systemd/system/geo-mapper-mock-api.service`

```ini
[Unit]
Description=Geo Mapper Mock API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/geo-mapper-mock-api
Environment=HOST=0.0.0.0
Environment=PORT=8080
ExecStart=/opt/geo-mapper-mock-api/.venv/bin/python -m app.main
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Service aktivieren:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now geo-mapper-mock-api
sudo systemctl status geo-mapper-mock-api
```

Logs ansehen:

```bash
sudo journalctl -u geo-mapper-mock-api -f
```

### 6. Firewall (falls aktiv)

```bash
sudo ufw allow 8080/tcp
```

## Hinweise

- Datenpfad ist standardmaessig `./geodata_clean`.
- Optional kannst du einen anderen Pfad setzen:

```bash
DATA_ROOT=/mein/pfad/zu/geodata_clean HOST=0.0.0.0 PORT=8080 python3 -m app.main
```
- Fuer `lor` sind aktuell nur dann Ergebnisse vorhanden, wenn entsprechende Dateien im Datenordner liegen.
