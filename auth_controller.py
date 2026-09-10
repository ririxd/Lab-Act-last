import hashlib
import math
import os
import re
import sqlite3
import time

from database import DB_PATH


PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$")
EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


class AuthController:
    def __init__(self, database_path=DB_PATH):
        self.database_path = str(database_path or DB_PATH)
        self.initialize()

    def connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self):
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'USER',
                    failed_attempts INTEGER NOT NULL DEFAULT 0,
                    locked INTEGER NOT NULL DEFAULT 0,
                    locked_until REAL NOT NULL DEFAULT 0
                )
                """
            )
            columns = {row[1] for row in connection.execute("PRAGMA table_info(users)")}
            if "locked_until" not in columns:
                connection.execute("ALTER TABLE users ADD COLUMN locked_until REAL NOT NULL DEFAULT 0")

    @staticmethod
    def validate_password(password):
        if not PASSWORD_PATTERN.fullmatch(password or ""):
            return False, "Password must be at least 8 characters with an uppercase letter, number, and special character."
        return True, "Password is valid."

    @staticmethod
    def validate_email(email):
        email = (email or "").strip().lower()
        if not EMAIL_PATTERN.fullmatch(email):
            return False, "Enter a valid email address."
        return True, email

    @staticmethod
    def hash_password(password, salt=None):
        salt = salt or os.urandom(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200000)
        return salt.hex(), digest.hex()

    def register(self, username, email, password, role="STUDENT"):
        username = str(username or "").strip()
        role = str(role or "USER").strip().upper()
        valid, email_or_message = self.validate_email(email)
        if not username:
            return False, "Username is required."
        if not valid:
            return False, email_or_message
        valid, message = self.validate_password(str(password or ""))
        if not valid:
            return False, message
        if role == "TECHNICIAN" and not email_or_message.endswith("@admin.com"):
            return False, "Invalid email."
        if role == "ADMIN" and not email_or_message.endswith("@admin.com"):
            return False, f"{role.title()} registration requires an @admin.com email address."
        if role not in {"STUDENT", "TECHNICIAN", "ADMIN"}:
            return False, "Invalid role."
        salt, password_hash = self.hash_password(password)
        try:
            with self.connect() as connection:
                connection.execute(
                    "INSERT INTO users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, ?)",
                    (username, email_or_message, password_hash, salt, role),
                )
            return True, "Registration successful."
        except sqlite3.IntegrityError:
            return False, "Username or email is already registered."

    def login(self, username, password):
        username = str(username or "").strip()
        password = str(password or "")
        with self.connect() as connection:
            user = connection.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            if not user:
                return False, "Invalid username or password.", None
            if user["locked"]:
                remaining = math.ceil(user["locked_until"] - time.time())
                if remaining > 0:
                    return False, f"Account locked. Try again in {remaining} seconds.", None
                connection.execute("UPDATE users SET locked = 0, failed_attempts = 0, locked_until = 0 WHERE id = ?", (user["id"],))
            _, calculated_hash = self.hash_password(password, bytes.fromhex(user["salt"]))
            if calculated_hash != user["password_hash"]:
                attempts = user["failed_attempts"] + 1
                connection.execute(
                    "UPDATE users SET failed_attempts = ?, locked = ?, locked_until = ? WHERE id = ?",
                    (attempts, int(attempts >= 3), time.time() + 30 if attempts >= 3 else 0, user["id"]),
                )
                return False, "Invalid username or password." if attempts < 3 else "Account locked for 30 seconds after three failed attempts.", None
            connection.execute("UPDATE users SET failed_attempts = 0, locked = 0, locked_until = 0 WHERE id = ?", (user["id"],))
            return True, "Login successful.", dict(user)

    def lockout_remaining(self, username):
        with self.connect() as connection:
            user = connection.execute("SELECT locked_until FROM users WHERE username = ?", ((username or "").strip(),)).fetchone()
        return max(0, math.ceil(user["locked_until"] - time.time())) if user else 0
