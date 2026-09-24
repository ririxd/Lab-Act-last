import tkinter as tk
from datetime import date
from tkinter import messagebox, simpledialog, ttk

from database import CSV_REPORT_PATH, AssetStore
from LoginView import LoginWindow
from StudentView import StudentWindow


class AppManager:
    def __init__(self, root):
        self.root = root
        self.current_user = None
        self.root.geometry("1180x760")
        self.root.minsize(900, 600)
        self.root.resizable(True, True)
        self.show_login()

    def show_login(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        LoginWindow(self.root, self)

    def show_tracker(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        AssetTracker(self.root, self)

    def show_student(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        StudentWindow(self.root, self)


class AssetTracker:
    def __init__(self, root, app_manager):
        self.root = root
        self.app_manager = app_manager
        self.store = AssetStore()
        self.selected_asset = None
        self.root.title("Laboratory Asset Tracker")
        self.root.geometry("1180x760")
        self.root.minsize(960, 620)
        self.build()
        self.refresh()

    def build(self):
        header = tk.Frame(self.root, bg="#17324d", padx=24, pady=18)
        header.pack(fill="x")
        tk.Label(header, text="LABORATORY ASSET TRACKER", fg="white", bg="#17324d", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        tk.Label(header, text="Equipment availability, reservations, and checkouts", fg="#c9d8e6", bg="#17324d", font=("Segoe UI", 10)).pack(anchor="w", pady=(3, 0))
        tk.Label(header, text=f"Signed in: {self.app_manager.current_user['username']}", fg="white", bg="#17324d", font=("Segoe UI", 10)).pack(anchor="e")
        tk.Button(header, text="Logout", command=self.logout).pack(anchor="e", pady=(5, 0))
        if self.app_manager.current_user["role"] in {"ADMIN", "TECHNICIAN"}:
            tk.Button(header, text="Export CSV Report", command=self.export_report).pack(anchor="e", pady=(5, 0))

        form = ttk.LabelFrame(self.root, text="Register Asset", padding=12)
        form.pack(fill="x", padx=18, pady=14)
        self.asset_fields = {}
        fields = (("Asset tag", ""), ("Name", ""), ("Category", ""), ("Total Quantity", ""), ("Location", ""))
        for column, (label, placeholder) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=0, column=column, sticky="w", padx=5)
            entry = ttk.Entry(form, width=22)
            entry.insert(0, placeholder)
            entry.grid(row=1, column=column, padx=5, pady=(3, 0))
            self.asset_fields[label] = entry
        ttk.Button(form, text="Add Asset", command=self.add_asset).grid(row=1, column=6, padx=12)

        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill="x", padx=18, pady=(0, 8))
        ttk.Label(toolbar, text="Search").pack(side="left")
        self.search = ttk.Entry(toolbar, width=32)
        self.search.pack(side="left", padx=8)
        self.search.bind("<Return>", lambda event: self.refresh())
        ttk.Button(toolbar, text="Refresh", command=self.refresh).pack(side="left")
        ttk.Button(toolbar, text="Checkout Selected", command=self.checkout_selected).pack(side="right", padx=4)
        ttk.Button(toolbar, text="Maintenance", command=self.maintenance_selected).pack(side="right", padx=4)
        ttk.Button(toolbar, text="Update Status", command=self.update_status_selected).pack(side="right", padx=4)
        ttk.Button(toolbar, text="Activity Log", command=self.show_activity_log).pack(side="right", padx=4)

        columns = ("id", "tag", "name", "category", "quantity", "borrowed", "borrowable", "location", "condition", "status")
        self.asset_tree = ttk.Treeview(self.root, columns=columns, show="headings", height=12)
        headings = ("ID", "Asset Tag", "Name", "Category", "Total Qty", "Borrowed", "Borrowable", "Location", "Condition", "Status")
        for column, heading in zip(columns, headings):
            self.asset_tree.heading(column, text=heading)
            self.asset_tree.column(column, anchor="center", width=120)
        self.asset_tree.column("id", width=45)
        self.asset_tree.column("name", width=220)
        self.asset_tree.column("borrowed", width=90)
        self.asset_tree.column("borrowable", width=100)
        self.asset_tree.column("quantity", width=90)
        self.asset_tree.bind("<<TreeviewSelect>>", self.select_asset)
        self.asset_tree.pack(fill="both", expand=True, padx=18)

        bottom = ttk.LabelFrame(self.root, text="Active Checkouts", padding=8)
        bottom.pack(fill="x", padx=18, pady=14)
        checkout_columns = ("id", "tag", "name", "borrower", "quantity", "due", "location", "due_time", "status")
        self.checkout_tree = ttk.Treeview(bottom, columns=checkout_columns, show="headings", height=5)
        for column in checkout_columns:
            self.checkout_tree.heading(column, text=column.title())
            self.checkout_tree.column(column, anchor="center", width=150)
        self.checkout_tree.pack(side="left", fill="both", expand=True)
        ttk.Button(bottom, text="Mark Returned", command=self.return_selected).pack(side="right", padx=(10, 2))

    def selected_id(self):
        selection = self.asset_tree.selection()
        return int(self.asset_tree.item(selection[0], "values")[0]) if selection else None

    def select_asset(self, event=None):
        self.selected_asset = self.selected_id()

    def add_asset(self):
        try:
            total_quantity = int(self.asset_fields["Total Quantity"].get())
            self.store.add_asset(
                self.asset_fields["Asset tag"].get(),
                self.asset_fields["Name"].get(),
                self.asset_fields["Category"].get(),
                total_quantity,
                self.asset_fields["Location"].get(),
            )
            self.refresh()
            messagebox.showinfo("Asset added", "The asset is now available for tracking.")
        except ValueError as error:
            messagebox.showerror("Cannot add asset", str(error))

    def logout(self):
        self.app_manager.current_user = None
        self.app_manager.show_login()

    def show_activity_log(self):
        window = tk.Toplevel(self.root)
        window.title("Activity Log")
        window.geometry("900x480")
        window.minsize(700, 350)
        columns = ("time", "actor", "action", "details")
        tree = ttk.Treeview(window, columns=columns, show="headings")
        for column, heading in zip(columns, ("Time", "Actor", "Action", "Details")):
            tree.heading(column, text=heading)
            tree.column(column, anchor="center", width=160)
        tree.column("details", width=360)
        for row in self.store.activity_log():
            tree.insert("", "end", values=tuple(row))
        tree.pack(fill="both", expand=True, padx=12, pady=12)

    def export_report(self):
        try:
            report_path = self.store.export_inventory_csv(self.app_manager.current_user["username"], CSV_REPORT_PATH)
            messagebox.showinfo("Report exported", f"Inventory report saved to {report_path}")
        except (PermissionError, OSError) as error:
            messagebox.showerror("Export failed", str(error))


    def refresh(self):
        for item in self.asset_tree.get_children():
            self.asset_tree.delete(item)
        for row in self.store.assets(self.search.get() if hasattr(self, "search") else ""):
            self.asset_tree.insert("", "end", values=tuple(row))
        for item in self.checkout_tree.get_children():
            self.checkout_tree.delete(item)
        for row in self.store.active_checkouts():
            self.checkout_tree.insert("", "end", values=tuple(row))

    def dialog(self, title, fields):
        window = tk.Toplevel(self.root)
        window.title(title)
        window.resizable(False, False)
        entries = {}
        for row, field in enumerate(fields):
            label, value = field[:2]
            ttk.Label(window, text=label).grid(row=row, column=0, padx=12, pady=6, sticky="w")
            if len(field) > 2:
                entry = ttk.Combobox(window, values=field[2], state="readonly", width=29)
                if field[2]:
                    entry.set(field[2][0])
            else:
                entry = ttk.Entry(window, width=32)
            entry.insert(0, value)
            entry.grid(row=row, column=1, padx=12, pady=6)
            entries[label] = entry
        return window, entries

    def reserve_selected(self):
        asset_id = self.selected_id()
        if not asset_id:
            messagebox.showwarning("Select an asset", "Select an asset first.")
            return
        window, fields = self.dialog("Reserve equipment", (("Borrower", ""), ("Quantity", "1"), ("Start date", date.today().isoformat()), ("End date", date.today().isoformat()), ("Purpose", "")))
        ttk.Button(window, text="Create Reservation", command=lambda: self.submit_reservation(window, fields, asset_id)).grid(row=5, column=1, pady=12, sticky="e")

    def submit_reservation(self, window, fields, asset_id):
        try:
            self.store.reserve(asset_id, *(fields[label].get() for label in ("Borrower", "Quantity", "Start date", "End date", "Purpose")))
            window.destroy(); self.refresh(); messagebox.showinfo("Reserved", "Reservation created successfully.")
        except ValueError as error:
            messagebox.showerror("Cannot reserve", str(error), parent=window)

    def checkout_selected(self):
        asset_id = self.selected_id()
        if not asset_id:
            messagebox.showwarning("Select an asset", "Select an asset first.")
            return
        selected_values = self.asset_tree.item(self.asset_tree.selection()[0], "values")
        borrowable_quantity = int(selected_values[6])
        status = selected_values[9]
        if borrowable_quantity < 1 or status != "Available":
            messagebox.showerror(
                "Checkout unavailable",
                f"This item cannot be borrowed. Status: {status}; borrowable quantity: {borrowable_quantity}.",
            )
            return
        students = self.store.registered_students()
        if not students:
            messagebox.showerror("No registered students", "Register a student account before assigning equipment.")
            return
        window, fields = self.dialog(
            "Checkout equipment",
            (("Borrower", "", students), ("Quantity", "1"), ("Due date", date.today().isoformat()), ("Return time", "17:00"), ("Borrow location", "")),
        )
        ttk.Button(window, text="Complete Checkout", command=lambda: self.submit_checkout(window, fields, asset_id)).grid(row=5, column=1, pady=12, sticky="e")

    def submit_checkout(self, window, fields, asset_id):
        try:
            self.store.checkout(asset_id, fields["Borrower"].get(), fields["Quantity"].get(), fields["Due date"].get(), fields["Borrow location"].get(), fields["Return time"].get())
            window.destroy(); self.refresh(); messagebox.showinfo("Checked out", "Equipment checked out successfully.")
        except ValueError as error:
            messagebox.showerror("Cannot checkout", str(error), parent=window)

    def return_selected(self):
        selection = self.checkout_tree.selection()
        if not selection:
            messagebox.showwarning("Select a checkout", "Select an active checkout first.")
            return
        checkout_id = int(self.checkout_tree.item(selection[0], "values")[0])
        try:
            self.store.return_checkout(checkout_id)
            self.refresh()
        except ValueError as error:
            messagebox.showerror("Cannot return equipment", str(error))

    def maintenance_selected(self):
        asset_id = self.selected_id()
        if not asset_id:
            messagebox.showwarning("Select an asset", "Select an asset first.")
            return
        description = simpledialog.askstring("Maintenance", "Describe the maintenance work:", parent=self.root)
        if description:
            try:
                self.store.set_maintenance(asset_id, description)
                self.refresh()
            except ValueError as error:
                messagebox.showerror("Cannot update maintenance", str(error))

    def update_status_selected(self):
        asset_id = self.selected_id()
        if not asset_id:
            messagebox.showwarning("Select an asset", "Select an asset first.")
            return
        current_status = self.asset_tree.item(self.asset_tree.selection()[0], "values")[9]
        window = tk.Toplevel(self.root)
        window.title("Update asset status")
        window.resizable(False, False)
        ttk.Label(window, text="New status").grid(row=0, column=0, padx=12, pady=12)
        status = ttk.Combobox(window, values=("Available", "Out of Stock", "Under Maintenance", "Lost", "Damaged", "Retired"), state="readonly", width=22)
        status.set(current_status)
        status.grid(row=0, column=1, padx=12, pady=12)

        def save_status():
            try:
                self.store.update_status(asset_id, status.get())
                window.destroy()
                self.refresh()
            except ValueError as error:
                messagebox.showerror("Cannot update status", str(error), parent=window)

        ttk.Button(window, text="Save Status", command=save_status).grid(row=1, column=1, padx=12, pady=(0, 12), sticky="e")



if __name__ == "__main__":
    root = tk.Tk()
    AppManager(root)
    root.mainloop()
