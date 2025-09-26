import sqlite3
import json
import os
from datetime import datetime
from config import Config

# Initialize configuration
config = Config()

# Database path for SQLite
DATABASE_PATH = config.database_config['path'] if config.database_config['type'] == 'sqlite' else None

# PostgreSQL connection
if config.use_postgresql:
    import psycopg
    from urllib.parse import urlparse

def get_db_connection():
    """Get database connection based on configuration"""
    if config.use_postgresql:
        return psycopg.connect(config.database_config['url'])
    else:
        return sqlite3.connect(DATABASE_PATH)

def execute_sql(sql, params=None, fetch=False):
    """Execute SQL with proper parameter binding for both databases"""
    if config.use_postgresql:
        # Convert SQLite-style ? placeholders to PostgreSQL %s
        pg_sql = sql.replace('?', '%s')
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(pg_sql, params or ())
        if fetch:
            result = cursor.fetchall()
        else:
            result = None
        conn.commit()
        conn.close()
        return result
    else:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, params or ())
        if fetch:
            result = cursor.fetchall()
        else:
            result = None
        conn.commit()
        conn.close()
        return result

def init_database():
    """Initialize the database with required tables."""

    # Create main data table - PostgreSQL and SQLite compatible
    if config.use_postgresql:
        create_table_sql = '''
            CREATE TABLE IF NOT EXISTS brecher_data (
                id SERIAL PRIMARY KEY,
                week TEXT NOT NULL,
                person TEXT NOT NULL,
                day TEXT NOT NULL,
                category TEXT NOT NULL,
                value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(week, person, day, category)
            )
        '''
    else:
        create_table_sql = '''
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
        '''

    execute_sql(create_table_sql)

    # Create index for better performance
    execute_sql('''
        CREATE INDEX IF NOT EXISTS idx_week_person_day
        ON brecher_data(week, person, day)
    ''')

    db_info = config.database_config['url'] if config.use_postgresql else DATABASE_PATH
    print(f"✅ Database initialized: {db_info}")

def migrate_json_to_database(json_file='brecher_data.json'):
    """Migrate existing JSON data to database (only if database is empty)."""
    if not os.path.exists(json_file):
        print(f"ℹ️ JSON file {json_file} not found - using database only")
        return

    # Check if database already has data
    existing_records = execute_sql('SELECT COUNT(*) FROM brecher_data', fetch=True)[0][0]

    if existing_records > 0:
        print(f"ℹ️ Database already contains {existing_records} records - skipping migration")
        return

    # Load JSON data
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    migrated_records = 0

    for week, week_data in data.items():
        for person, person_data in week_data.items():
            for day, day_data in person_data.items():
                for category, value in day_data.items():
                    # Insert record (only if database was empty)
                    execute_sql('''
                        INSERT INTO brecher_data
                        (week, person, day, category, value, updated_at)
                        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (week, person, day, category, str(value) if value else ''))
                    migrated_records += 1

    print(f"✅ Migrated {migrated_records} records from JSON to database")

def get_all_data():
    """Get all data in the original JSON format."""
    rows = execute_sql('''
        SELECT week, person, day, category, value
        FROM brecher_data
        ORDER BY week, person, day, category
    ''', fetch=True)

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
    saved_records = 0

    for week, week_data in data.items():
        for person, person_data in week_data.items():
            for day, day_data in person_data.items():
                for category, value in day_data.items():
                    execute_sql('''
                        INSERT OR REPLACE INTO brecher_data
                        (week, person, day, category, value, updated_at)
                        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (week, person, day, category, str(value) if value else ''))
                    saved_records += 1

    return saved_records

def get_week_data(week):
    """Get data for a specific week."""
    rows = execute_sql('''
        SELECT person, day, category, value
        FROM brecher_data
        WHERE week = ?
        ORDER BY person, day, category
    ''', (week,), fetch=True)

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
    execute_sql('''
        INSERT OR REPLACE INTO brecher_data
        (week, person, day, category, value, updated_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (week, person, day, category, str(value) if value else ''))

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
    weeks_raw = execute_sql('SELECT DISTINCT week FROM brecher_data ORDER BY week', fetch=True)

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
    total_records = execute_sql('SELECT COUNT(*) FROM brecher_data', fetch=True)[0][0]
    total_weeks = execute_sql('SELECT COUNT(DISTINCT week) FROM brecher_data', fetch=True)[0][0]
    total_persons = execute_sql('SELECT COUNT(DISTINCT person) FROM brecher_data', fetch=True)[0][0]
    last_updated = execute_sql('SELECT MAX(updated_at) FROM brecher_data', fetch=True)[0][0]

    db_info = config.database_config['url'] if config.use_postgresql else DATABASE_PATH
    return {
        'total_records': total_records,
        'total_weeks': total_weeks,
        'total_persons': total_persons,
        'last_updated': last_updated,
        'database_file': db_info
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