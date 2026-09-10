from datetime import date
import csv
from pathlib import Path
import sqlite3


DB_PATH = Path(__file__).resolve().parent / "lab_assets.db"
CSV_REPORT_PATH = DB_PATH.parent / "asset_inventory_report.csv"
ASSET_STATUSES = ("Available", "Out of Stock", "Under Maintenance", "Lost", "Damaged", "Retired")


class AssetStore:
    def __init__(self, database_path=DB_PATH):
        self.database_path = str(database_path or DB_PATH)
        self.initialize()

    def connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self):
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL DEFAULT '',
                    salt TEXT NOT NULL DEFAULT '',
                    role TEXT NOT NULL DEFAULT 'STUDENT',
                    failed_attempts INTEGER NOT NULL DEFAULT 0,
                    locked INTEGER NOT NULL DEFAULT 0,
                    locked_until REAL NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS assets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_tag TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    quantity INTEGER NOT NULL CHECK (quantity > 0),
                    borrowed_quantity INTEGER NOT NULL DEFAULT 0 CHECK (borrowed_quantity >= 0),
                    location TEXT NOT NULL,
                    condition TEXT NOT NULL DEFAULT 'Good',
                    status TEXT NOT NULL DEFAULT 'Available',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS reservations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_id INTEGER NOT NULL,
                    borrower TEXT NOT NULL,
                    quantity INTEGER NOT NULL CHECK (quantity > 0),
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    reservation_location TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'ACTIVE',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE RESTRICT,
                    CHECK (end_date >= start_date)
                );
                CREATE TABLE IF NOT EXISTS checkouts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_id INTEGER NOT NULL,
                    borrower TEXT NOT NULL,
                    quantity INTEGER NOT NULL CHECK (quantity > 0),
                    checked_out_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    due_date TEXT NOT NULL,
                    checkout_location TEXT NOT NULL DEFAULT '',
                    due_time TEXT NOT NULL DEFAULT '17:00',
                    returned_at TEXT,
                    return_condition TEXT,
                    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE RESTRICT
                );
                CREATE TABLE IF NOT EXISTS maintenance_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_id INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT,
                    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE RESTRICT
                );
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            columns = {row[1] for row in connection.execute("PRAGMA table_info(assets)")}
            if "borrowed_quantity" not in columns:
                connection.execute("ALTER TABLE assets ADD COLUMN borrowed_quantity INTEGER NOT NULL DEFAULT 0")

            checkout_columns = {row[1] for row in connection.execute("PRAGMA table_info(checkouts)")}
            if "checkout_location" not in checkout_columns:
                connection.execute("ALTER TABLE checkouts ADD COLUMN checkout_location TEXT NOT NULL DEFAULT ''")
            if "due_time" not in checkout_columns:
                connection.execute("ALTER TABLE checkouts ADD COLUMN due_time TEXT NOT NULL DEFAULT '17:00'")

            reservation_columns = {row[1] for row in connection.execute("PRAGMA table_info(reservations)")}
            if "reservation_location" not in reservation_columns:
                connection.execute("ALTER TABLE reservations ADD COLUMN reservation_location TEXT NOT NULL DEFAULT ''")
            connection.execute("UPDATE reservations SET status = 'ACTIVE' WHERE status IS NULL OR status = ''")

    @staticmethod
    def parse_date(value, label):
        try:
            return date.fromisoformat((value or "").strip())
        except (TypeError, ValueError) as error:
            raise ValueError(f"{label} must use YYYY-MM-DD format.") from error

    def _audit(self, connection, actor, action, details):
        connection.execute(
            "INSERT INTO audit_log (actor, action, details) VALUES (?, ?, ?)",
            (actor, action, details),
        )

    def add_asset(self, asset_tag, name, category, quantity, location, condition="Good", borrowed_quantity=0):
        asset_tag, name, category, location = [str(value or "").strip() for value in (asset_tag, name, category, location)]
        if not all((asset_tag, name, category, location)):
            raise ValueError("Asset tag, name, category, and location are required.")
        try:
            quantity = int(quantity)
        except (TypeError, ValueError) as error:
            raise ValueError("Quantity must be a positive whole number.") from error
        if quantity < 1:
            raise ValueError("Quantity must be a positive whole number.")
        try:
            borrowed_quantity = int(borrowed_quantity)
        except (TypeError, ValueError) as error:
            raise ValueError("Borrowed quantity must be a non-negative whole number.") from error
        if borrowed_quantity < 0 or borrowed_quantity > quantity:
            raise ValueError("Borrowed quantity cannot exceed total quantity.")
        try:
            with self.connect() as connection:
                connection.execute(
                    "INSERT INTO assets (asset_tag, name, category, quantity, borrowed_quantity, location, condition) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (asset_tag, name, category, quantity, borrowed_quantity, location, condition or "Good"),
                )
                self._audit(connection, "system", "ASSET_ADDED", asset_tag)
        except sqlite3.IntegrityError as error:
            raise ValueError("Asset tag already exists.") from error

    def assets(self, search=""):
        term = f"%{(search or '').strip()}%"
        today = date.today().isoformat()
        with self.connect() as connection:
            return connection.execute(
                "SELECT a.id, a.asset_tag, a.name, a.category, a.quantity, "
                "a.borrowed_quantity + COALESCE((SELECT SUM(c.quantity) FROM checkouts c "
                "WHERE c.asset_id = a.id AND c.returned_at IS NULL), 0) AS borrowed_quantity, "
                "CASE WHEN a.status = 'Available' THEN MAX(0, a.quantity - "
                "a.borrowed_quantity - COALESCE((SELECT SUM(c.quantity) FROM checkouts c "
                "WHERE c.asset_id = a.id AND c.returned_at IS NULL), 0) - "
                "COALESCE((SELECT SUM(r.quantity) FROM reservations r WHERE r.asset_id = a.id "
                "AND r.status = 'ACTIVE' AND r.start_date <= ? AND r.end_date >= ?), 0) - "
                "COALESCE((SELECT SUM(c.quantity) FROM checkouts c WHERE c.asset_id = a.id "
                "AND c.returned_at IS NULL), 0)) ELSE 0 END AS borrowable_quantity, "
                "a.location, a.condition, CASE WHEN a.status = 'Available' AND "
                "a.quantity - a.borrowed_quantity - COALESCE((SELECT SUM(c.quantity) FROM checkouts c "
                "WHERE c.asset_id = a.id AND c.returned_at IS NULL), 0) - "
                "COALESCE((SELECT SUM(r.quantity) FROM reservations r WHERE r.asset_id = a.id "
                "AND r.status = 'ACTIVE' AND r.start_date <= ? AND r.end_date >= ?), 0) <= 0 "
                "THEN 'Out of Stock' ELSE a.status END AS status FROM assets a "
                "WHERE asset_tag LIKE ? OR name LIKE ? OR category LIKE ? ORDER BY name",
                (today, today, today, today, term, term, term),
            ).fetchall()

    def _allocated(self, connection, asset_id, start_date, end_date):
        reserved = connection.execute(
            "SELECT COALESCE(SUM(quantity), 0) FROM reservations "
            "WHERE asset_id = ? AND status = 'ACTIVE' AND start_date <= ? AND end_date >= ?",
            (asset_id, end_date, start_date),
        ).fetchone()[0]
        checked_out = connection.execute(
            "SELECT COALESCE(SUM(quantity), 0) FROM checkouts WHERE asset_id = ? AND returned_at IS NULL",
            (asset_id,),
        ).fetchone()[0]
        baseline = connection.execute("SELECT borrowed_quantity FROM assets WHERE id = ?", (asset_id,)).fetchone()[0]
        return int(baseline) + int(reserved) + int(checked_out)

    def reserve(self, asset_id, borrower, quantity, start_date, end_date, purpose, requires_approval=False):
        start = self.parse_date(start_date, "Start date")
        end = self.parse_date(end_date, "End date")
        if end < start:
            raise ValueError("End date cannot be before start date.")
        borrower, purpose = str(borrower or "").strip(), str(purpose or "").strip()
        if not borrower or not purpose:
            raise ValueError("Borrower and purpose are required.")
        try:
            quantity = int(quantity)
        except (TypeError, ValueError) as error:
            raise ValueError("Quantity must be a positive whole number.") from error
        if quantity < 1:
            raise ValueError("Quantity must be a positive whole number.")

        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            asset = connection.execute("SELECT quantity, status FROM assets WHERE id = ?", (asset_id,)).fetchone()
            if not asset:
                raise ValueError("Asset not found.")
            if asset["status"] != "Available":
                raise ValueError("This asset is not available for reservation.")

            start_iso = start.isoformat()
            end_iso = end.isoformat()
            reserved = connection.execute(
                "SELECT COALESCE(SUM(quantity), 0) FROM reservations "
                "WHERE asset_id = ? AND status IN ('ACTIVE', 'PENDING') AND start_date <= ? AND end_date >= ?",
                (asset_id, end_iso, start_iso),
            ).fetchone()[0]
            checked_out = connection.execute(
                "SELECT COALESCE(SUM(quantity), 0) FROM checkouts WHERE asset_id = ? AND returned_at IS NULL",
                (asset_id,),
            ).fetchone()[0]
            baseline = connection.execute("SELECT borrowed_quantity FROM assets WHERE id = ?", (asset_id,)).fetchone()[0]
            if int(baseline) + int(reserved) + int(checked_out) + quantity > asset["quantity"]:
                raise ValueError("Not enough available quantity for those dates.")

            status = "PENDING" if requires_approval else "ACTIVE"
            cursor = connection.execute(
                "INSERT INTO reservations (asset_id, borrower, quantity, start_date, end_date, purpose, reservation_location, status) "
                "SELECT ?, ?, ?, ?, ?, ?, location, ? FROM assets WHERE id = ?",
                (asset_id, borrower, quantity, start_iso, end_iso, purpose, status, asset_id),
            )
            self._audit(connection, borrower, "RESERVATION_CREATED", f"asset_id={asset_id}, status={status}")
            return cursor.lastrowid

    def approve_reservation(self, reservation_id, approved=True):
        with self.connect() as connection:
            reservation = connection.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,)).fetchone()
            if not reservation:
                raise ValueError("Reservation not found.")
            status = "ACTIVE" if approved else "REJECTED"
            connection.execute("UPDATE reservations SET status = ? WHERE id = ?", (status, reservation_id))
            self._audit(connection, "admin", "RESERVATION_UPDATED", f"reservation_id={reservation_id}, status={status}")
            return status

    def pending_reservations(self):
        with self.connect() as connection:
            return connection.execute(
                "SELECT r.id, a.asset_tag, a.name, r.borrower, r.quantity, r.start_date, r.end_date, r.purpose "
                "FROM reservations r JOIN assets a ON a.id = r.asset_id WHERE r.status = 'PENDING' ORDER BY r.start_date"
            ).fetchall()

    def reservations(self):
        with self.connect() as connection:
            return connection.execute(
                "SELECT r.id, a.asset_tag, a.name, r.borrower, r.quantity, r.start_date, r.end_date, r.purpose "
                "FROM reservations r JOIN assets a ON a.id = r.asset_id WHERE r.status = 'ACTIVE' ORDER BY r.start_date"
            ).fetchall()

    def checkout(self, asset_id, borrower, quantity, due_date, checkout_location, due_time="17:00"):
        due = self.parse_date(due_date, "Due date")
        borrower = str(borrower or "").strip()
        checkout_location = str(checkout_location or "").strip()
        if not borrower or not checkout_location:
            raise ValueError("Borrower and checkout location are required.")
        try:
            due_time = due_time.strip()
            if len(due_time) != 5 or due_time[2] != ":" or not (0 <= int(due_time[:2]) <= 23 and 0 <= int(due_time[3:]) <= 59):
                raise ValueError
        except (AttributeError, TypeError, ValueError) as error:
            raise ValueError("Return time must use HH:MM format.") from error
        try:
            quantity = int(quantity)
        except (TypeError, ValueError) as error:
            raise ValueError("Quantity must be a positive whole number.") from error
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            asset = connection.execute("SELECT quantity, status, location FROM assets WHERE id = ?", (asset_id,)).fetchone()
            if not asset or asset["status"] != "Available":
                raise ValueError("This asset is not available for checkout.")
            borrower_record = connection.execute("SELECT role FROM users WHERE username = ?", (borrower,)).fetchone()
            if not borrower_record or borrower_record["role"] != "STUDENT":
                raise ValueError("Only registered students can be assigned as borrowers.")
            if asset["location"] != checkout_location:
                raise ValueError("Checkout location must match the asset's registered location.")
            reservation = connection.execute(
                "SELECT DISTINCT reservation_location FROM reservations WHERE asset_id = ? "
                "AND status = 'ACTIVE' AND start_date <= ? AND end_date >= ?",
                (asset_id, date.today().isoformat(), due.isoformat()),
            ).fetchall()
            reservation_locations = {row["reservation_location"] for row in reservation if row["reservation_location"]}
            if reservation_locations and checkout_location not in reservation_locations:
                raise ValueError("Checkout location does not match the reservation location.")
            if quantity < 1 or self._allocated(connection, asset_id, date.today().isoformat(), due.isoformat()) + quantity > asset["quantity"]:
                raise ValueError("No available quantity remains for checkout.")
            connection.execute(
                "INSERT INTO checkouts (asset_id, borrower, quantity, due_date, checkout_location, due_time) VALUES (?, ?, ?, ?, ?, ?)",
                (asset_id, borrower, quantity, due.isoformat(), checkout_location, due_time),
            )
            self._audit(connection, borrower, "ASSET_CHECKED_OUT", f"asset_id={asset_id}")

    def return_checkout(self, checkout_id, return_condition="Good"):
        with self.connect() as connection:
            checkout = connection.execute(
                "SELECT borrower FROM checkouts WHERE id = ? AND returned_at IS NULL", (checkout_id,)
            ).fetchone()
            if not checkout:
                raise ValueError("Active checkout not found.")
            connection.execute(
                "UPDATE checkouts SET returned_at = CURRENT_TIMESTAMP, return_condition = ? WHERE id = ?",
                (return_condition or "Good", checkout_id),
            )
            self._audit(connection, checkout["borrower"], "ASSET_RETURNED", f"checkout_id={checkout_id}")

    def active_checkouts(self):
        with self.connect() as connection:
            return connection.execute(
                "SELECT c.id, a.asset_tag, a.name, c.borrower, c.quantity, c.due_date, c.checkout_location, c.due_time, "
                "CASE WHEN a.status = 'Available' AND a.quantity - a.borrowed_quantity - "
                "COALESCE((SELECT SUM(active.quantity) FROM checkouts active WHERE active.asset_id = a.id "
                "AND active.returned_at IS NULL), 0) <= 0 THEN 'Out of Stock' ELSE a.status END AS status "
                "FROM checkouts c JOIN assets a ON a.id = c.asset_id WHERE c.returned_at IS NULL ORDER BY c.due_date"
            ).fetchall()

    def borrower_checkouts(self, borrower):
        with self.connect() as connection:
            return connection.execute(
                "SELECT c.id, a.asset_tag, a.name, c.quantity, c.checked_out_at, c.due_date, c.due_time, c.checkout_location "
                "FROM checkouts c JOIN assets a ON a.id = c.asset_id "
                "WHERE c.borrower = ? AND c.returned_at IS NULL ORDER BY c.due_date",
                (borrower,),
            ).fetchall()

    def registered_students(self):
        with self.connect() as connection:
            table_exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'users'"
            ).fetchone()
            if not table_exists:
                return []
            return [row[0] for row in connection.execute(
                "SELECT username FROM users WHERE role = 'STUDENT' ORDER BY username"
            ).fetchall()]

    def activity_log(self, limit=200):
        with self.connect() as connection:
            return connection.execute(
                "SELECT created_at, actor, action, details FROM audit_log ORDER BY id DESC LIMIT ?",
                (int(limit),),
            ).fetchall()

    def export_inventory_csv(self, actor, report_path=CSV_REPORT_PATH):
        with self.connect() as connection:
            user = connection.execute("SELECT role FROM users WHERE username = ?", (str(actor or "").strip(),)).fetchone()
            if not user or user["role"] not in {"ADMIN", "TECHNICIAN"}:
                raise PermissionError("Only management users can export inventory reports.")
        rows = self.assets()
        target = Path(report_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", newline="", encoding="utf-8") as report_file:
            writer = csv.writer(report_file)
            writer.writerow(("ID", "Asset Tag", "Name", "Category", "Total Quantity", "Borrowed", "Borrowable", "Location", "Condition", "Status"))
            writer.writerows(tuple(row) for row in rows)
        return str(target)

    def set_maintenance(self, asset_id, description):
        description = str(description or "").strip()
        if not description:
            raise ValueError("Maintenance description is required.")
        with self.connect() as connection:
            connection.execute("UPDATE assets SET status = 'Under Maintenance' WHERE id = ?", (asset_id,))
            connection.execute("INSERT INTO maintenance_records (asset_id, description) VALUES (?, ?)", (asset_id, description))
            self._audit(connection, "system", "MAINTENANCE_STARTED", f"asset_id={asset_id}")

    def mark_available(self, asset_id):
        self.update_status(asset_id, "Available")

    def update_status(self, asset_id, status):
        status = str(status or "").strip()
        if status not in ASSET_STATUSES:
            raise ValueError("Choose a valid asset status.")
        with self.connect() as connection:
            asset = connection.execute("SELECT asset_tag FROM assets WHERE id = ?", (asset_id,)).fetchone()
            if not asset:
                raise ValueError("Asset not found.")
            connection.execute("UPDATE assets SET status = ?, condition = ? WHERE id = ?", (status, status, asset_id))
            if status == "Available":
                connection.execute(
                    "UPDATE maintenance_records SET completed_at = CURRENT_TIMESTAMP WHERE asset_id = ? AND completed_at IS NULL",
                    (asset_id,),
                )
            self._audit(connection, "system", "ASSET_STATUS_UPDATED", f"asset={asset['asset_tag']}, status={status}")

