"""
Simple SQL migration runner.

Usage:
    python migrate.py

Applies any .sql files in the migrations/ folder that haven't been run yet.
Tracks applied migrations in a `schema_migrations` table in the database.
"""

import os
import sys
import pymysql
import TranslatorApp.Configuration as Configuration

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), 'migrations')


def get_connection():
    return pymysql.connect(
        host=Configuration.dbHost,
        user=Configuration.dbUser,
        password=Configuration.dbPassword,
        db=Configuration.dbDatabase,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


def ensure_migrations_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS `schema_migrations` (
            `filename` VARCHAR(255) NOT NULL PRIMARY KEY,
            `applied_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)


def get_applied_migrations(cursor):
    cursor.execute("SELECT filename FROM `schema_migrations`")
    return {row['filename'] for row in cursor.fetchall()}


def get_pending_migrations(applied):
    all_files = sorted(f for f in os.listdir(MIGRATIONS_DIR) if f.endswith('.sql'))
    return [f for f in all_files if f not in applied]


def run_migration(cursor, filename):
    filepath = os.path.join(MIGRATIONS_DIR, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        sql = f.read()

    # Execute each statement separated by semicolons
    for statement in sql.split(';'):
        statement = statement.strip()
        if statement and not statement.startswith('--'):
            cursor.execute(statement)

    cursor.execute(
        "INSERT INTO `schema_migrations` (filename) VALUES (%s)", (filename,)
    )


if __name__ == '__main__':
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            ensure_migrations_table(cursor)
            applied = get_applied_migrations(cursor)
            pending = get_pending_migrations(applied)

            if not pending:
                print("No pending migrations.")
                sys.exit(0)

            for filename in pending:
                print(f"Applying {filename}...")
                run_migration(cursor, filename)
                print(f"  Done.")

            connection.commit()
            print(f"\n{len(pending)} migration(s) applied successfully.")

    except Exception as e:
        connection.rollback()
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        connection.close()
