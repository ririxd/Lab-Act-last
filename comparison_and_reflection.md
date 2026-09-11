# Desktop and Web Conversion Notes

## Desktop vs Web Comparison

| Area | Desktop application | Web application |
|---|---|---|
| Interface | Tkinter windows and widgets | Browser pages rendered with HTML, CSS, and Jinja |
| Entry point | `app.py` | `web_app.py` |
| Business logic | Reused from `AuthController` and `AssetStore` | Reused from `AuthController` and `AssetStore` |
| Database | SQLite file | The same SQLite file for local use |
| Interaction | Button callbacks and dialogs | HTTP routes and HTML forms |
| Client-side behavior | Tkinter event handlers | Limited JavaScript for browser UX |
| Deployment | Runs on a desktop Python installation | Runs on a local Flask host |

## Reflection

The conversion changes the presentation layer without replacing the domain layer. Authentication, validation, inventory, reservations, quantity checks, approvals, returns, and audit logging remain in Python. The Flask application acts as an adapter: it receives browser requests, calls the existing controllers, and renders the result through Jinja templates.

Tkinter widgets cannot be sent to a browser because they are native desktop objects. The browser version therefore uses HTML controls and forms while preserving the original desktop source as a working reference and fallback.

A pending borrow request does not immediately reduce available stock because it still requires approval. The requested quantity must be checked against the available quantity to prevent overbooking. Borrowed items are already checked out; pending requests are waiting for an administrator or technician decision.

SQLite remains appropriate for this local laboratory because it is lightweight, file-based, and requires no separate database server. Before public deployment, the system would need HTTPS, a production WSGI server, secure secrets, CSRF protection, stronger authorization checks, backups, monitoring, and a production database such as PostgreSQL.
