#!/usr/bin/env python3
"""Apply database migrations safely."""

import sqlite3
import os
from pathlib import Path

DATABASE_PATH = "data/juan365_socmed.db"
MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def get_applied_migrations(conn):
    """Get list of already applied migrations."""
    cursor = conn.cursor()
    # Check if migrations table exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='migrations'
    """)
    if not cursor.fetchone():
        # Create migrations tracking table
        cursor.execute("""
            CREATE TABLE migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL UNIQUE,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        return set()

    cursor.execute("SELECT filename FROM migrations")
    return set(row[0] for row in cursor.fetchall())


def apply_migration(conn, migration_file: Path):
    """Apply a single migration file."""
    print(f"Applying migration: {migration_file.name}")

    with open(migration_file, 'r') as f:
        sql = f.read()

    cursor = conn.cursor()

    # For ALTER TABLE statements, execute them one at a time
    # since SQLite doesn't support multiple in one executescript
    statements = [s.strip() for s in sql.split(';') if s.strip()]

    for stmt in statements:
        if stmt.startswith('--'):
            continue
        try:
            cursor.execute(stmt)
            print(f"  OK: {stmt[:60]}...")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"  SKIP (already exists): {stmt[:60]}...")
            elif "already exists" in str(e).lower():
                print(f"  SKIP (already exists): {stmt[:60]}...")
            else:
                print(f"  ERROR: {e}")
                raise

    # Record migration as applied
    cursor.execute(
        "INSERT OR IGNORE INTO migrations (filename) VALUES (?)",
        (migration_file.name,)
    )
    conn.commit()
    print(f"  Migration {migration_file.name} applied successfully!")


def main():
    print("=" * 60)
    print("Database Migration Tool")
    print("=" * 60)

    if not os.path.exists(DATABASE_PATH):
        print(f"Database not found at {DATABASE_PATH}")
        print("Run 'python database.py init' first.")
        return

    conn = sqlite3.connect(DATABASE_PATH)

    # Get applied migrations
    applied = get_applied_migrations(conn)
    print(f"\nAlready applied: {len(applied)} migrations")

    # Get all migration files
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    print(f"Available migrations: {len(migration_files)}")

    # Apply pending migrations
    pending = [f for f in migration_files if f.name not in applied]

    if not pending:
        print("\nNo pending migrations.")
    else:
        print(f"\nApplying {len(pending)} pending migrations...")
        for migration_file in pending:
            apply_migration(conn, migration_file)

    conn.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
