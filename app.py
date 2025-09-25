from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'brecher_system_secret_key_2025'  # Für Sessions

# Passwort für die Website
WEBSITE_PASSWORD = 'AlphaBrecher'

# BrecherSystem Konfiguration
NAMES = ['David', 'Cedric', 'Müller']
CATEGORIES = ['Gym', 'Food', 'Saps', 'Sleep', 'Study', 'Steps', 'Hausarbeit', 'Work', 'Recovery', 'Podcast/Read', 'Fehler']
DAYS = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
WEEKS = list(range(39, 47))  # KW 39-46

# Datenstruktur für alle Wochen
data_store = {}

def initialize_data():
    """Initialisiere Datenstruktur für alle Wochen"""
    for week in WEEKS:
        data_store[f'KW{week}'] = {
            person: {
                day: {cat: '' for cat in CATEGORIES}
                for day in DAYS
            }
            for person in NAMES
        }

def calculate_points(category, value):
    """Berechne Punkte basierend auf Kategorie und Wert (genau wie im Excel)"""
    if not value or value == '':
        return 0

    try:
        val = float(value)
    except:
        if category == 'Recovery' and str(value).upper() == 'R':
            return 1
        return 0

    if category == 'Gym':
        return min(val * 2, 4)
    elif category == 'Food':
        return min(val, 3)
    elif category == 'Saps':
        return 1 if val > 0 else 0
    elif category == 'Sleep':
        if 7 <= val <= 9:
            return 4
        elif (6 <= val < 7) or (9 < val <= 10):
            return 3
        else:
            return 1
    elif category == 'Study':
        if val >= 4:
            return 3
        elif val >= 2:
            return 2
        elif val >= 1:
            return 1
        else:
            return 0
    elif category == 'Steps':
        return int(val // 5000)
    elif category == 'Hausarbeit':
        return val
    elif category == 'Work':
        return val / 100
    elif category == 'Recovery':
        return 1 if str(value).upper() == 'R' else 0
    elif category == 'Podcast/Read':
        return min(val * 2, 6)
    elif category == 'Fehler':
        return val * -2

    return 0

def get_cell_color(category, value, person=None, day=None, week=None):
    """Bestimme Zellfarbe basierend auf Wert (genau wie im Excel)"""
    if not value or value == '':
        return 'white'

    try:
        val = float(value)
    except:
        if category == 'Recovery' and str(value).upper() == 'R':
            return 'green'
        return 'white'

    if category == 'Gym':
        if val >= 2: return 'green'
        elif val >= 1: return 'orange'
        else: return 'red'
    elif category == 'Food':
        if val >= 3: return 'green'
        elif val >= 2: return 'orange'
        else: return 'red'
    elif category == 'Saps':
        if val >= 1: return 'green'
        else: return 'red'
    elif category == 'Sleep':
        if 7 <= val <= 9: return 'green'
        elif (6 <= val < 7) or (9 < val <= 10): return 'orange'
        else: return 'red'
    elif category == 'Study':
        if val >= 4: return 'green'
        elif val >= 2: return 'orange'
        else: return 'red'
    elif category == 'Steps':
        if val >= 15000: return 'green'
        elif val >= 10000: return 'orange'
        else: return 'red'
    elif category == 'Hausarbeit':
        if val >= 3: return 'green'
        elif val >= 2: return 'orange'
        else: return 'red'
    elif category == 'Work':
        if val >= 300: return 'green'
        elif val >= 150: return 'orange'
        else: return 'red'
    elif category == 'Podcast/Read':
        if val >= 3: return 'green'
        elif val >= 1: return 'orange'
        else: return 'red'
    elif category == 'Fehler':
        if val == 0: return 'green'
        elif val <= 2: return 'orange'
        else: return 'red'
    elif category == 'Recovery':
        # Spezielle Behandlung für Recovery
        if val == 0: return 'darkgreen'  # Dark green für Rest Day (0)
        else: return 'red'  # Alles andere ist ungültig

    return 'white'

def validate_recovery_entry(value, person, day, week):
    """Validiere Recovery-Einträge: R nur wenn Gym=0 und Steps>=5000"""
    if not value or str(value).upper() != 'R':
        return True  # Andere Werte (0, leer) sind immer erlaubt

    # Für 'R' müssen spezielle Bedingungen erfüllt sein
    week_data = data_store.get(week, {})
    person_data = week_data.get(person, {})
    day_data = person_data.get(day, {})

    # Prüfe Gym = 0
    gym_value = day_data.get('Gym', '')
    try:
        gym_val = float(gym_value) if gym_value else 0
    except:
        gym_val = 0

    # Prüfe Steps >= 5000
    steps_value = day_data.get('Steps', '')
    try:
        steps_val = float(steps_value) if steps_value else 0
    except:
        steps_val = 0

    # R ist nur erlaubt wenn Gym = 0 und Steps >= 5000
    return gym_val == 0 and steps_val >= 5000

def calculate_daily_total(person, day, week):
    """Berechne Tagespunkte für eine Person"""
    total = 0
    week_data = data_store.get(week, {})
    person_data = week_data.get(person, {})
    day_data = person_data.get(day, {})

    for category in CATEGORIES:
        value = day_data.get(category, '')
        points = calculate_points(category, value)
        total += points

    return round(total, 2)

def calculate_weekly_total(person, week):
    """Berechne Wochenpunkte für eine Person"""
    total = 0
    for day in DAYS:
        total += calculate_daily_total(person, day, week)
    return round(total, 2)

def get_weekly_scoreboard(week):
    """Erstelle Scoreboard für eine Woche"""
    scores = []
    for person in NAMES:
        score = calculate_weekly_total(person, week)
        scores.append((person, score))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores

def get_monthly_scoreboard():
    """Erstelle Monats-Scoreboard (alle Wochen zusammen)"""
    monthly_scores = {person: 0 for person in NAMES}

    for week in WEEKS:
        week_key = f'KW{week}'
        for person in NAMES:
            monthly_scores[person] += calculate_weekly_total(person, week_key)

    scores = [(person, round(score, 2)) for person, score in monthly_scores.items()]
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores

def get_total_scoreboard():
    """Erstelle TOTAL-Scoreboard (identisch mit monthly da nur ein Zeitraum)"""
    return get_monthly_scoreboard()

def get_weekly_overview():
    """Erstelle Übersicht aller Wochen für Hauptseite"""
    overview = []
    for week in WEEKS:
        week_key = f'KW{week}'
        week_scores = get_weekly_scoreboard(week_key)

        # Bestimme Gewinner nur wenn Punkte > 0 existieren
        winner = None
        if week_scores and any(score > 0 for _, score in week_scores):
            # Finde die höchste Punktzahl
            max_score = max(score for _, score in week_scores)
            if max_score > 0:
                winner = next((person, score) for person, score in week_scores if score == max_score)

        overview.append({
            'week': week,
            'scores': {person: score for person, score in week_scores},
            'winner': winner
        })
    return overview

def get_category_data_for_charts():
    """Erstelle Kategorie-Daten für Charts"""
    category_data = {}

    # Relevante Kategorien für Charts
    chart_categories = ['Gym', 'Food', 'Sleep', 'Study', 'Steps', 'Work']

    for category in chart_categories:
        category_data[category] = {
            'weeks': [],
            'David': [],
            'Cedric': [],
            'Müller': []
        }

        # Für jede Woche die Kategorie-Punkte sammeln
        for week in WEEKS:
            week_key = f'KW{week}'
            category_data[category]['weeks'].append(f'KW{week}')

            for person in NAMES:
                weekly_category_points = 0
                person_data = data_store.get(week_key, {}).get(person, {})

                # Berechne Wochenpunkte für diese Kategorie
                for day in DAYS:
                    day_data = person_data.get(day, {})
                    value = day_data.get(category, '')
                    points = calculate_points(category, value)
                    weekly_category_points += points

                category_data[category][person].append(round(weekly_category_points, 2))

    return category_data

def get_current_week_leaders():
    """Finde Führende in aktueller Woche pro Kategorie"""
    # Nimm letzte Woche als "aktuelle" (KW46 in unserem Fall)
    current_week = WEEKS[-1]
    week_key = f'KW{current_week}'

    leaders = {}
    chart_categories = ['Gym', 'Food', 'Sleep', 'Study', 'Steps', 'Work']

    for category in chart_categories:
        category_scores = {}

        for person in NAMES:
            person_data = data_store.get(week_key, {}).get(person, {})
            weekly_points = 0

            for day in DAYS:
                day_data = person_data.get(day, {})
                value = day_data.get(category, '')
                points = calculate_points(category, value)
                weekly_points += points

            category_scores[person] = round(weekly_points, 2)

        # Finde Führenden
        if any(score > 0 for score in category_scores.values()):
            leader = max(category_scores.items(), key=lambda x: x[1])
            leaders[category] = {
                'leader': leader[0],
                'score': leader[1],
                'scores': category_scores
            }
        else:
            leaders[category] = {
                'leader': None,
                'score': 0,
                'scores': category_scores
            }

    return leaders

def require_auth():
    """Prüfe ob Benutzer eingeloggt ist"""
    return session.get('authenticated', False)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login-Seite"""
    if request.method == 'POST':
        password = request.form.get('password')
        if password == WEBSITE_PASSWORD:
            session['authenticated'] = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Falsches Passwort!')

    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout-Funktion"""
    session.pop('authenticated', None)
    return redirect(url_for('login'))

@app.route('/')
def index():
    """Hauptseite mit Wochenübersicht"""
    if not require_auth():
        return redirect(url_for('login'))

    weekly_overview = get_weekly_overview()
    monthly_scoreboard = get_monthly_scoreboard()
    total_scoreboard = get_total_scoreboard()

    return render_template('index.html',
                         weeks=WEEKS,
                         weekly_overview=weekly_overview,
                         monthly_scoreboard=monthly_scoreboard,
                         total_scoreboard=total_scoreboard)

@app.route('/api/chart-data')
def chart_data():
    """API Endpoint für Chart-Daten"""
    if not require_auth():
        return jsonify({'error': 'Authentication required'}), 401

    category_data = get_category_data_for_charts()
    current_leaders = get_current_week_leaders()

    return jsonify({
        'category_data': category_data,
        'current_leaders': current_leaders
    })

@app.route('/week/<int:week_num>')
def week_view(week_num):
    """Ansicht für eine spezifische Woche"""
    if not require_auth():
        return redirect(url_for('login'))

    week_key = f'KW{week_num}'

    if week_key not in data_store:
        return redirect(url_for('index'))

    # Berechne alle Punkte und Farben für die Woche
    week_data = {}
    for person in NAMES:
        person_data = {}
        for day in DAYS:
            day_data = {}
            person_day_data = data_store[week_key].get(person, {}).get(day, {})

            for category in CATEGORIES:
                value = person_day_data.get(category, '')
                points = calculate_points(category, value)
                color = get_cell_color(category, value)

                day_data[category] = {
                    'value': value,
                    'points': points,
                    'color': color
                }

            # Tagesgesamtpunkte
            daily_total = calculate_daily_total(person, day, week_key)
            day_data['daily_total'] = daily_total
            person_data[day] = day_data

        # Wochenpunkte
        weekly_total = calculate_weekly_total(person, week_key)
        person_data['weekly_total'] = weekly_total
        week_data[person] = person_data

    # Scoreboard
    scoreboard = get_weekly_scoreboard(week_key)

    return render_template('week.html',
                         week_num=week_num,
                         week_data=week_data,
                         names=NAMES,
                         categories=CATEGORIES,
                         days=DAYS,
                         scoreboard=scoreboard)

@app.route('/update_cell', methods=['POST'])
def update_cell():
    """Update einer einzelnen Zelle"""
    if not require_auth():
        return jsonify({'error': 'Authentication required'}), 401

    data = request.json
    week = data.get('week')
    person = data.get('person')
    day = data.get('day')
    category = data.get('category')
    value = data.get('value', '')

    # Validierung
    if week not in data_store:
        return jsonify({'error': 'Invalid week'}), 400

    if person not in NAMES or day not in DAYS or category not in CATEGORIES:
        return jsonify({'error': 'Invalid parameters'}), 400

    # Recovery Validierung
    if category == 'Recovery' and not validate_recovery_entry(value, person, day, week):
        return jsonify({'error': 'Recovery "R" nur bei Gym=0 und Steps≥5000 möglich'}), 400

    # Update Daten
    if person not in data_store[week]:
        data_store[week][person] = {}
    if day not in data_store[week][person]:
        data_store[week][person][day] = {}

    data_store[week][person][day][category] = value

    # Berechne neue Werte
    points = calculate_points(category, value)
    color = get_cell_color(category, value)
    daily_total = calculate_daily_total(person, day, week)
    weekly_total = calculate_weekly_total(person, week)

    # Scoreboard neu berechnen
    scoreboard = get_weekly_scoreboard(week)

    return jsonify({
        'points': points,
        'color': color,
        'daily_total': daily_total,
        'weekly_total': weekly_total,
        'scoreboard': scoreboard
    })

@app.route('/api/data')
def get_all_data():
    """API Endpoint für alle Daten"""
    if not require_auth():
        return jsonify({'error': 'Authentication required'}), 401
    return jsonify(data_store)

@app.route('/api/save', methods=['POST'])
def save_data():
    """Speichere Daten in JSON-Datei"""
    if not require_auth():
        return jsonify({'error': 'Authentication required'}), 401
    try:
        with open('brecher_data.json', 'w') as f:
            json.dump(data_store, f, indent=2)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/load', methods=['POST'])
def load_data():
    """Lade Daten aus JSON-Datei"""
    if not require_auth():
        return jsonify({'error': 'Authentication required'}), 401
    try:
        if os.path.exists('brecher_data.json'):
            with open('brecher_data.json', 'r') as f:
                loaded_data = json.load(f)
                data_store.update(loaded_data)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    initialize_data()

    # Lade gespeicherte Daten falls vorhanden
    if os.path.exists('brecher_data.json'):
        try:
            with open('brecher_data.json', 'r') as f:
                data_store.update(json.load(f))
        except:
            pass

    # Starte Server auf allen Netzwerk-Interfaces
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)