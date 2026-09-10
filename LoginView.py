import tkinter as tk
from tkinter import messagebox

from auth_controller import AuthController


class LoginWindow:
    def __init__(self, root, app_manager):
        self.root = root
        self.app_manager = app_manager
        self.auth = AuthController()
        self.root.title("Laboratory Asset Tracker - Login")
        self.root.geometry("440x430")
        self.root.minsize(440, 430)
        self.root.resizable(True, True)
        self.login_frame = tk.Frame(root)
        self.register_frame = tk.Frame(root)
        self.lockout_job = None
        self.build_login()
        self.build_register()
        self.show(self.login_frame)

    def field(self, parent, label, show=None):
        row = tk.Frame(parent)
        row.pack(fill="x", padx=34, pady=7)
        tk.Label(row, text=label, width=12, anchor="w", font=("Segoe UI", 10)).pack(side="left")
        entry = tk.Entry(row, width=27, font=("Segoe UI", 11), show=show)
        entry.pack(side="right")
        return entry

    def build_login(self):
        tk.Label(self.login_frame, text="LABORATORY ASSET TRACKER", font=("Segoe UI", 18, "bold")).pack(pady=(42, 24))
        self.login_user = self.field(self.login_frame, "Username")
        self.login_password = self.field(self.login_frame, "Password", "*")
        self.add_password_toggle(self.login_frame, self.login_password)
        self.login_button = tk.Button(self.login_frame, text="Login", width=18, command=self.login, bg="#2e7d32", fg="white", font=("Segoe UI", 10, "bold"))
        self.login_button.pack(pady=16)
        self.lockout_label = tk.Label(self.login_frame, text="", fg="#b71c1c")
        self.lockout_label.pack()
        tk.Button(self.login_frame, text="Create Account", width=18, command=lambda: self.show(self.register_frame)).pack()

    def build_register(self):
        tk.Label(self.register_frame, text="CREATE ACCOUNT", font=("Segoe UI", 18, "bold")).pack(pady=(32, 18))
        self.register_user = self.field(self.register_frame, "Username")
        self.register_email = self.field(self.register_frame, "Email")
        self.register_password = self.field(self.register_frame, "Password", "*")
        self.add_password_toggle(self.register_frame, self.register_password)
        tk.Label(self.register_frame, text="Account type").pack(anchor="w", padx=38)
        self.register_role = tk.StringVar(value="STUDENT")
        tk.OptionMenu(self.register_frame, self.register_role, "STUDENT", "TECHNICIAN").pack(anchor="w", padx=34)
        buttons = tk.Frame(self.register_frame)
        buttons.pack(pady=20)
        tk.Button(buttons, text="Register", width=14, command=self.register, bg="#1565c0", fg="white").pack(side="left", padx=5)
        tk.Button(buttons, text="Back to Login", width=14, command=lambda: self.show(self.login_frame)).pack(side="left", padx=5)

    def add_password_toggle(self, parent, entry):
        visible = tk.BooleanVar(value=False)
        tk.Checkbutton(
            parent,
            text="Show Password",
            variable=visible,
            command=lambda: entry.config(show="" if visible.get() else "*"),
        ).pack(anchor="w", padx=142, pady=(0, 4))

    def show(self, frame):
        self.login_frame.pack_forget()
        self.register_frame.pack_forget()
        frame.pack(fill="both", expand=True)

    def login(self):
        success, message, user = self.auth.login(self.login_user.get(), self.login_password.get())
        if success:
            self.app_manager.current_user = user
            if user["role"] == "STUDENT":
                self.app_manager.show_student()
            else:
                self.app_manager.show_tracker()
        else:
            messagebox.showerror("Login failed", message)
            remaining = self.auth.lockout_remaining(self.login_user.get())
            if remaining:
                self.start_lockout_countdown(remaining)

    def start_lockout_countdown(self, remaining):
        if self.lockout_job:
            self.root.after_cancel(self.lockout_job)
        self.login_button.config(state=tk.DISABLED)
        self.lockout_label.config(text=f"Login locked. Try again in {remaining} seconds.")
        self.lockout_job = self.root.after(1000, self.update_lockout_countdown)

    def update_lockout_countdown(self):
        remaining = self.auth.lockout_remaining(self.login_user.get())
        if remaining:
            self.lockout_label.config(text=f"Login locked. Try again in {remaining} seconds.")
            self.lockout_job = self.root.after(1000, self.update_lockout_countdown)
        else:
            self.login_button.config(state=tk.NORMAL)
            self.lockout_label.config(text="Login is available again.")
            self.lockout_job = None

    def register(self):
        success, message = self.auth.register(self.register_user.get(), self.register_email.get(), self.register_password.get(), self.register_role.get())
        if success:
            messagebox.showinfo("Registration", message)
        else:
            title = "Invalid email" if self.register_role.get() == "TECHNICIAN" and message == "Invalid email." else f"Invalid {self.register_role.get().lower()} email" if self.register_role.get() == "ADMIN" and "@admin.com" in message else "Registration"
            messagebox.showerror(title, message)
        if success:
            self.show(self.login_frame)
