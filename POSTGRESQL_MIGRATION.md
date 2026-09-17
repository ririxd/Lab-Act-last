# PostgreSQL Migration

The Flask application supports PostgreSQL through the `DATABASE_URL` environment variable. SQLite remains available when a test passes a `.db` path or when `DATABASE_URL` is not set, so the original desktop application and existing tests remain usable.

## Install dependencies

```powershell
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
```

## Configure PostgreSQL

Copy `.env.example` to `.env` and set a PostgreSQL connection URL before starting the web app. The `.env` file is ignored by Git.

```powershell
Copy-Item .env.example .env
```

Edit `.env` and replace the placeholders with the Supabase connection string and a new secret. The local Flask app and migration script load these values automatically.

The database and user must already exist. The application creates its tables on startup.

## Migrate the existing SQLite data

Run the migration once, before starting the PostgreSQL-backed app:

```powershell
& ".\.venv\Scripts\python.exe" migrate_sqlite_to_postgres.py
```

The source is `lab_assets.db` by default. The migration preserves users, assets, reservations, checkouts, maintenance records, and audit logs, including their IDs. Run it against an empty PostgreSQL database to avoid duplicate-key conflicts.

If a previous migration partially populated PostgreSQL, rerun with the explicit reset option. This clears the target tables before importing the SQLite backup:

```powershell
& ".\.venv\Scripts\python.exe" migrate_sqlite_to_postgres.py --reset
```

## Start the web app

```powershell
& ".\.venv\Scripts\python.exe" web_app.py
```

The desktop Tkinter app continues to use its local SQLite fallback through `app.py`.
