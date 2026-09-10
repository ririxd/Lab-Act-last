import auth_controller
from auth_controller import AuthController
from database import AssetStore


def test_register_and_login(tmp_path):
    auth = AuthController(tmp_path / "auth.db")
    ok, message = auth.register("admin", "admin@admin.com", "Secure123!", "ADMIN")
    assert ok is True, message

    ok, message, user = auth.login("admin", "Secure123!")
    assert ok is True, message
    assert user["role"] == "ADMIN"


def test_register_accepts_numeric_usernames_and_nested_export_dir(tmp_path):
    auth = AuthController(tmp_path / "auth.db")
    ok, message = auth.register(123, "numeric@example.com", "Secure123!", "STUDENT")
    assert ok is True, message

    ok, message, user = auth.login("123", "Secure123!")
    assert ok is True, message
    assert user["username"] == "123"

    store = AssetStore(tmp_path / "assets.db")
    admin = AuthController(tmp_path / "assets.db")
    admin.register("manager", "manager@admin.com", "Secure123!", "ADMIN")
    store.add_asset("LAB-100", "Pressure Gauge", "Safety", 1, "Room 101")
    report_path = tmp_path / "reports" / "nested" / "inventory.csv"
    saved = store.export_inventory_csv("manager", report_path)
    assert report_path.exists()
    assert saved == str(report_path)


def test_wrong_password_locks_account_for_thirty_seconds(tmp_path, monkeypatch):
    auth = AuthController(tmp_path / "auth.db")
    auth.register("user", "user@example.com", "Secure123!")

    current_time = [1_700_000_000.0]
    monkeypatch.setattr(auth_controller.time, "time", lambda: current_time[0])
    for _ in range(3):
        ok, _, _ = auth.login("user", "Wrong123!")
        assert ok is False

    ok, message, _ = auth.login("user", "Secure123!")
    assert ok is False
    assert "30 seconds" in message

    current_time[0] += 31
    ok, message, user = auth.login("user", "Secure123!")
    assert ok is True, message
    assert user["username"] == "user"


def test_duplicate_email_is_rejected(tmp_path):
    auth = AuthController(tmp_path / "auth.db")
    auth.register("first", "same@example.com", "Secure123!")
    ok, message = auth.register("second", "same@example.com", "Secure123!")
    assert ok is False
    assert "already registered" in message


def test_admin_registration_requires_admin_email_domain(tmp_path):
    auth = AuthController(tmp_path / "auth.db")
    ok, message = auth.register("admin", "admin@example.com", "Secure123!", "ADMIN")
    assert ok is False
    assert "@admin.com" in message

    ok, message = auth.register("admin", "admin@admin.com", "Secure123!", "ADMIN")
    assert ok is True, message


def test_student_and_technician_account_types_are_allowed(tmp_path):
    auth = AuthController(tmp_path / "auth.db")
    ok, message = auth.register("student", "student@example.com", "Secure123!", "STUDENT")
    assert ok is True, message
    ok, message = auth.register("technician", "technician@admin.com", "Secure123!", "TECHNICIAN")
    assert ok is True, message


def test_technician_registration_requires_admin_email_domain(tmp_path):
    auth = AuthController(tmp_path / "auth.db")
    ok, message = auth.register("technician", "technician@example.com", "Secure123!", "TECHNICIAN")
    assert ok is False
    assert message == "Invalid email."

    ok, message = auth.register("technician", "technician@admin.com", "Secure123!", "TECHNICIAN")
    assert ok is True, message


def test_student_registration_accepts_any_email_domain(tmp_path):
    auth = AuthController(tmp_path / "auth.db")
    for username, email in (("gmailstudent", "student@gmail.com"), ("yahoostudent", "student@yahoo.com"), ("adminstudent", "student@admin.com")):
        ok, message = auth.register(username, email, "Secure123!", "STUDENT")
        assert ok is True, message


def test_admin_and_technician_have_the_same_management_access(tmp_path):
    database_path = tmp_path / "auth.db"
    auth = AuthController(database_path)
    admin_ok, _ = auth.register("admin", "admin@admin.com", "Secure123!", "ADMIN")
    technician_ok, _ = auth.register("technician", "technician@admin.com", "Secure123!", "TECHNICIAN")
    assert admin_ok is True
    assert technician_ok is True


def test_registration_does_not_offer_admin_account_type():
    from pathlib import Path

    login_view = Path(__file__).with_name("LoginView.py").read_text(encoding="utf-8")
    assert '"STUDENT", "TECHNICIAN", "ADMIN"' not in login_view
