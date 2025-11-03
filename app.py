from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import json
import os
from datetime import datetime, timedelta
from database import get_all_data as db_get_all_data, save_data as db_save_data, get_week_data, update_entry, init_database, get_database_stats, get_all_weeks, get_db_connection
from config import config
from firebase_auth import init_firebase, verify_firebase_token, require_firebase_auth, get_current_user, is_firebase_available
from firestore_users import create_user_profile, get_user_profile, update_user_profile

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
CATEGORIES = ['Gym', 'Food', 'Supps', 'Sleep', 'FH', 'Steps', 'Hausarbeit', 'Work', 'Study', 'Fehler', 'Morgenroutine', 'Abendroutine', 'PB']
DAYS = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
# get_weeks_list() wird jetzt dynamisch aus der Datenbank geladen

# Datenstruktur - jetzt aus der Datenbank
data_store = {}
db_initialized = False

def get_weeks_list():
    """Hole verfügbare Wochen aus der Datenbank"""
    return get_all_weeks()

def ensure_database_initialized():
    """Stelle sicher, dass die Datenbank initialisiert ist"""
    global db_initialized, data_store
    if db_initialized:
        return

    try:
        init_database()

        # Initialize Firebase
        init_firebase()

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
        db_initialized = True
        print('✅ Database initialized successfully')
    except Exception as e:
        print(f'❌ Database initialization failed: {e}')
        raise

def initialize_data():
    """Initialisiere Datenbank und lade Daten"""
    ensure_database_initialized()

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
    """Berechne Punkte basierend auf Kategorie und Wert"""
    if not value or value == '':
        return 0

    try:
        val = float(value)
    except:
        # Gym 'R' (Rest Day) - 1x pro Woche erlaubt, gibt 2 Punkte
        if category == 'Gym' and str(value).upper() == 'R':
            return 2
        return 0

    if category == 'Gym':
        # 1 Workout = 2 Punkte, 2 Workouts = 4 Punkte, etc.
        return val * 2
    elif category == 'Food':
        return min(val, 3)
    elif category == 'Supps':  # Renamed from Saps
        return 1 if val > 0 else 0
    elif category == 'Sleep':
        if 7 <= val <= 9:
            return 4
        elif (6 <= val < 7) or (9 < val <= 10):
            return 3
        else:
            return 1
    elif category == 'FH':  # Renamed from Study - 0.5 points per hour
        return val * 0.5
    elif category == 'Steps':
        # New formula: (steps * 2) / 10000
        return (val * 2) / 10000
    elif category == 'Hausarbeit':
        return val
    elif category == 'Work':
        return val / 100
    elif category == 'Study':  # Renamed from Podcast/Read - 2 points per hour
        return val * 2
    elif category == 'Fehler':
        # Fehler-Berechnung erfolgt über die ganze Woche (siehe calculate_daily_total)
        return val * -2  # Temporär, wird in calculate_daily_total überschrieben
    elif category == 'Morgenroutine':
        return 2 if val >= 1 else 0
    elif category == 'Abendroutine':
        return 2 if val >= 1 else 0
    elif category == 'PB':
        # 1h = 1 Punkt (direkte Umrechnung)
        return val
    return 0

def get_cell_color(category, value, person=None, day=None, week=None):
    """Bestimme Zellfarbe basierend auf Wert"""
    if not value or value == '':
        return 'white'

    try:
        val = float(value)
    except:
        # Gym 'R' (Rest Day) - grün
        if category == 'Gym' and str(value).upper() == 'R':
            return 'green'
        return 'white'

    if category == 'Gym':
        # 1 Workout = grün, 2+ Workouts = grün
        if val >= 1: return 'green'
        else: return 'orange'
    elif category == 'Food':
        if val >= 3: return 'green'
        elif val >= 2: return 'orange'
        else: return 'red'
    elif category == 'Supps':  # Renamed from Saps
        if val >= 1: return 'green'
        else: return 'red'
    elif category == 'Sleep':
        if 7 <= val <= 9: return 'green'
        elif (6 <= val < 7) or (9 < val <= 10): return 'orange'
        else: return 'red'
    elif category == 'FH':  # Renamed from Study - 0.5 points per hour
        if val >= 4: return 'green'
        elif val >= 2: return 'orange'
        else: return 'red'
    elif category == 'Steps':
        # New thresholds based on new formula
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
    elif category == 'Study':  # Renamed from Podcast/Read - 2 points per hour
        if val >= 3: return 'green'
        elif val >= 1: return 'orange'
        else: return 'red'
    elif category == 'Fehler':
        if val == 0:
            return 'green'  # Keine Fehler = grün
        else:
            # Prüfe ob es der erste Fehler der Woche ist (braucht week context)
            if person and day and week:
                fehler_points = calculate_fehler_points_for_day(person, day, week)
                if fehler_points == 0:
                    return 'green'  # Erster Fehler = grün (toleriert)
                else:
                    return 'red'  # Weitere Fehler = rot
            else:
                return 'red'  # Fallback
    elif category == 'Morgenroutine':
        if val >= 1: return 'green'
        else: return 'red'
    elif category == 'Abendroutine':
        if val >= 1: return 'green'
        else: return 'red'
    elif category == 'PB':
        if val >= 6: return 'green'
        elif val >= 2: return 'orange'
        else: return 'red'
    return 'white'

