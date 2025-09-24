#!/bin/bash

# BrecherSystem Web Server Starter

echo "🚀 Starte BrecherSystem Web Server..."
echo ""

# Aktiviere Virtual Environment falls vorhanden
if [ -d "../brecher_env" ]; then
    echo "📦 Aktiviere Virtual Environment..."
    source ../brecher_env/bin/activate
fi

# Installiere Requirements
echo "📥 Installiere/Aktualisiere Abhängigkeiten..."
pip install -r requirements.txt

# Finde und zeige lokale IP-Adresse
echo ""
echo "🌐 NETZWERK-INFO:"
echo "=================="

if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}')
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    LOCAL_IP=$(hostname -I | awk '{print $1}')
else
    # Windows (Git Bash)
    LOCAL_IP=$(ipconfig | grep "IPv4" | head -1 | awk '{print $NF}')
fi

echo "📱 Lokaler Zugriff:"
echo "   http://localhost:8080"
echo "   http://127.0.0.1:8080"
echo ""
echo "📡 Netzwerk-Zugriff (andere Geräte im WLAN):"
echo "   http://${LOCAL_IP}:8080"
echo ""
echo "💡 Andere können diese URL in ihrem Browser öffnen!"
echo ""
echo "🔧 Server läuft auf Port 8080"
echo "🛑 Zum Stoppen: Strg+C"
echo ""
echo "=================="

# Starte Flask App
python app.py