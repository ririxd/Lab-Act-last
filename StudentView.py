import tkinter as tk
from tkinter import ttk

from database import AssetStore


class StudentWindow:
    def __init__(self, root, app_manager):
        self.root = root
        self.app_manager = app_manager
        self.store = AssetStore()
        self.borrower = app_manager.current_user["username"]
        self.root.title("Student Borrowed Equipment")
        self.root.geometry("940x500")
        self.root.minsize(760, 420)
        self.root.resizable(True, True)
        self.build()
        self.refresh()

    def build(self):
        header = tk.Frame(self.root, bg="#17324d", padx=24, pady=18)
        header.pack(fill="x")
        tk.Label(header, text="STUDENT EQUIPMENT DASHBOARD", fg="white", bg="#17324d", font=("Segoe UI", 19, "bold")).pack(anchor="w")
        tk.Label(header, text=f"Borrowed equipment for {self.borrower}", fg="#c9d8e6", bg="#17324d", font=("Segoe UI", 10)).pack(anchor="w", pady=(3, 0))
        tk.Button(header, text="Logout", command=self.logout).pack(anchor="e", pady=(5, 0))

        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill="x", padx=18, pady=12)
        ttk.Label(toolbar, text="Your active borrowed equipment").pack(side="left")
        ttk.Button(toolbar, text="Refresh", command=self.refresh).pack(side="right")

        columns = ("id", "tag", "name", "quantity", "checked_out", "due_date", "due_time", "location")
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings", height=12)
        headings = ("ID", "Asset Tag", "Equipment", "Quantity", "Checked Out", "Return Date", "Return Time", "Location")
        for column, heading in zip(columns, headings):
            self.tree.heading(column, text=heading)
            self.tree.column(column, anchor="center", width=115)
        self.tree.column("name", width=200)
        self.tree.column("location", width=150)
        self.tree.pack(fill="both", expand=True, padx=18, pady=(0, 18))

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in self.store.borrower_checkouts(self.borrower):
            self.tree.insert("", "end", values=tuple(row))

    def logout(self):
        self.app_manager.current_user = None
        self.app_manager.show_login()
