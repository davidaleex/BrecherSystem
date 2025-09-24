# 🏆 BrecherSystem Web App

Eine Web-basierte Version des BrecherSystems, die im lokalen Netzwerk läuft und von allen Geräten im WLAN erreichbar ist.

## 🚀 Quick Start

### Automatisch starten:
```bash
./start_server.sh
```

### Manuell starten:
```bash
# 1. Virtual Environment aktivieren (falls vorhanden)
source ../brecher_env/bin/activate

# 2. Abhängigkeiten installieren
pip install -r requirements.txt

# 3. Server starten
python app.py
```

## 🌐 Zugriff

### Lokal (auf diesem Computer):
- http://localhost:5000
- http://127.0.0.1:5000

### Netzwerk (andere Geräte im WLAN):
- http://[DEINE-IP-ADRESSE]:5000
- z.B. http://192.168.1.100:5000

**So findest du deine IP-Adresse:**
- **macOS/Linux:** `ifconfig` oder `ip addr`
- **Windows:** `ipconfig`

## 📱 Features

### ✅ Komplett funktionsfähiges BrecherSystem
- 8 Kalenderwochen (KW39-KW46)
- Alle Excel-Formeln implementiert
- Farbkodierung wie im Original
- Live-Scoreboard
- Automatische Punkte-Berechnung

### ✅ Web-spezifische Features
- **Responsive Design:** Funktioniert auf Desktop, Tablet und Handy
- **Real-time Updates:** Änderungen werden sofort berechnet
- **Auto-Save:** Daten werden alle 30 Sekunden gespeichert
- **Multi-Device:** Mehrere Personen können gleichzeitig arbeiten
- **Navigation:** Einfach zwischen Wochen wechseln

### ✅ Netzwerk-Features
- **Lokales Hosting:** Läuft auf deinem Computer
- **WLAN-Zugriff:** Alle im gleichen WLAN können zugreifen
- **Keine Internet-Verbindung nötig**
- **Datenschutz:** Alle Daten bleiben lokal

## 🎯 Kategorien & Punkte

| Kategorie | Eingabe | Punkte | Grün | Orange | Rot |
|-----------|---------|---------|------|--------|-----|
| **Gym** | Sessions | Sessions × 2 (max 4) | ≥2 | 1 | <1 |
| **Food** | Mahlzeiten | Mahlzeiten (max 3) | ≥3 | 2 | <2 |
| **Saps** | 1/0 | 1 wenn genommen | ≥1 | - | 0 |
| **Sleep** | Stunden | 7-9h=4, 6-7h/9-10h=3, sonst=1 | 7-9h | 6-7h, 9-10h | <6h, >10h |
| **Study** | Stunden | 4+h=3, 2-4h=2, 1-2h=1 | ≥4h | 2-4h | <2h |
| **Steps** | Schritte | Schritte ÷ 5000 | ≥15k | 10-15k | <10k |
| **Hausarbeit** | Punkte | Direkt | ≥3 | 2 | <2 |
| **Work** | CHF | CHF ÷ 100 | ≥300 | 150-300 | <150 |
| **Recovery** | "R" | 1 wenn "R" | R | - | - |
| **Podcast/Read** | Stunden | Stunden × 2 (max 6) | ≥3h | 1-3h | <1h |
| **Fehler** | Anzahl | Anzahl × -2 | 0 | 1-2 | >2 |

## 💾 Daten

- **Automatisches Speichern:** Alle 30 Sekunden
- **Manuelles Speichern:** Button "Daten speichern"
- **Datei:** `brecher_data.json` (wird automatisch erstellt)
- **Backup:** Einfach die JSON-Datei kopieren

## 🔧 Technische Details

- **Framework:** Flask (Python)
- **Frontend:** HTML, CSS, JavaScript
- **Datenformat:** JSON
- **Port:** 5000
- **Host:** 0.0.0.0 (alle Netzwerk-Interfaces)

## 🛠 Problemlösung

### Server startet nicht?
```bash
# Prüfe ob Port 5000 frei ist
lsof -i :5000

# Oder anderen Port verwenden
python app.py --port 8080
```

### Andere Geräte können nicht zugreifen?
1. Firewall-Einstellungen prüfen
2. IP-Adresse korrekt?
3. Gleiche WLAN-Verbindung?
4. Port 5000 freigegeben?

### Daten weg?
1. `brecher_data.json` im Ordner vorhanden?
2. Button "Daten laden" versuchen
3. Backup wiederherstellen

## 📱 Mobile Nutzung

Die App ist vollständig responsive und funktioniert auf:
- 📱 Smartphones (iOS/Android)
- 📱 Tablets (iPad/Android)
- 💻 Desktop (Windows/Mac/Linux)
- 🌐 Alle modernen Browser

## 🤝 Multi-User

- **Gleichzeitig:** Mehrere Personen können gleichzeitig arbeiten
- **Real-time:** Änderungen werden live übertragen
- **Konflikt-frei:** Jede Zelle kann unabhängig bearbeitet werden

## 🔒 Sicherheit

- **Lokales Netzwerk:** Nur im WLAN erreichbar
- **Keine Cloud:** Alle Daten bleiben auf deinem Computer
- **Open Source:** Code ist einsehbar und anpassbar

---

**🎉 Viel Spaß mit dem BrecherSystem Web App! 🎉**