def validate_gym_r_entry(value, person, week):
    """Validiere Gym 'R' Einträge: nur 1x pro Woche erlaubt"""
    if not value or str(value).upper() != 'R':
        return True  # Andere Werte sind immer erlaubt

    # Zähle bereits vorhandene 'R' Einträge in der Woche
    week_data = data_store.get(week, {})
    person_data = week_data.get(person, {})

    r_count = 0
    for day in DAYS:
        day_data = person_data.get(day, {})
        gym_value = day_data.get('Gym', '')
        if str(gym_value).upper() == 'R':
            r_count += 1

    # Nur 1 'R' pro Woche erlaubt
    return r_count < 1

def calculate_fehler_points_for_day(person, target_day, week):
    """Berechne Fehler-Punkte für einen Tag basierend auf der gesamten Woche
    Regel: Erster Fehler der Woche = 0 Punkte, alle weiteren = -2 Punkte
    """
    week_data = data_store.get(week, {})
    person_data = week_data.get(person, {})

    # Sammle alle Fehler der gesamten Woche in chronologischer Reihenfolge
    all_week_errors = []

    for day in DAYS:
        day_data = person_data.get(day, {})
        fehler_value = day_data.get('Fehler', '')
        if fehler_value and fehler_value.strip():
            try:
                fehler_count = int(float(fehler_value))
                if fehler_count > 0:
                    # Füge für jeden Fehler dieses Tages einen Eintrag hinzu
                    for _ in range(fehler_count):
                        all_week_errors.append(day)
            except:
                pass

    # Finde Fehler für den Ziel-Tag
    target_day_data = person_data.get(target_day, {})
    target_fehler_value = target_day_data.get('Fehler', '')

    if not target_fehler_value or target_fehler_value.strip() == '':
        return 0

    try:
        target_fehler_count = int(float(target_fehler_value))
    except:
        return 0

    if target_fehler_count <= 0:
        return 0

    # Berechne welche Position die Fehler des Ziel-Tags in der Gesamt-Woche haben
    total_points = 0
    error_position = 1  # Zähler für die Gesamtposition der Fehler

    for day in DAYS:
        day_data = person_data.get(day, {})
        day_fehler_value = day_data.get('Fehler', '')

        if day_fehler_value and day_fehler_value.strip():
            try:
                day_fehler_count = int(float(day_fehler_value))
                if day_fehler_count > 0:
                    # Wenn das der Ziel-Tag ist, berechne Punkte
                    if day == target_day:
                        for _ in range(day_fehler_count):
                            if error_position == 1:
                                total_points += 0  # Erster Fehler der Woche = 0 Punkte
                            else:
                                total_points += -2  # Weitere Fehler = -2 Punkte
                            error_position += 1
                        break
                    else:
                        # Andere Tage: erhöhe nur den Zähler
                        error_position += day_fehler_count
            except:
                pass

    return total_points

def calculate_daily_total(person, day, week):
    """Berechne Tagespunkte für eine Person"""
    total = 0
    week_data = data_store.get(week, {})
    person_data = week_data.get(person, {})
    day_data = person_data.get(day, {})

    for category in CATEGORIES:
        value = day_data.get(category, '')
        if category == 'Fehler':
            # Spezielle Behandlung für Fehler (wochenweise Toleranz)
            points = calculate_fehler_points_for_day(person, day, week)
        else:
            points = calculate_points(category, value)
        total += points

    return round(total, 2)

def calculate_weekly_total(person, week):
    """Berechne Wochenpunkte für eine Person"""
    total = 0
    for day in DAYS:
        total += calculate_daily_total(person, day, week)

    # Add weekly bonus points
    bonus_points = calculate_weekly_bonus(person, week)
    total += bonus_points

    return round(total, 2)

def calculate_weekly_bonus(person, week):
    """Berechne Wochen-Bonus: 5x Gym = 2 Punkte, 7 fehlerfreie Tage = 2 Punkte"""
    week_data = data_store.get(week, {})
    person_data = week_data.get(person, {})

    bonus_points = 0

    # Bonus 1: 5x Gym = 2 Bonus-Punkte
    gym_count = 0
    for day in DAYS:
        day_data = person_data.get(day, {})
        gym_value = day_data.get('Gym', '')

        # Zähle nur echte Workouts, nicht 'R' (Rest Day)
        if gym_value and str(gym_value).upper() != 'R':
            try:
                gym_val = float(gym_value)
                if gym_val > 0:
                    gym_count += gym_val
            except:
                pass

    if gym_count >= 5:
        bonus_points += 2

    # Bonus 2: 7 fehlerfreie Tage = 2 Bonus-Punkte
    # ALLE 7 Tage müssen eingetragen UND 0 sein (grün)
    all_days_filled_and_zero = True
    for day in DAYS:
        day_data = person_data.get(day, {})
        fehler_value = day_data.get('Fehler', '')

        # Tag muss einen Wert haben UND dieser muss 0 sein
        if not fehler_value or fehler_value.strip() == '':
            all_days_filled_and_zero = False  # Kein Eintrag = kein Bonus
            break

        try:
            fehler_val = float(fehler_value)
            if fehler_val != 0:
                all_days_filled_and_zero = False  # Nicht 0 = kein Bonus
                break
        except:
            all_days_filled_and_zero = False  # Ungültiger Wert = kein Bonus
            break

    # Nur wenn alle 7 Tage explizit mit 0 eingetragen sind
    if all_days_filled_and_zero:
        bonus_points += 2

    return bonus_points

