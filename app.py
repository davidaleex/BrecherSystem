from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import json
import os
from datetime import datetime
from database import get_all_data as db_get_all_data, save_data as db_save_data, get_week_data, update_entry, init_database, get_database_stats, get_all_weeks
from config import config

app = Flask(__name__)

# Configure app based on environment
config_name = os.environ.get('FLASK_ENV', 'development')
app_config = config.get(config_name, config['default'])
app.config.from_object(app_config)
app.secret_key = app_config.SECRET_KEY

# Passwort für die Website
WEBSITE_PASSWORD = 'AlphaBrecher'

# BrecherSystem Konfiguration
NAMES = ['David', 'Cedric', 'Müller']
CATEGORIES = ['Gym', 'Food', 'Saps', 'Sleep', 'Study', 'Steps', 'Hausarbeit', 'Work', 'Recovery', 'Podcast/Read', 'Fehler', 'Fasten', 'Cold Plunge', 'Organisatorisches', 'PB']
DAYS = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
# get_weeks_list() wird jetzt dynamisch aus der Datenbank geladen

# Datenstruktur - jetzt aus der Datenbank
data_store = {}

def get_weeks_list():
    """Hole verfügbare Wochen aus der Datenbank"""
    return get_all_weeks()

def initialize_data():
    """Initialisiere Datenbank und lade Daten"""
    global data_store
    init_database()

    # Auto-migrate data on Railway if database is empty
    if os.environ.get('DATABASE_URL') and os.path.exists('railway_migration.json'):
        from database import get_database_stats
        stats = get_database_stats()
        if stats['total_records'] == 0:
            print('🚀 Auto-migrating data to Railway PostgreSQL...')
            try:
                import json
                with open('railway_migration.json', 'r') as f:
                    migration_data = json.load(f)
                records = db_save_data(migration_data)
                print(f'✅ Auto-migrated {records} records!')
            except Exception as e:
                print(f'❌ Migration error: {e}')

    data_store = db_get_all_data()

    # Sicherstellen, dass alle Wochen aus der DB existieren
    available_weeks = get_weeks_list()
    for week in available_weeks:
        week_key = f'KW{week}'
        if week_key not in data_store:
            data_store[week_key] = {}
        for person in NAMES:
            if person not in data_store[week_key]:
                data_store[week_key][person] = {}
            for day in DAYS:
                if day not in data_store[week_key][person]:
                    data_store[week_key][person][day] = {}
                for cat in CATEGORIES:
                    if cat not in data_store[week_key][person][day]:
                        data_store[week_key][person][day][cat] = ''

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
    elif category == 'Fasten':
        return 2 if val > 0 else 0  # 1 eingetragen = 2 Punkte
    elif category == 'Cold Plunge':
        return 1 if val > 0 else 0  # 1 eingetragen = 1 Punkt
    elif category == 'Organisatorisches':
        return min(val, 2)  # Pro Stunde 1 Punkt, max 2
    elif category == 'PB':
        # 2h=1pt, 4h=2pt, 6h=3pt, 8h=4pt
        if val >= 8:
            return 4
        elif val >= 6:
            return 3
        elif val >= 4:
            return 2
        elif val >= 2:
            return 1
        else:
            return 0

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
    elif category == 'Fasten':
        # Nur grün oder rot - 1=grün, 0/leer=rot
        if val >= 1: return 'green'
        else: return 'red'
    elif category == 'Cold Plunge':
        # Nur grün oder rot - 1=grün, 0/leer=rot
        if val >= 1: return 'green'
        else: return 'red'
    elif category == 'Organisatorisches':
        # Stunden: 2=grün, 1=orange, 0=rot
        if val >= 2: return 'green'
        elif val >= 1: return 'orange'
        else: return 'red'
    elif category == 'PB':
        # Stunden: 8=grün, 6=grün, 4=orange, 2=orange, 0=rot
        if val >= 6: return 'green'
        elif val >= 2: return 'orange'
        else: return 'red'

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

    for week in get_weeks_list():
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
    for week in get_weeks_list():
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

