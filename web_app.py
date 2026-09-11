from __future__ import annotations

from flask import Flask, current_app, flash, redirect, render_template, request, session, url_for

from auth_controller import AuthController
from database import AssetStore


def create_app(database_path=None):
    app = Flask(__name__, template_folder="Front")
    app.config["SECRET_KEY"] = "lab-tracker-dev"
    app.config["AUTH"] = AuthController(database_path)
    app.config["STORE"] = AssetStore(database_path)

    @app.before_request
    def require_login():
        allowed = {"login", "register", "static"}
        if request.endpoint in allowed:
            return None
        if "user" not in session:
            return redirect(url_for("login"))
        return None

    @app.after_request
    def prevent_auth_page_caching(response):
        if request.endpoint in {"login", "register", "logout"}:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    def management_user():
        user = session.get("user")
        return user if user and user.get("role") in {"ADMIN", "TECHNICIAN"} else None

    @app.route("/")
    def index():
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "")
            password = request.form.get("password", "")
            success, message, user = current_app.config["AUTH"].login(username, password)
            if success:
                session["user"] = user
                role = user["role"]
                if role in {"ADMIN", "TECHNICIAN"}:
                    return redirect(url_for("inventory"))
                return redirect(url_for("student"))
            flash(message, "error")
        return render_template("login.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "GET":
            return render_template("register.html")

        username = request.form.get("username", "")
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        role = request.form.get("role", "STUDENT")
        success, message = current_app.config["AUTH"].register(username, email, password, role)
        if success:
            flash("Registration successful. Please sign in.", "success")
        else:
            flash(message, "error")
        return redirect(url_for("login"))

    @app.route("/logout")
    def logout():
        session.clear()
        flash("Logged out.", "info")
        return redirect(url_for("login"))

    @app.route("/inventory", methods=["GET", "POST"])
    def inventory():
        user = session.get("user")
        if not user:
            return redirect(url_for("login"))

        if request.method == "POST" and request.form.get("action") == "add_asset":
            if not management_user():
                flash("Only administrators and technicians can add assets.", "error")
                return redirect(url_for("inventory"))
            try:
                current_app.config["STORE"].add_asset(
                    request.form.get("asset_tag", ""),
                    request.form.get("name", ""),
                    request.form.get("category", ""),
                    request.form.get("quantity", 0),
                    request.form.get("location", ""),
                )
                flash("Asset added successfully.", "success")
            except ValueError as exc:
                flash(str(exc), "error")
            return redirect(url_for("inventory"))

        assets = current_app.config["STORE"].assets()
        pending = current_app.config["STORE"].pending_reservations() if management_user() else []
        return render_template("inventory.html", user=user, assets=assets, pending=pending)

    @app.route("/reserve", methods=["POST"])
    def reserve():
        user = session.get("user")
        if not user:
            return redirect(url_for("login"))
        try:
            current_app.config["STORE"].reserve(
                request.form.get("asset_id"),
                user["username"],
                request.form.get("quantity", 1),
                request.form.get("start_date"),
                request.form.get("end_date"),
                request.form.get("purpose", ""),
                requires_approval=user["role"] == "STUDENT" or bool(request.form.get("requires_approval")),
            )
            flash("Reservation created.", "success")
        except ValueError as exc:
            flash(str(exc), "error")
        return redirect(url_for("inventory"))

    @app.route("/checkout", methods=["POST"])
    def checkout():
        user = session.get("user")
        if not user:
            return redirect(url_for("login"))
        if user["role"] not in {"ADMIN", "TECHNICIAN"}:
            flash("Only administrators and technicians can complete checkouts.", "error")
            return redirect(url_for("inventory"))
        try:
            current_app.config["STORE"].checkout(
                request.form.get("asset_id"),
                request.form.get("borrower", ""),
                request.form.get("quantity", 1),
                request.form.get("due_date"),
                request.form.get("checkout_location", ""),
                request.form.get("due_time", "17:00"),
            )
            flash("Checkout recorded.", "success")
        except ValueError as exc:
            flash(str(exc), "error")
        return redirect(url_for("inventory"))

    @app.route("/return/<int:checkout_id>", methods=["POST"])
    def return_checkout(checkout_id):
        try:
            current_app.config["STORE"].return_checkout(checkout_id, request.form.get("return_condition", "Good"))
            flash("Equipment returned.", "success")
        except ValueError as exc:
            flash(str(exc), "error")
        return redirect(url_for("student"))

    @app.route("/approve_reservation/<int:reservation_id>", methods=["POST"])
    def approve_reservation(reservation_id):
        if not management_user():
            flash("Only administrators and technicians can approve requests.", "error")
            return redirect(url_for("student"))
        try:
            action = request.form.get("decision", "approve")
            approved = action == "approve"
            current_app.config["STORE"].approve_reservation(reservation_id, approved=approved)
            flash("Reservation updated.", "success")
        except ValueError as exc:
            flash(str(exc), "error")
        return redirect(url_for("inventory"))

    @app.route("/student")
    def student():
        user = session.get("user")
        if not user:
            return redirect(url_for("login"))
        checkout_rows = current_app.config["STORE"].borrower_checkouts(user["username"])
        return render_template("student.html", user=user, checkouts=checkout_rows)

    @app.route("/history")
    def history():
        user = session.get("user")
        if not user:
            return redirect(url_for("login"))
        log_rows = current_app.config["STORE"].activity_log(limit=50)
        return render_template("history.html", user=user, activity=log_rows)

    @app.route("/export")
    def export_inventory():
        user = session.get("user")
        if not user:
            return redirect(url_for("login"))
        try:
            report_path = current_app.config["STORE"].export_inventory_csv(user["username"])
            flash(f"Inventory exported to {report_path}.", "success")
        except PermissionError as exc:
            flash(str(exc), "error")
        return redirect(url_for("inventory"))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
