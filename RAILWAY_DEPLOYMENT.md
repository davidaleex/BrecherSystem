# Railway Deployment Instructions für BrecherSystem

## Voraussetzungen
1. Railway Account erstellen: https://railway.app
2. GitHub Repository für das Projekt

## Deployment Steps

### 1. Railway CLI installieren (optional)
```bash
npm install -g @railway/cli
railway login
```

### 2. PostgreSQL Datenbank erstellen
1. Gehe zu Railway Dashboard
2. Erstelle ein neues Projekt
3. Wähle "Add Service" → "Database" → "PostgreSQL"
4. Notiere die DATABASE_URL aus den Environment Variables

### 3. Web Service deployen
1. Im selben Projekt: "Add Service" → "GitHub Repo"
2. Verbinde dein Repository
3. Railway erkennt automatisch die Python App

### 4. Environment Variables setzen
Im Railway Dashboard → dein Web Service → Variables:
```
DATABASE_URL=postgresql://...  (wird automatisch gesetzt wenn PostgreSQL Service im selben Projekt)
SECRET_KEY=your-secret-key-here
FLASK_ENV=production
```

### 5. Migration der lokalen Daten
Nachdem die App deployed ist:
1. Lade die Railway CLI oder nutze die Web Console
2. Führe die Migration aus:
```bash
railway run python database.py
```

### 6. Domain und DNS (optional)
- Railway generiert automatisch eine .railway.app Domain
- Für custom Domain: Railway Dashboard → Settings → Domains

## Wichtige Dateien für Deployment
- `requirements.txt` - Python Dependencies
- `Procfile` - Startet die App mit Gunicorn
- `railway.toml` - Railway-spezifische Konfiguration
- `config.py` - Automatische PostgreSQL/SQLite Erkennung
- `database.py` - Unterstützt beide Datenbanktypen
- `.env.example` - Template für Environment Variables

## Kosten
- PostgreSQL: $5/Monat für 1GB (500MB können gratis sein)
- Web Service: $5/Monat (500 Stunden können gratis sein)
- Erste $5 sind normalerweise gratis bei Railway

## Troubleshooting
1. **Migration Fehler**: Stelle sicher, dass DATABASE_URL korrekt gesetzt ist
2. **App startet nicht**: Prüfe die Logs im Railway Dashboard
3. **Datenbank Connection**: Beide Services müssen im selben Projekt sein für automatische DATABASE_URL