def get_weekly_scoreboard(week):
    """Erstelle Scoreboard für eine Woche"""
    scores = []
    for person in NAMES:
        score = calculate_weekly_total(person, week)
        scores.append((person, score))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores

def get_monthly_scoreboard():
    """Erstelle Monats-Scoreboard - nur abgeschlossene Wochen
    
    WICHTIG: Laufende Wochen werden nicht in das Monthly Scoreboard einbezogen.
    """
    monthly_scores = {person: 0 for person in NAMES}
    
    # Bestimme welche Woche aktuell im Scoreboard angezeigt wird (abgeschlossene Wochen)
    current_scoreboard_week = get_scoreboard_week()

    # Nur abgeschlossene Wochen in das Monthly Scoreboard einbeziehen
    for week in get_weeks_list():
        if week <= current_scoreboard_week:  # Nur abgeschlossene Wochen
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
    """Erstelle Übersicht aller Wochen für Hauptseite
    
    WICHTIG: Für die aktuelle laufende Woche werden keine endgültigen
    Punkte oder Gewinner angezeigt, bis das offizielle Scoreboard live geht
    (ab Sonntag 22:00).
    """
    overview = []
    
    # Bestimme welche Woche aktuell im Scoreboard angezeigt wird
    current_scoreboard_week = get_scoreboard_week()
    
    for week in get_weeks_list():
        week_key = f'KW{week}'
        
        # Für abgeschlossene Wochen: Normale Berechnung mit Punkten und Gewinnern
        if week <= current_scoreboard_week:
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
                'winner': winner,
                'is_final': True  # Woche ist abgeschlossen
            })
        
        # Für laufende Wochen: Zeige nur dass die Woche läuft, ohne endgültige Punkte
        else:
            # Erstelle leere/vorläufige Punkte für laufende Woche
            preliminary_scores = []
            for person in NAMES:
                preliminary_scores.append((person, 0.0))  # Keine Punkte anzeigen
                
            overview.append({
                'week': week,
                'scores': {person: 0.0 for person in NAMES},  # Keine Punkte für laufende Woche
                'winner': None,  # Kein Gewinner für laufende Woche
                'is_final': False,  # Woche läuft noch
                'status': 'In Progress'  # Status-Indikator
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
                if any(day_data.get(cat, '').strip() for cat in ['Gym', 'Food', 'Sleep', 'FH', 'Steps', 'Work'] if day_data.get(cat, '').strip()):
                    has_data = True
                    break
            if has_data:
                break

        if has_data:
            weeks_with_data.append(week)

    return weeks_with_data

def get_category_data_for_charts():
    """Erstelle Kategorie-Daten für Charts - nur für abgeschlossene Wochen
    
    WICHTIG: Laufende Wochen werden nicht in Charts angezeigt bis Sonntag 22:00.
    """
    category_data = {}

    # ALLE Kategorien für Charts (Backend -> Frontend Mapping)
    # Alle 13 Backend categories: ['Gym', 'Food', 'Supps', 'Sleep', 'FH', 'Steps', 'Hausarbeit', 'Work', 'Study', 'Fehler', 'Morgenroutine', 'Abendroutine', 'PB']
    backend_categories = ['Gym', 'Food', 'Supps', 'Sleep', 'FH', 'Steps', 'Hausarbeit', 'Work', 'Study', 'Fehler', 'Morgenroutine', 'Abendroutine', 'PB']
    
    # Frontend-Namen Mapping (falls nötig)
    frontend_names = {
        'FH': 'FH (University)',  # FH bleibt FH
        'Supps': 'Supplements',
        'PB': 'Personal Business'
    }
    
    # Bestimme welche Woche aktuell im Scoreboard angezeigt wird (abgeschlossene Wochen)
    current_scoreboard_week = get_scoreboard_week()

    # Nur Wochen mit tatsächlichen Daten verwenden UND die abgeschlossen sind
    weeks_with_data = [week for week in get_weeks_with_data() if week <= current_scoreboard_week]

    for backend_category in backend_categories:
        # Frontend-Namen für Kategorie bestimmen
        frontend_category = frontend_names.get(backend_category, backend_category)
        
        category_data[frontend_category] = {
            'weeks': [],
            'David': [],
            'Cedric': [],
            'Müller': []
        }

        # Für jede abgeschlossene Woche mit Daten die Kategorie-Punkte sammeln
        for week in weeks_with_data:
            week_key = f'KW{week}'
            category_data[frontend_category]['weeks'].append(f'KW{week}')

            for person in NAMES:
                weekly_category_points = 0
                person_data = data_store.get(week_key, {}).get(person, {})

                # Berechne Wochenpunkte für diese Kategorie (Backend-Namen verwenden!)
                for day in DAYS:
                    day_data = person_data.get(day, {})
                    value = day_data.get(backend_category, '')  # Backend-Kategorie für Datenabfrage
                    points = calculate_points(backend_category, value)  # Backend-Kategorie für Punkteberechnung
                    weekly_category_points += points

                category_data[frontend_category][person].append(round(weekly_category_points, 2))

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
    """Finde Führende in aktueller/abgeschlossener Woche pro Kategorie
    
    WICHTIG: Zeigt nur Leaders für abgeschlossene Wochen (ab Sonntag 22:00).
    Für laufende Wochen werden keine Leaders angezeigt.
    """
    # Bestimme welche Woche im Scoreboard angezeigt wird (abgeschlossene Woche)
    current_scoreboard_week = get_scoreboard_week()
    current_week = get_current_week_number()
    
    # Wenn aktuelle Woche noch nicht abgeschlossen ist, zeige Leaders OHNE Punkte! 😎
    if current_week > current_scoreboard_week:
        # Laufende Woche - Leaders zeigen aber KEINE Punkte verraten!
        week_key = f'KW{current_week}'
        leaders = {}
        # Backend/Frontend Mapping für Leaders (ALLE 13 Kategorien)
        backend_categories = ['Gym', 'Food', 'Supps', 'Sleep', 'FH', 'Steps', 'Hausarbeit', 'Work', 'Study', 'Fehler', 'Morgenroutine', 'Abendroutine', 'PB']
        frontend_names = {
            'FH': 'FH (University)',
            'Supps': 'Supplements',
            'PB': 'Personal Business'
        }
        
        for backend_category in backend_categories:
            frontend_category = frontend_names.get(backend_category, backend_category)
            category_scores = {}
            
            # Berechne echte Führung für laufende Woche
            for person in NAMES:
                person_data = data_store.get(week_key, {}).get(person, {})
                weekly_points = 0
                
                for day in DAYS:
                    day_data = person_data.get(day, {})
                    value = day_data.get(backend_category, '')
                    points = calculate_points(backend_category, value)
                    weekly_points += points
                    
                category_scores[person] = round(weekly_points, 2)
            
            # Finde Führenden ABER verstecke die Punkte! 😏
            if any(score > 0 for score in category_scores.values()):
                leader = max(category_scores.items(), key=lambda x: x[1])
                leaders[frontend_category] = {
                    'leader': leader[0],  # Name des Führenden zeigen ✅
                    'score': '?',  # Punkte verstecken 🤫
                    'scores': {person: '?' for person in NAMES},  # Alle Punkte verstecken
                    'status': 'In Progress - Leader ohne Punkte!'  # Status
                }
            else:
                leaders[frontend_category] = {
                    'leader': None,
                    'score': '?',
                    'scores': {person: '?' for person in NAMES},
                    'status': 'In Progress - Noch keine Daten'
                }
        return leaders
    
    # Woche ist abgeschlossen - normale Leader-Berechnung
    week_key = f'KW{current_scoreboard_week}'
    leaders = {}
    backend_categories = ['Gym', 'Food', 'Supps', 'Sleep', 'FH', 'Steps', 'Hausarbeit', 'Work', 'Study', 'Fehler', 'Morgenroutine', 'Abendroutine', 'PB']
    frontend_names = {
        'FH': 'FH (University)',
        'Supps': 'Supplements',
        'PB': 'Personal Business'
    }

    for backend_category in backend_categories:
        frontend_category = frontend_names.get(backend_category, backend_category)
        category_scores = {}

        for person in NAMES:
            person_data = data_store.get(week_key, {}).get(person, {})
            weekly_points = 0

            for day in DAYS:
                day_data = person_data.get(day, {})
                value = day_data.get(backend_category, '')  # Backend-Namen für Datenabfrage
                points = calculate_points(backend_category, value)  # Backend-Namen für Punkteberechnung
                weekly_points += points

            category_scores[person] = round(weekly_points, 2)

        # Finde Führenden
        if any(score > 0 for score in category_scores.values()):
            leader = max(category_scores.items(), key=lambda x: x[1])
            leaders[frontend_category] = {  # Frontend-Namen für Output
                'leader': leader[0],
                'score': leader[1],
                'scores': category_scores,
                'status': 'Final'  # Woche ist abgeschlossen
            }
        else:
            leaders[frontend_category] = {  # Frontend-Namen für Output
                'leader': None,
                'score': 0,
                'scores': category_scores,
                'status': 'Final'  # Woche ist abgeschlossen
            }

    return leaders

def get_current_week_scoreboard():
    """Erstelle Leaderboard für anzuzeigende Woche (vorherige abgeschlossene Woche)"""
    scoreboard_week = get_scoreboard_week()
    week_key = f'KW{scoreboard_week}'
    return get_weekly_scoreboard(week_key), scoreboard_week

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

def is_scoreboard_visible():
    """Prüfe ob Scoreboards sichtbar sein sollen (Sonntag 22:00 - nächster Sonntag 22:00)"""
    now = datetime.now()
    current_weekday = now.weekday()  # 0=Montag, 6=Sonntag
    current_hour = now.hour

    # Sonntag (6) ab 22:00
    if current_weekday == 6 and current_hour >= 22:
        return True

    # Montag bis Samstag (ganze Woche)
    if current_weekday >= 0 and current_weekday <= 5:
        return True

    # Sonntag vor 22:00
    if current_weekday == 6 and current_hour < 22:
        return True

    return False

def calculate_user_statistics(user_name):
    """Berechne Statistiken für einen User: Wins, Gesamtpunkte, absolvierte Wochen
    
    WICHTIG: Wins werden nur für abgeschlossene Wochen gezählt!
    Eine Woche gilt als abgeschlossen, wenn sie im offiziellen Scoreboard angezeigt wird.
    Das passiert ab Sonntag 22:00 für die gerade beendete Woche.
    """
    if user_name not in NAMES:
        return {'wins': 0, 'total_points': 0, 'completed_weeks': 0}

    wins = 0
    total_points = 0
    completed_weeks = 0
    
    # Bestimme welche Woche aktuell im Scoreboard angezeigt wird
    # Nur Wochen bis zu dieser Woche (einschließlich) zählen für Wins
    current_scoreboard_week = get_scoreboard_week()

    for week in get_weeks_list():
        week_key = f'KW{week}'

        # Berechne Gesamtpunkte für diese Woche (immer, unabhängig vom Zeitpunkt)
        week_points = calculate_weekly_total(user_name, week_key)
        total_points += week_points

        # Prüfe ob User diese Woche gewonnen hat
        # ABER: Wins nur zählen wenn Woche bereits "abgeschlossen" ist (im Scoreboard angezeigt wird)
        if week <= current_scoreboard_week:
            week_scoreboard = get_weekly_scoreboard(week_key)
            if week_scoreboard and week_scoreboard[0][0] == user_name:
                wins += 1

        # Prüfe ob Woche "absolviert" (alle Kategorien ausgefüllt)
        week_data = data_store.get(week_key, {})
        user_data = week_data.get(user_name, {})

        week_completed = True
        for day in DAYS:
            day_data = user_data.get(day, {})
            for category in CATEGORIES:
                value = day_data.get(category, '')
                if not value or value.strip() == '':
                    week_completed = False
                    break
            if not week_completed:
                break

        if week_completed:
            completed_weeks += 1

    return {
        'wins': wins,
        'total_points': round(total_points, 2),
        'completed_weeks': completed_weeks
    }

def get_scoreboard_week():
    """Bestimme welche Woche im Scoreboard angezeigt werden soll"""
    now = datetime.now()
    current_week = now.isocalendar()[1]
    current_weekday = now.weekday()  # 0=Montag, 6=Sonntag
    current_hour = now.hour

    # Wenn Sonntag ab 22:00, zeige aktuelle Woche (die gerade abgeschlossen wurde)
    if current_weekday == 6 and current_hour >= 22:
        return current_week

    # Sonst zeige vorherige Woche
    previous_week = current_week - 1

    # Handle year boundary (wenn wir in KW 1 sind und vorherige Woche brauchen)
    if previous_week < 1:
        # Get last week of previous year
        from datetime import date
        last_year = now.year - 1
        last_date_of_year = date(last_year, 12, 31)
        previous_week = last_date_of_year.isocalendar()[1]

    return previous_week

def require_auth():
    """Prüfe ob Benutzer eingeloggt ist"""
    # Check Firebase authentication first
    if is_firebase_available():
        current_user = get_current_user()
        if current_user:
            return True

    # Fallback to session-based auth
    return session.get('authenticated', False)

@app.route('/login', methods=['GET', 'POST'])
@app.route('/login-new', methods=['GET', 'POST'])
def login():
    """Firebase-basierte Login-Seite"""
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'legacy':
            # Alte Passwort-Anmeldung als Fallback
            password = request.form.get('old_password')
            if password == WEBSITE_PASSWORD:
                session['authenticated'] = True
                session['user_name'] = 'Legacy User'
                session['user_email'] = 'legacy@brechersystem.com'
                return redirect(url_for('index'))
            else:
                return render_template('login_fixed.html', error='Falsches altes Passwort!')

    return render_template('login_fixed.html')


@app.route('/login-fixed')
def login_fixed():
    """Verbesserte Firebase Login-Seite mit Debug-Info"""
    return render_template('login_fixed.html')

@app.route('/logout')
def logout():
    """Logout-Funktion"""
    session.pop('authenticated', None)
    session.pop('firebase_user', None)
    # Render logout page mit Firebase signOut
    return render_template('logout.html')


# Firebase Authentication Routes
@app.route('/api/auth/verify', methods=['POST'])
def verify_firebase_auth():
    """Verify Firebase ID token and create/update user"""
    try:
        print(f"🔐 Auth verification request received", flush=True)
        data = request.get_json()
        print(f"🔐 Request data keys: {list(data.keys()) if data else 'None'}", flush=True)

        id_token = data.get('idToken') if data else None
        profile_data = data.get('profile', {}) if data else {}

        if not id_token:
            print(f"❌ No ID token provided")
            return jsonify({'error': 'ID token required'}), 400

        print(f"🔐 Verifying Firebase token (length: {len(id_token)})", flush=True)

        # Verify Firebase token
        print(f"🔐 Calling verify_firebase_token...", flush=True)
        user_info = verify_firebase_token(id_token)
        if not user_info:
            print(f"❌ Firebase token verification failed", flush=True)
            return jsonify({'error': 'Invalid token'}), 401

        print(f"✅ Firebase token verified for user: {user_info.get('email')}", flush=True)

        # Create or update user in Firestore
        print(f"🔐 Creating/updating user in Firestore...", flush=True)

        # Merge profile data with user info
        extended_profile = {
            'profile_picture': user_info['profile_picture'],
            **profile_data  # Add birthdate, gender, city, country etc.
        }

        user = create_user_profile(
            firebase_uid=user_info['firebase_uid'],
            email=user_info['email'],
            display_name=user_info['display_name'],
            profile_data=extended_profile
        )
        print(f"✅ User created/updated in Firestore: {user is not None}", flush=True)
        print(f"🔐 Profile data saved: {profile_data}", flush=True)

        # Check if user creation failed
        if user is None:
            print(f"❌ Failed to create user profile in Firestore", flush=True)
            return jsonify({'error': 'Failed to create user profile'}), 500

        # Store user info in session
        session['firebase_user'] = user_info
        session['authenticated'] = True

        print(f"✅ Session updated successfully")

        return jsonify({
            'success': True,
            'user': {
                'uid': user_info['firebase_uid'],
                'email': user_info['email'],
                'displayName': user_info['display_name'],
                'photoURL': user_info['profile_picture']
            }
        })

    except Exception as e:
        print(f"❌ Firebase auth verification failed: {e}")
        import traceback
        traceback_str = traceback.format_exc()
        print(f"❌ Full traceback: {traceback_str}")

        # Return detailed error in development
        return jsonify({
            'error': 'Authentication failed',
            'details': str(e),
            'traceback': traceback_str
        }), 500


@app.route('/api/auth/status')
def auth_status():
    """Get current authentication status"""
    if is_firebase_available():
        user = get_current_user()
        if user:
            return jsonify({
                'authenticated': True,
                'firebase': True,
                'user': {
                    'uid': user['firebase_uid'],
                    'email': user['email'],
                    'displayName': user['display_name']
                }
            })

    # Fallback to old auth system
    if session.get('authenticated'):
        return jsonify({
            'authenticated': True,
            'firebase': False,
            'legacy': True
        })

    return jsonify({'authenticated': False})


@app.route('/api/firebase-config')
def firebase_config():
    """Get Firebase configuration for frontend"""
    return jsonify({
        'apiKey': app_config.FIREBASE_WEB_API_KEY or 'demo-key',
        'authDomain': app_config.FIREBASE_WEB_AUTH_DOMAIN or f'{app_config.FIREBASE_PROJECT_ID}.firebaseapp.com',
        'projectId': app_config.FIREBASE_WEB_PROJECT_ID or app_config.FIREBASE_PROJECT_ID,
        'storageBucket': app_config.FIREBASE_WEB_STORAGE_BUCKET or f'{app_config.FIREBASE_PROJECT_ID}.appspot.com',
        'messagingSenderId': app_config.FIREBASE_WEB_MESSAGING_SENDER_ID or '123456789',
        'appId': app_config.FIREBASE_WEB_APP_ID or '1:123456789:web:demo'
    })


@app.route('/test-auth')
def test_auth():
    """Firebase authentication test page"""
    with open('test_auth.html', 'r') as f:
        return f.read()


@app.route('/profile')
def profile():
    """User profile page"""
    if not require_auth():
        return redirect(url_for('login'))

    ensure_database_initialized()

    # Get current user info from Firestore
    current_user = get_current_user()

    if current_user:
        # Firebase user with Firestore data
        user_info = current_user  # Firestore data includes all fields

        # Map Firebase user to our system names for statistics
        user_name = None
        if current_user.get('email'):
            email = current_user['email'].lower()
            if 'david' in email:
                user_name = 'David'
            elif 'cedric.müller3' in email or 'cedric.mueller3' in email:
                user_name = 'Müller'
            elif 'cédric.neuhaus' in email or 'cedric.neuhaus' in email:
                user_name = 'Cedric'

        # Calculate user statistics
        if user_name:
            user_stats = calculate_user_statistics(user_name)
        else:
            user_stats = {'wins': 0, 'total_points': 0, 'completed_weeks': 0}
    else:
        # Legacy user fallback
        user_info = {
            'display_name': 'Legacy User',
            'email': None
        }
        user_stats = {'wins': 0, 'total_points': 0, 'completed_weeks': 0}

    return render_template('profile.html', user=user_info, stats=user_stats)

@app.route('/')
def index():
    """Hauptseite mit Wochenübersicht"""
    if not require_auth():
        return redirect(url_for('login'))

    # Ensure database is initialized
    ensure_database_initialized()

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
                         daily_stats=daily_stats,
                         show_scoreboards=is_scoreboard_visible())

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
                if category == 'Fehler':
                    # Spezielle Behandlung für Fehler mit Week-Context
                    points = calculate_fehler_points_for_day(person, day, week_key)
                    color = get_cell_color(category, value, person, day, week_key)
                else:
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

        # Add bonus row data
        bonus_points = calculate_weekly_bonus(person, week_key)

        # Berechne einzelne Bonus-Komponenten
        person_week_data = data_store[week_key].get(person, {})

        # Gym Bonus (5x Gym = 2 Punkte)
        gym_count = 0
        for day in DAYS:
            day_data = person_week_data.get(day, {})
            gym_value = day_data.get('Gym', '')
            if gym_value and str(gym_value).upper() != 'R':
                try:
                    gym_val = float(gym_value)
                    if gym_val > 0:
                        gym_count += gym_val
                except:
                    pass

        gym_bonus = 2 if gym_count >= 5 else 0

        # Fehler Bonus (7 fehlerfreie Tage = 2 Punkte)
        error_free_days = 0
        for day in DAYS:
            day_data = person_week_data.get(day, {})
            fehler_value = day_data.get('Fehler', '')

            # Tag ist fehlerfrei wenn kein Wert oder Wert = 0
            is_error_free = True
            if fehler_value and fehler_value.strip():
                try:
                    fehler_val = float(fehler_value)
                    if fehler_val > 0:
                        is_error_free = False
                except:
                    # Ungültiger Wert = kein Fehler
                    pass

            if is_error_free:
                error_free_days += 1

        fehler_bonus = 2 if error_free_days == 7 else 0

        person_data['bonus'] = {
            'value': bonus_points if bonus_points > 0 else '',
            'points': bonus_points,
            'color': 'green' if bonus_points > 0 else 'white',
            'gym_bonus': gym_bonus,
            'fehler_bonus': fehler_bonus
        }

        week_data[person] = person_data

    # Scoreboard nicht mehr nötig für week view

    # Get current user info for personalization
    current_user = get_current_user()
    current_user_name = None

    # Map Firebase user to our system names (email-based mapping)
    if current_user and current_user.get('email'):
        email = current_user['email'].lower()
        if 'david' in email:
            current_user_name = 'David'
        elif 'cedric.müller3' in email or 'cedric.mueller3' in email:
            current_user_name = 'Müller'
        elif 'cédric.neuhaus' in email or 'cedric.neuhaus' in email:
            current_user_name = 'Cedric'

    return render_template('week.html',
                         week_num=week_num,
                         week_data=week_data,
                         names=NAMES,
                         categories=CATEGORIES,
                         days=DAYS,
                         current_user_name=current_user_name)

@app.route('/update_cell', methods=['POST'])
def update_cell():
    """Update einer einzelnen Zelle"""
    if not require_auth():
        return jsonify({'error': 'Authentication required'}), 401

    try:
        data = request.json
        week = data.get('week')
        person = data.get('person')
        day = data.get('day')
        category = data.get('category')
        value = data.get('value', '')

        # Validierung und Auto-Load der Woche falls nicht im data_store
        if week not in data_store:
            # Versuche Woche aus der Datenbank zu laden
            week_data_from_db = get_week_data(week)
            if not week_data_from_db:
                return jsonify({'error': 'Invalid week'}), 400
            else:
                # Füge geladene Daten zum data_store hinzu
                data_store[week] = week_data_from_db

        if person not in NAMES or day not in DAYS or category not in CATEGORIES:
            return jsonify({'error': 'Invalid parameters'}), 400

        # Gym 'R' Validierung
        if category == 'Gym' and not validate_gym_r_entry(value, person, week):
            return jsonify({'error': 'Gym "R" nur 1x pro Woche möglich'}), 400

        # Sicherstellen, dass die Datenstruktur vollständig ist
        if person not in data_store[week]:
            data_store[week][person] = {}
        if day not in data_store[week][person]:
            data_store[week][person][day] = {}
            # Initialisiere alle Kategorien für diesen Tag falls noch nicht vorhanden
            for cat in CATEGORIES:
                if cat not in data_store[week][person][day]:
                    data_store[week][person][day][cat] = ''

        # Update Daten
        data_store[week][person][day][category] = value

        # Speichere auch in der Datenbank
        update_entry(week, person, day, category, value)

        # Berechne neue Werte
        if category == 'Fehler':
            points = calculate_fehler_points_for_day(person, day, week)
            color = get_cell_color(category, value, person, day, week)
        else:
            points = calculate_points(category, value)
            color = get_cell_color(category, value)
        daily_total = calculate_daily_total(person, day, week)
        weekly_total = calculate_weekly_total(person, week)

        # Bonus neu berechnen
        bonus_points = calculate_weekly_bonus(person, week)

        # Berechne einzelne Bonus-Komponenten
        week_data = data_store.get(week, {})
        person_data = week_data.get(person, {})

        # Gym Bonus (5x Gym = 2 Punkte)
        gym_count = 0
        for day in DAYS:
            day_data = person_data.get(day, {})
            gym_value = day_data.get('Gym', '')
            if gym_value and str(gym_value).upper() != 'R':
                try:
                    gym_val = float(gym_value)
                    if gym_val > 0:
                        gym_count += gym_val
                except:
                    pass

        gym_bonus = 2 if gym_count >= 5 else 0

        # Fehler Bonus (7 fehlerfreie Tage = 2 Punkte)
        # ALLE 7 Tage müssen eingetragen UND 0 sein (grün)
        all_days_filled_and_zero = True
        for day in DAYS:
            day_data = person_data.get(day, {})
            fehler_value = day_data.get('Fehler', '')

            # Tag muss einen Wert haben UND dieser muss 0 sein
            if not fehler_value or fehler_value.strip() == '':
                all_days_filled_and_zero = False  # Kein Eintrag = kein Bonus
                break

            try:
                fehler_val = float(fehler_value)
                if fehler_val != 0:
                    all_days_filled_and_zero = False  # Nicht 0 = kein Bonus
                    break
            except:
                all_days_filled_and_zero = False  # Ungültiger Wert = kein Bonus
                break

        fehler_bonus = 2 if all_days_filled_and_zero else 0

        # Scoreboard nur für Dashboard berechnen, nicht für week view

        # Berechne Bonus für alle Personen (da sich Bedingungen ändern können)
        all_bonus_data = {}
        for p in NAMES:
            p_bonus_points = calculate_weekly_bonus(p, week)

            # Berechne einzelne Bonus-Komponenten für Person p
            p_week_data = data_store.get(week, {})
            p_person_data = p_week_data.get(p, {})

            # Gym Bonus für Person p
            p_gym_count = 0
            for day in DAYS:
                day_data = p_person_data.get(day, {})
                gym_value = day_data.get('Gym', '')
                if gym_value and str(gym_value).upper() != 'R':
                    try:
                        gym_val = float(gym_value)
                        if gym_val > 0:
                            p_gym_count += gym_val
                    except:
                        pass

            p_gym_bonus = 2 if p_gym_count >= 5 else 0

            # Fehler Bonus für Person p (7 fehlerfreie Tage = 2 Punkte)
            # ALLE 7 Tage müssen eingetragen UND 0 sein (grün)
            p_all_days_filled_and_zero = True
            for day in DAYS:
                day_data = p_person_data.get(day, {})
                fehler_value = day_data.get('Fehler', '')

                # Tag muss einen Wert haben UND dieser muss 0 sein
                if not fehler_value or fehler_value.strip() == '':
                    p_all_days_filled_and_zero = False  # Kein Eintrag = kein Bonus
                    break

                try:
                    fehler_val = float(fehler_value)
                    if fehler_val != 0:
                        p_all_days_filled_and_zero = False  # Nicht 0 = kein Bonus
                        break
                except:
                    p_all_days_filled_and_zero = False  # Ungültiger Wert = kein Bonus
                    break

            p_fehler_bonus = 2 if p_all_days_filled_and_zero else 0

            all_bonus_data[p] = {
                'bonus_points': p_bonus_points,
                'bonus_color': 'green' if p_bonus_points > 0 else 'white',
                'gym_bonus': p_gym_bonus,
                'fehler_bonus': p_fehler_bonus
            }

        response_data = {
            'points': points,
            'color': color,
            'daily_total': daily_total,
            'weekly_total': weekly_total,
            'bonus_points': bonus_points,
            'bonus_color': 'green' if bonus_points > 0 else 'white',
            'gym_bonus': gym_bonus,
            'fehler_bonus': fehler_bonus,
            'all_bonus_data': all_bonus_data
        }

        # Wenn Fehler-Kategorie geändert wurde, berechne alle Fehler-Zellen dieser Person neu
        if category == 'Fehler':
            fehler_updates = {}
            for fehler_day in DAYS:
                fehler_day_data = person_data.get(fehler_day, {})
                fehler_value = fehler_day_data.get('Fehler', '')

                # Neu berechnen für jeden Tag
                fehler_points = calculate_fehler_points_for_day(person, fehler_day, week)
                fehler_color = get_cell_color('Fehler', fehler_value, person, fehler_day, week)
                fehler_daily_total = calculate_daily_total(person, fehler_day, week)

                fehler_updates[fehler_day] = {
                    'points': fehler_points,
                    'color': fehler_color,
                    'daily_total': fehler_daily_total
                }

            response_data['fehler_updates'] = fehler_updates

        return jsonify(response_data)

    except Exception as e:
        # Log the error but don't fail the update
        print(f"⚠️  Cell update warning: {e}")

        # Return minimal successful response to prevent frontend errors
        return jsonify({
            'points': 0,
            'color': 'white',
            'daily_total': 0,
            'weekly_total': 0,
            'bonus_points': 0,
            'bonus_color': 'white',
            'gym_bonus': 0,
            'fehler_bonus': 0,
            'all_bonus_data': {},
            'scoreboard': [],
            'warning': 'Update completed with warnings'
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
    # Check if running on Railway
    if os.environ.get('DATABASE_URL'):
        print("🚀 Starting BrecherSystem on Railway with PostgreSQL...")
        try:
            initialize_data()
            stats = get_database_stats()
            print(f"📊 Database loaded: {stats['total_records']} records, {stats['total_weeks']} weeks")
        except Exception as e:
            print(f"⚠️ Database initialization warning: {e}")
            print("🔧 Continuing startup - database will be initialized on first request...")
    else:
        print("🚀 Starting BrecherSystem with SQLite Database...")
        initialize_data()
        stats = get_database_stats()
        print(f"📊 Database loaded: {stats['total_records']} records, {stats['total_weeks']} weeks")

    # Starte Server auf allen Netzwerk-Interfaces
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)