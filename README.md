# Laboratory Asset Tracker

A laboratory equipment tracking system with both the original Tkinter desktop interface and a Flask web interface. Authentication, inventory, reservations, quantity validation, approvals, checkouts, returns, and audit logging remain in reusable Python controllers.

## Features

- Student, technician, and administrator accounts
- Password validation and login lockout
- Asset inventory and quantity tracking
- Student borrow requests with approval workflow
- Technician/admin checkout and return handling
- Reservation and availability validation
- Maintenance and status tracking
- Activity history and CSV export
- SQLite local fallback
- Optional PostgreSQL backend for web deployment

## Project Structure

- `app.py` - original Tkinter desktop application
- `LoginView.py` and `StudentView.py` - desktop views
- `auth_controller.py` - authentication and account rules
- `database.py` - inventory and transaction rules
- `web_app.py` - Flask web adapter and routes
- `HTML/` - Jinja templates
- `CSS + JS/` - browser CSS and JavaScript
- `lab_assets.db` - local SQLite database
- `hardware_inventory.db` - database backup
- `requirements.txt` - Python dependencies
- `migrate_sqlite_to_postgres.py` - SQLite-to-PostgreSQL migration utility

## Setup

From PowerShell in the project directory:

```powershell
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
```

## Run the Web App

```powershell
& ".\.venv\Scripts\python.exe" web_app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

Use `Ctrl+C` in the server terminal to stop Flask.

## Run the Desktop App

```powershell
& ".\.venv\Scripts\python.exe" app.py
```

## Test

```powershell
& ".\.venv\Scripts\python.exe" -m pytest -q
```

## PostgreSQL

The web app uses SQLite by default. To use PostgreSQL, set `DATABASE_URL` to a reachable PostgreSQL database:

```powershell
$env:DATABASE_URL = "postgresql://USER:PASSWORD@HOST:5432/lab_assets"
```

Migrate the existing SQLite data before starting the web app:

```powershell
& ".\.venv\Scripts\python.exe" migrate_sqlite_to_postgres.py
& ".\.venv\Scripts\python.exe" web_app.py
```

See [POSTGRESQL_MIGRATION.md](POSTGRESQL_MIGRATION.md) for the full migration notes.

## Deploy to Render

This repository includes [render.yaml](render.yaml). In Render, create a new Blueprint from the GitHub repository and set `DATABASE_URL` to the Supabase PostgreSQL connection string in the service environment settings. Render generates `SECRET_KEY` automatically from the Blueprint configuration.

## Architecture

The presentation layer is replaceable. Tkinter and Flask provide different interfaces, while `AuthController` and `AssetStore` contain the shared authentication, database, and business rules. Browser JavaScript is limited to interface behavior and does not replace server-side validation.

The original desktop source is intentionally preserved so the working desktop application remains available as a reference and fallback during web development.
