from datetime import date

import pytest

from auth_controller import AuthController
from database import AssetStore


def create_student(database_path, username):
    auth = AuthController(database_path)
    auth.register(username, f"{username}@example.com", "Secure123!", "STUDENT")


def test_reservation_conflict_is_rejected(tmp_path):
    store = AssetStore(tmp_path / "test.db")
    store.add_asset("LAB-001", "Oscilloscope", "Electronics", 1, "Room 1")
    store.reserve(1, "Ava", 1, "2026-09-10", "2026-09-12", "Experiment A")

    try:
        store.reserve(1, "Ben", 1, "2026-09-11", "2026-09-13", "Experiment B")
    except ValueError as error:
        assert "available quantity" in str(error)
    else:
        raise AssertionError("Overlapping reservation was accepted")


def test_return_releases_checkout_quantity(tmp_path):
    database_path = tmp_path / "test.db"
    create_student(database_path, "Ava")
    create_student(database_path, "Ben")
    store = AssetStore(database_path)
    store.add_asset("LAB-002", "Power Supply", "Electronics", 1, "Room 2")
    store.checkout(1, "Ava", 1, "2026-09-15", "Room 2")
    assert len(store.active_checkouts()) == 1
    store.return_checkout(1, "Good")
    assert len(store.active_checkouts()) == 0
    store.checkout(1, "Ben", 1, "2026-09-20", "Room 2")
    assert len(store.active_checkouts()) == 1


def test_assets_reports_borrowable_quantity(tmp_path):
    database_path = tmp_path / "test.db"
    create_student(database_path, "Ava")
    create_student(database_path, "Ben")
    store = AssetStore(database_path)
    store.add_asset("LAB-003", "Thermal Camera", "Imaging", 3, "Room 3")
    store.checkout(1, "Ava", 1, "2026-09-30", "Room 3")
    today = date.today().isoformat()
    store.reserve(1, "Ben", 1, today, today, "Experiment C")

    asset = store.assets()[0]
    assert asset[4] == 3
    assert asset[5] == 1

    store.set_maintenance(1, "Annual inspection")
    assert store.assets()[0][6] == 0


def test_unavailable_status_blocks_borrowing(tmp_path):
    store = AssetStore(tmp_path / "test.db")
    store.add_asset("LAB-004", "Centrifuge", "Lab Equipment", 2, "Room 4")
    store.update_status(1, "Lost")

    try:
        store.checkout(1, "Ava", 1, "2026-09-30", "Room 11")
    except ValueError as error:
        assert "not available" in str(error)
    else:
        raise AssertionError("Unavailable asset was checked out")

    assert store.assets()[0][6] == 0


def test_lost_damaged_and_maintenance_assets_cannot_be_borrowed(tmp_path):
    for status in ("Lost", "Damaged", "Under Maintenance"):
        store = AssetStore(tmp_path / f"{status.replace(' ', '_')}.db")
        store.add_asset("LAB-011", "Lab Equipment", "Equipment", 1, "Room 211")
        store.update_status(1, status)

        assert store.assets()[0][6] == 0
        try:
            store.checkout(1, "Ava", 1, "2026-09-30", "Room 211")
        except ValueError as error:
            assert "not available" in str(error)
        else:
            raise AssertionError(f"{status} asset was checked out")
        try:
            store.reserve(1, "Ava", 1, date.today().isoformat(), date.today().isoformat(), "Invalid attempt")
        except ValueError as error:
            assert "not available" in str(error)
        else:
            raise AssertionError(f"{status} asset was reserved")


def test_asset_status_shows_out_of_stock_when_all_units_are_borrowed(tmp_path):
    database_path = tmp_path / "test.db"
    create_student(database_path, "Ava")
    store = AssetStore(database_path)
    store.add_asset("LAB-005", "Microscope", "Lab Equipment", 2, "Room 5")
    assert store.assets()[0][9] == "Available"

    store.checkout(1, "Ava", 2, "2026-09-30", "Room 5")
    asset = store.assets()[0]
    assert asset[5] == 2
    assert asset[6] == 0
    assert asset[9] == "Out of Stock"

    store.return_checkout(1)
    assert store.assets()[0][9] == "Available"


def test_location_changes_only_when_checkout_occurs(tmp_path):
    database_path = tmp_path / "test.db"
    create_student(database_path, "Ava")
    store = AssetStore(database_path)
    store.add_asset("LAB-007", "Soldering Station", "Electronics", 1, "Storage Room")
    assert store.assets()[0][7] == "Storage Room"

    try:
        store.checkout(1, "Ava", 1, "2026-09-30", "Workshop Room")
    except ValueError as error:
        assert "registered location" in str(error)
    else:
        raise AssertionError("A checkout location different from the registered location was accepted")
    assert store.assets()[0][7] == "Storage Room"

    store.checkout(1, "Ava", 1, "2026-09-30", "Storage Room")
    assert store.assets()[0][7] == "Storage Room"
    assert store.active_checkouts()[0][6] == "Storage Room"
    assert store.active_checkouts()[0][8] == "Out of Stock"


def test_checkout_location_must_match_active_reservation(tmp_path):
    database_path = tmp_path / "test.db"
    create_student(database_path, "Ava")
    store = AssetStore(database_path)
    store.add_asset("LAB-008", "Function Generator", "Electronics", 1, "Storage Room")
    today = date.today().isoformat()
    store.reserve(1, "Ava", 1, today, today, "Experiment D")

    try:
        store.checkout(1, "Ava", 1, today, "Workshop Room")
    except ValueError as error:
        assert "registered location" in str(error)
    else:
        raise AssertionError("Mismatched reservation location was accepted")

    assert store.assets()[0][7] == "Storage Room"


