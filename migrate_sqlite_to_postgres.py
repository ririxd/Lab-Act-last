from __future__ import annotations

import os
import sqlite3

from db_compat import DatabaseConnection, close_connection
from database import DB_PATH, AssetStore


TABLES = (
    ("users", ("id", "username", "email", "password_hash", "salt", "role", "failed_attempts", "locked", "locked_until")),
    ("assets", ("id", "asset_tag", "name", "category", "quantity", "borrowed_quantity", "location", "condition", "status", "created_at")),
    ("reservations", ("id", "asset_id", "borrower", "quantity", "start_date", "end_date", "purpose", "reservation_location", "status", "created_at")),
    ("checkouts", ("id", "asset_id", "borrower", "quantity", "checked_out_at", "due_date", "checkout_location", "due_time", "returned_at", "return_condition")),
    ("maintenance_records", ("id", "asset_id", "description", "started_at", "completed_at")),
    ("audit_log", ("id", "actor", "action", "details", "created_at")),
)


def migrate(source_path=DB_PATH, target_url=None):
    target_url = target_url or os.getenv("DATABASE_URL")
    if not target_url or not target_url.startswith(("postgres://", "postgresql://")):
        raise ValueError("Set DATABASE_URL to a PostgreSQL connection URL before migrating.")

    source = sqlite3.connect(str(source_path))
    source.row_factory = sqlite3.Row
    target_manager = DatabaseConnection(target_url, DB_PATH)
    target = target_manager.connect()
    try:
        AssetStore(target_url)
        for table, columns in TABLES:
            rows = source.execute(f"SELECT {', '.join(columns)} FROM {table}").fetchall()
            placeholders = ", ".join("?" for _ in columns)
            column_list = ", ".join(columns)
            for row in rows:
                target.execute(
                    f"INSERT INTO {table} ({column_list}) VALUES ({placeholders})",
                    tuple(row[column] for column in columns),
                )
            if rows:
                target.execute(
                    f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), (SELECT MAX(id) FROM {table}), true)"
                )
        target.connection.commit()
    finally:
        close_connection(target)
        source.close()


if __name__ == "__main__":
    migrate()
    print("SQLite data migrated to PostgreSQL.")