def get_weeks_with_data():
    """Gibt nur Wochen zurück, die tatsächlich Daten enthalten"""
    weeks_with_data = []
    for week in get_weeks_list():
        week_key = f'KW{week}'
        week_data = data_store.get(week_key, {})

        # Prüfe ob mindestens eine Person Daten hat
        has_data = False
        for person in NAMES:
            person_data = week_data.get(person, {})
            for day in DAYS:
                day_data = person_data.get(day, {})
                if any(day_data.get(cat, '').strip() for cat in ['Gym', 'Food', 'Sleep', 'Study', 'Steps', 'Work'] if day_data.get(cat, '').strip()):
                    has_data = True
                    break
            if has_data:
                break

        if has_data:
            weeks_with_data.append(week)

    return weeks_with_data

def get_category_data_for_charts():
    """Erstelle Kategorie-Daten für Charts - nur für Wochen mit Daten"""
    category_data = {}

    # Relevante Kategorien für Charts
    chart_categories = ['Gym', 'Food', 'Sleep', 'Study', 'Steps', 'Work']

    # Nur Wochen mit tatsächlichen Daten verwenden
    weeks_with_data = get_weeks_with_data()

    for category in chart_categories:
        category_data[category] = {
            'weeks': [],
            'David': [],
            'Cedric': [],
            'Müller': []
        }

        # Für jede Woche mit Daten die Kategorie-Punkte sammeln
        for week in weeks_with_data:
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

def get_current_week_number():
    """Bestimme aktuelle Kalenderwoche"""
    from datetime import datetime
    current_week = datetime.now().isocalendar()[1]
    # Falls aktuelle Woche nicht in unserem System ist, nimm die letzte
    if current_week not in get_weeks_list():
        return get_weeks_list()[-1]
    return current_week

def get_current_week_leaders():
    """Finde Führende in aktueller Woche pro Kategorie"""
    current_week = get_current_week_number()
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

def get_current_week_scoreboard():
    """Erstelle Leaderboard für aktuelle Woche"""
    current_week = get_current_week_number()
    week_key = f'KW{current_week}'
    return get_weekly_scoreboard(week_key), current_week

def get_daily_statistics(week_num=None):
    """Erstelle tägliche Statistiken für eine Woche"""
    if week_num is None:
        week_num = get_current_week_number()

    week_key = f'KW{week_num}'
    daily_stats = {}

    for day in DAYS:
        daily_stats[day] = {}
        for person in NAMES:
            daily_total = calculate_daily_total(person, day, week_key)
            daily_stats[day][person] = daily_total

        # Sortiere nach Punkten für den Tag
        day_ranking = sorted(daily_stats[day].items(), key=lambda x: x[1], reverse=True)
        daily_stats[day]['ranking'] = day_ranking

    return daily_stats, week_num

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
    current_week_scoreboard, current_week_num = get_current_week_scoreboard()
    daily_stats, _ = get_daily_statistics()

    return render_template('index.html',
                         weeks=get_weeks_list(),
                         weekly_overview=weekly_overview,
                         monthly_scoreboard=monthly_scoreboard,
                         total_scoreboard=total_scoreboard,
                         current_week_scoreboard=current_week_scoreboard,
                         current_week_num=current_week_num,
                         daily_stats=daily_stats)

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

@app.route('/api/statistics/<view_type>')
def statistics_data(view_type):
    """API für verschiedene Statistik-Ansichten"""
    if not require_auth():
        return jsonify({'error': 'Authentication required'}), 401

    if view_type == 'daily':
        stats, week_num = get_daily_statistics()
        return jsonify({'stats': stats, 'week_num': week_num, 'type': 'daily'})
    elif view_type == 'weekly':
        weekly_overview = get_weekly_overview()
        return jsonify({'stats': weekly_overview, 'type': 'weekly'})
    elif view_type == 'monthly':
        monthly_scoreboard = get_monthly_scoreboard()
        return jsonify({'stats': monthly_scoreboard, 'type': 'monthly'})
    else:
        return jsonify({'error': 'Invalid view type'}), 400

@app.route('/week/<int:week_num>')
def week_view(week_num):
    """Ansicht für eine spezifische Woche"""
    if not require_auth():
        return redirect(url_for('login'))

    week_key = f'KW{week_num}'

    # Lade Wochendaten aus der Datenbank falls nicht im data_store
    if week_key not in data_store:
        # Versuche Daten aus Datenbank zu laden
        week_data_from_db = get_week_data(week_key)
        if not week_data_from_db:
            # Erstelle leere Woche falls nicht existiert
            data_store[week_key] = {}
            for person in NAMES:
                data_store[week_key][person] = {}
                for day in DAYS:
                    data_store[week_key][person][day] = {}
                    for cat in CATEGORIES:
                        data_store[week_key][person][day][cat] = ''
        else:
            # Füge geladene Daten zum data_store hinzu
            data_store[week_key] = week_data_from_db

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

    # Speichere auch in der Datenbank
    update_entry(week, person, day, category, value)

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
def get_all_data_api():
    """API Endpoint für alle Daten"""
    if not require_auth():
        return jsonify({'error': 'Authentication required'}), 401
    return jsonify(data_store)

