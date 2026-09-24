import tkinter as tk
from tkinter import ttk

from database import AssetStore


class StudentWindow:
    def __init__(self, root, app_manager):
        self.root = root
        self.app_manager = app_manager
        self.store = AssetStore()
        self.borrower = app_manager.current_user["username"]
        self.root.title("My Borrowed Equipment")
        self.root.geometry("1080x560")
        self.root.minsize(860, 460)
        self.root.resizable(True, True)
        self.build()
        self.refresh()

    def build(self):
        header = tk.Frame(self.root, bg="#17324d", padx=24, pady=18)
        header.pack(fill="x")
        tk.Label(header, text="MY EQUIPMENT", fg="white", bg="#17324d", font=("Segoe UI", 19, "bold")).pack(anchor="w")
        tk.Label(header, text=f"Active equipment issued to {self.borrower}", fg="#c9d8e6", bg="#17324d", font=("Segoe UI", 10)).pack(anchor="w", pady=(3, 0))
        tk.Button(header, text="Logout", command=self.logout).pack(anchor="e", pady=(5, 0))

        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill="x", padx=18, pady=12)
        self.summary = ttk.Label(toolbar, text="Loading active borrowings...")
        self.summary.pack(side="left")
        ttk.Button(toolbar, text="Refresh", command=self.refresh).pack(side="right")

        columns = ("tag", "name", "category", "quantity", "checked_out", "due_date", "due_time", "location", "condition")
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings", height=12)
        headings = ("Asset Tag", "Equipment", "Category", "Quantity", "Issued", "Return Date", "Return Time", "Collection Location", "Condition")
        for column, heading in zip(columns, headings):
            self.tree.heading(column, text=heading)
            self.tree.column(column, anchor="center", width=115)
        self.tree.column("name", width=190)
        self.tree.column("category", width=130)
        self.tree.column("location", width=160)
        self.tree.pack(fill="both", expand=True, padx=18, pady=(0, 18))

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        checkouts = self.store.borrower_checkouts(self.borrower)
        self.summary.config(
            text=(
                f"{len(checkouts)} active borrowing(s) · Review each item's due date and return location."
                if checkouts
                else "No equipment is currently issued to you."
            )
        )
        for row in checkouts:
            self.tree.insert("", "end", values=(
                row[1], row[2], row[8], row[3], row[4], row[5], row[6], row[7], row[9],
            ))

    def logout(self):
        self.app_manager.current_user = None
        self.app_manager.show_login()
