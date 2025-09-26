#!/usr/bin/env python3
"""
Migration script to transfer local data to Railway PostgreSQL database.
Run this once after Railway deployment to migrate your local data.
"""

import json
import os
from database import save_data, get_database_stats, init_database

def migrate_data():
    print('🚀 Starting BrecherSystem data migration to Railway...')

    # Check if we're on Railway (has DATABASE_URL)
    if not os.environ.get('DATABASE_URL'):
        print('❌ ERROR: DATABASE_URL not found. This script should run on Railway.')
        return

    print('✅ PostgreSQL DATABASE_URL detected')

    # Initialize database
    print('📊 Initializing database...')
    init_database()

    # Check if data already exists
    stats = get_database_stats()
    if stats['total_records'] > 0:
        print(f'ℹ️ Database already has {stats["total_records"]} records. Skipping migration.')
        return

    # Load backup file
    backup_file = 'railway_migration.json'
    if not os.path.exists(backup_file):
        print(f'❌ ERROR: Backup file {backup_file} not found!')
        return

    print(f'📄 Loading backup from {backup_file}...')
    with open(backup_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f'📊 Found data for {len(data)} weeks')

    # Migrate data
    print('⬆️ Migrating data to PostgreSQL...')
    records = save_data(data)
    print(f'✅ Successfully migrated {records} records!')

    # Show final stats
    final_stats = get_database_stats()
    print(f'🎉 Migration complete!')
    print(f'📊 Final database: {final_stats["total_records"]} records across {final_stats["total_weeks"]} weeks for {final_stats["total_persons"]} persons')

if __name__ == '__main__':
    migrate_data()