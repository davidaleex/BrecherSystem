import sqlite3
import json
import os
from datetime import datetime

DATABASE_PATH = 'brecher_system.db'

def init_database():
    """Initialize the SQLite database with required tables."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Create main data table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS brecher_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week TEXT NOT NULL,
            person TEXT NOT NULL,
            day TEXT NOT NULL,
            category TEXT NOT NULL,
            value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(week, person, day, category)
        )
    ''')

    # Create index for better performance
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_week_person_day
        ON brecher_data(week, person, day)
    ''')

    conn.commit()
    conn.close()
    print(f"✅ Database initialized: {DATABASE_PATH}")

def migrate_json_to_database(json_file='brecher_data.json'):
    """Migrate existing JSON data to SQLite database."""
    if not os.path.exists(json_file):
        print(f"❌ JSON file {json_file} not found")
        return

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Load JSON data
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    migrated_records = 0

    for week, week_data in data.items():
        for person, person_data in week_data.items():
            for day, day_data in person_data.items():
                for category, value in day_data.items():
                    # Insert or update record
                    cursor.execute('''
                        INSERT OR REPLACE INTO brecher_data
                        (week, person, day, category, value, updated_at)
                        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (week, person, day, category, str(value) if value else ''))
                    migrated_records += 1

    conn.commit()
    conn.close()
    print(f"✅ Migrated {migrated_records} records from JSON to database")

def get_all_data():
    """Get all data in the original JSON format."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT week, person, day, category, value
        FROM brecher_data
        ORDER BY week, person, day, category
    ''')

    rows = cursor.fetchall()
    conn.close()

    # Rebuild nested structure
    data = {}
    for week, person, day, category, value in rows:
        if week not in data:
            data[week] = {}
        if person not in data[week]:
            data[week][person] = {}
        if day not in data[week][person]:
            data[week][person][day] = {}
        data[week][person][day][category] = value

    return data

def save_data(data):
    """Save data to database."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    saved_records = 0

    for week, week_data in data.items():
        for person, person_data in week_data.items():
            for day, day_data in person_data.items():
                for category, value in day_data.items():
                    cursor.execute('''
                        INSERT OR REPLACE INTO brecher_data
                        (week, person, day, category, value, updated_at)
                        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (week, person, day, category, str(value) if value else ''))
                    saved_records += 1

    conn.commit()
    conn.close()
    return saved_records

def get_week_data(week):
    """Get data for a specific week."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT person, day, category, value
        FROM brecher_data
        WHERE week = ?
        ORDER BY person, day, category
    ''', (week,))

    rows = cursor.fetchall()
    conn.close()

    # Rebuild structure for this week
    week_data = {}
    for person, day, category, value in rows:
        if person not in week_data:
            week_data[person] = {}
        if day not in week_data[person]:
            week_data[person][day] = {}
        week_data[person][day][category] = value

    return week_data

def update_entry(week, person, day, category, value):
    """Update a specific entry."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR REPLACE INTO brecher_data
        (week, person, day, category, value, updated_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (week, person, day, category, str(value) if value else ''))

    conn.commit()
    conn.close()

def backup_to_json(filename=None):
    """Backup database to JSON file."""
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"brecher_backup_{timestamp}.json"

    data = get_all_data()

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Database backed up to {filename}")
    return filename

def get_all_weeks():
    """Get all available weeks from database."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT DISTINCT week FROM brecher_data ORDER BY week')
    weeks_raw = cursor.fetchall()
    conn.close()

    # Extrahiere Wochennummern aus "KW39" Format
    weeks = []
    for week_tuple in weeks_raw:
        week_str = week_tuple[0]
        if week_str.startswith('KW'):
            try:
                week_num = int(week_str[2:])  # "KW39" -> 39
                weeks.append(week_num)
            except ValueError:
                continue

    return sorted(weeks)

def get_database_stats():
    """Get database statistics."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM brecher_data')
    total_records = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(DISTINCT week) FROM brecher_data')
    total_weeks = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(DISTINCT person) FROM brecher_data')
    total_persons = cursor.fetchone()[0]

    cursor.execute('SELECT MAX(updated_at) FROM brecher_data')
    last_updated = cursor.fetchone()[0]

    conn.close()

    return {
        'total_records': total_records,
        'total_weeks': total_weeks,
        'total_persons': total_persons,
        'last_updated': last_updated,
        'database_file': DATABASE_PATH
    }

if __name__ == "__main__":
    # Initialize database and migrate from JSON
    print("🚀 Setting up BrecherSystem Database...")
    init_database()
    migrate_json_to_database()

    # Show stats
    stats = get_database_stats()
    print(f"\n📊 Database Stats:")
    print(f"   Records: {stats['total_records']}")
    print(f"   Weeks: {stats['total_weeks']}")
    print(f"   Persons: {stats['total_persons']}")
    print(f"   Last Updated: {stats['last_updated']}")