@app.route('/api/save', methods=['POST'])
def save_data():
    """Speichere Daten in SQLite-Datenbank"""
    if not require_auth():
        return jsonify({'error': 'Authentication required'}), 401
    try:
        records_saved = db_save_data(data_store)
        return jsonify({'success': True, 'records_saved': records_saved})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/load', methods=['POST'])
def load_data():
    """Lade Daten aus SQLite-Datenbank"""
    if not require_auth():
        return jsonify({'error': 'Authentication required'}), 401
    try:
        global data_store
        data_store = db_get_all_data()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/database/stats')
def database_stats():
    """API Endpoint für Datenbankstatistiken"""
    if not require_auth():
        return jsonify({'error': 'Authentication required'}), 401
    return jsonify(get_database_stats())

@app.route('/api/create-week', methods=['POST'])
def create_week():
    """Erstelle eine neue Kalenderwoche"""
    if not require_auth():
        return jsonify({'error': 'Authentication required'}), 401

    data = request.json
    week_number = data.get('week_number')

    # Validierung
    if not week_number:
        return jsonify({'error': 'Wochennummer ist erforderlich'}), 400

    try:
        week_number = int(week_number)
        if week_number < 1 or week_number > 53:
            return jsonify({'error': 'Wochennummer muss zwischen 1 und 53 liegen'}), 400
    except ValueError:
        return jsonify({'error': 'Ungültige Wochennummer'}), 400

    week_key = f'KW{week_number}'

    # Prüfen ob Woche bereits existiert
    if week_key in data_store:
        return jsonify({'error': f'KW{week_number} existiert bereits'}), 400

    # Neue Woche erstellen
    data_store[week_key] = {}
    for person in NAMES:
        data_store[week_key][person] = {}
        for day in DAYS:
            data_store[week_key][person][day] = {}
            for category in CATEGORIES:
                data_store[week_key][person][day][category] = ''
                # Speichere leeren Eintrag in der Datenbank
                update_entry(week_key, person, day, category, '')

    # Neue Woche ist jetzt in der Datenbank verfügbar
    # get_weeks_list() wird sie automatisch beim nächsten Aufruf finden

    return jsonify({
        'success': True,
        'message': f'KW{week_number} wurde erfolgreich erstellt',
        'week_number': week_number,
        'redirect_url': f'/week/{week_number}'
    })

@app.route('/migrate-data-now')
def migrate_data_now():
    """Manueller Migration Endpoint - nur für Railway Setup"""
    if not os.environ.get('DATABASE_URL'):
        return "❌ Nur auf Railway verfügbar (DATABASE_URL benötigt)"

    try:
        from database import get_database_stats, init_database

        # Zuerst Datenbank initialisieren (Tabellen erstellen)
        init_database()

        # Dann prüfen ob schon Daten da sind
        stats = get_database_stats()
        if stats['total_records'] > 0:
            return f"ℹ️ Datenbank hat bereits {stats['total_records']} Datensätze"

        # Migration ausführen
        import json
        if not os.path.exists('railway_migration.json'):
            return "❌ railway_migration.json nicht gefunden"

        with open('railway_migration.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        records = db_save_data(data)
        final_stats = get_database_stats()

        return f"""
        ✅ Migration erfolgreich!<br>
        📊 {records} Datensätze migriert<br>
        📊 Finale Statistik: {final_stats['total_records']} Einträge über {final_stats['total_weeks']} Wochen<br>
        🎉 BrecherSystem ist bereit!
        """

    except Exception as e:
        return f"❌ Migration Fehler: {str(e)}"

if __name__ == '__main__':
    print("🚀 Starting BrecherSystem with SQLite Database...")
    initialize_data()

    # Show database stats
    stats = get_database_stats()
    print(f"📊 Database loaded: {stats['total_records']} records, {stats['total_weeks']} weeks")

    # Starte Server auf allen Netzwerk-Interfaces
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)