def test_checkout_location_must_match_reservation_for_any_borrower(tmp_path):
    database_path = tmp_path / "test.db"
    create_student(database_path, "Ava")
    create_student(database_path, "Ben")
    store = AssetStore(database_path)
    store.add_asset("LAB-009", "Logic Analyzer", "Electronics", 1, "Room 203")
    today = date.today().isoformat()
    store.reserve(1, "Ava", 1, today, today, "Experiment E")

    try:
        store.checkout(1, "Ben", 1, today, "Room 204")
    except ValueError as error:
        assert "registered location" in str(error)
    else:
        raise AssertionError("A different checkout location was accepted")


def test_status_update_changes_selected_asset_condition(tmp_path):
    store = AssetStore(tmp_path / "test.db")
    store.add_asset("LAB-010", "Bench Supply", "Electronics", 1, "Room 210")
    store.update_status(1, "Retired")

    assert store.assets()[0][8] == "Retired"


def test_assigned_student_sees_checkout_in_student_dashboard_data(tmp_path):
    database_path = tmp_path / "test.db"
    auth = AuthController(database_path)
    auth.register("student1", "student1@example.com", "Secure123!", "STUDENT")
    store = AssetStore(database_path)
    store.add_asset("LAB-012", "Digital Scale", "Lab Equipment", 1, "Room 212")
    store.checkout(1, "student1", 1, "2026-09-30", "Room 212", "16:30")

    checkout = store.borrower_checkouts("student1")[0]
    assert checkout[2] == "Digital Scale"
    assert checkout[5] == "2026-09-30"
    assert checkout[6] == "16:30"


def test_original_quantity_borrowed_makes_borrowable_zero(tmp_path):
    store = AssetStore(tmp_path / "test.db")
    store.add_asset("LAB-006", "Tripod Stand", "Lab Equipment", 3, "Room 6", borrowed_quantity=3)

    asset = store.assets()[0]
    assert asset[4] == 3
    assert asset[5] == 3
    assert asset[6] == 0
    assert asset[9] == "Out of Stock"


def test_activity_log_returns_asset_actions(tmp_path):
    store = AssetStore(tmp_path / "test.db")
    store.add_asset("LAB-016", "Safety Meter", "Safety", 1, "Room 216")

    activity = store.activity_log()
    assert activity[0][2] == "ASSET_ADDED"
    assert "LAB-016" in activity[0][3]


def test_reservation_approval_and_quantity_limits(tmp_path):
    database_path = tmp_path / "test.db"
    create_student(database_path, "Ava")
    create_student(database_path, "Ben")
    store = AssetStore(database_path)
    store.add_asset("LAB-017", "Spectrometer", "Analysis", 2, "Room 217")

    today = date.today().isoformat()
    with pytest.raises(ValueError):
        store.reserve(1, "Ava", 3, today, today, "Too many", requires_approval=True)

    reservation_id = store.reserve(1, "Ava", 2, today, today, "Approval needed", requires_approval=True)
    pending = store.pending_reservations()
    assert len(pending) == 1
    assert pending[0][3] == "Ava"

    store.approve_reservation(reservation_id, approved=True)
    approved = store.reservations()
    assert len(approved) == 1
    assert approved[0][3] == "Ava"

    try:
        store.checkout(1, "Ben", 1, today, "Room 217")
    except ValueError as error:
        assert "available quantity" in str(error)
    else:
        raise AssertionError("Approved reservation did not reserve quantity correctly")


def test_inventory_csv_export_is_admin_only(tmp_path):
    database_path = tmp_path / "test.db"
    auth = AuthController(database_path)
    auth.register("admin", "admin@admin.com", "Secure123!", "ADMIN")
    auth.register("student", "student@example.com", "Secure123!", "STUDENT")
    store = AssetStore(database_path)
    store.add_asset("LAB-013", "Digital Meter", "Electronics", 3, "Room 213")
    report_path = tmp_path / "inventory.csv"

    try:
        store.export_inventory_csv("student", report_path)
    except PermissionError as error:
        assert "management users" in str(error)
    else:
        raise AssertionError("Student was allowed to export a report")

    store.export_inventory_csv("admin", report_path)
    report = report_path.read_text(encoding="utf-8")
    assert "LAB-013" in report
    assert "Borrowable" in report


def test_only_registered_students_can_be_assigned_borrowed_items(tmp_path):
    database_path = tmp_path / "test.db"
    auth = AuthController(database_path)
    auth.register("admin", "admin@admin.com", "Secure123!", "ADMIN")
    auth.register("technician", "technician@example.com", "Secure123!", "TECHNICIAN")
    auth.register("student", "student@example.com", "Secure123!", "STUDENT")
    store = AssetStore(database_path)
    store.add_asset("LAB-014", "Signal Meter", "Electronics", 1, "Room 214")

    assert store.registered_students() == ["student"]
    try:
        store.checkout(1, "admin", 1, "2026-09-30", "Room 214")
    except ValueError as error:
        assert "registered students" in str(error)
    else:
        raise AssertionError("Admin was incorrectly assigned as the borrower")

    store.checkout(1, "student", 1, "2026-09-30", "Room 214")


