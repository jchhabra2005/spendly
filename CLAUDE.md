# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 1. Project Context

Spendly is a Flask + SQLite personal expense tracker that lets users register, log in, and record/view/edit/delete expenses with category breakdowns and monthly summaries.

---

## 2. Architecture

```
expense-tracker/
├── app.py               # All Flask routes — the only place routes are defined
├── database/
│   ├── __init__.py      # Empty; marks database/ as a package
│   └── db.py            # SQLite helpers: get_db(), init_db(), seed_db()
├── templates/
│   ├── base.html        # Shared layout — navbar, footer, CSS/JS links
│   ├── landing.html     # Marketing homepage (hero, features, CTA)
│   ├── login.html       # Sign-in form
│   ├── register.html    # Registration form
│   ├── terms.html       # Terms and Conditions (static copy)
│   └── privacy.html     # Privacy Policy (static copy)
├── static/
│   ├── css/style.css    # All styles — single file, organized by component
│   └── js/main.js       # Vanilla JS — intentionally minimal, added per feature
├── requirements.txt     # flask, werkzeug, pytest, pytest-flask
└── venv/                # Local virtualenv — gitignored
```

**Where things live:**
- **New routes** go in `app.py`, grouped with their related placeholder stubs.
- **Database schema and queries** go in `database/db.py` — `get_db()` for connections, `init_db()` for DDL, query functions added alongside those.
- **New pages** are new files in `templates/`, always extending `base.html`.
- **New styles** are appended to `static/css/style.css` as a new named section using the existing `/* --- Section --- */` comment block pattern.
- **New JavaScript** goes in `static/js/main.js`.
- The SQLite database file (`expense_tracker.db`) is created at runtime and is gitignored.

---

## 3. Code Style & Conventions

**Python / Routes (`app.py`)**
- One `@app.route` decorator per function; function name matches the URL slug (e.g. `/add_expense` → `def add_expense()`).
- GET-only routes use `render_template()` directly. POST handlers will check `request.method` and redirect on success.
- Placeholder stubs return a plain string (`return "Feature — coming in Step N"`); replace the entire function body when implementing.
- No blueprints — all routes stay in `app.py` for this project.

**Templates (Jinja2)**
- Every page template starts with `{% extends "base.html" %}`.
- Available blocks: `{% block title %}`, `{% block head %}` (extra `<style>` or `<link>`), `{% block content %}`, `{% block scripts %}` (extra `<script>`).
- Page-specific CSS overrides go inside a `<style>` tag in `{% block head %}` — see `landing.html` for the pattern.
- Error messages use the `.auth-error` class inside an `{% if error %}` guard.
- Use `{{ url_for('route_name') }}` for all internal links — never hardcode paths.

**CSS (`static/css/style.css`)**
- All color, typography, spacing, and radius tokens are CSS custom properties on `:root` — always use `var(--token-name)`, never hardcode values.
- Key tokens: `--ink` (text), `--paper` (background), `--accent` (green `#1a472a`), `--accent-2` (amber), `--danger` (red), `--border`, `--font-display` (DM Serif Display), `--font-body` (DM Sans).
- File is organized into sections with `/* ---- Section ---- */` comment dividers — add new sections at the bottom.
- Responsive breakpoints: 900 px (stack hero, collapse features grid) and 600 px (hide nav links, tighten padding).

**JavaScript (`static/js/main.js`)**
- Vanilla JS only — no frameworks or build step.
- Inline `<script>` blocks inside `{% block scripts %}` are acceptable for page-specific logic (see `landing.html` video modal).

---

## 4. Preferred Libraries & Tools

| Layer | Library / Tool |
|---|---|
| Web framework | Flask 3.1.3 |
| WSGI utilities | Werkzeug 3.1.6 |
| Database | SQLite 3 (stdlib `sqlite3` module) |
| Password hashing | `werkzeug.security` — `generate_password_hash` / `check_password_hash` |
| Sessions | Flask built-in `session` (cookie-based) |
| Testing | pytest 8.3.5 + pytest-flask 1.3.0 |
| Frontend | Vanilla JS, Google Fonts (DM Sans + DM Serif Display via CDN) |

No frontend build tool, no ORM, no JS framework.

---

## 5. Commands

All commands assume the virtualenv is active. This is a **Windows machine**.

```powershell
# Activate the virtual environment
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the development server (http://127.0.0.1:5001)
python app.py

# Run all tests
pytest

# Run a single test file
pytest tests\test_auth.py

# Run tests with output
pytest -v

# Deactivate the virtual environment
deactivate
```

---

## 6. Critical Rules

- **Never use `python3`** — use `python` on this machine.
- **Never use bash-style paths** (`venv/bin/activate`, forward slashes in shell commands) — this is Windows; use backslashes in PowerShell commands.
- **Do not touch `base.html` navbar or footer** when working on a specific feature page — those elements are shared across every page.
- **Do not modify `style.css` variables on `:root`** — the entire visual design depends on them. Add new tokens if needed; never change existing ones.
- **All internal `<a href>` values must use `url_for()`** — never hardcode `/login`, `/register`, etc.
- **`database/db.py` is the only place for SQL** — do not write raw queries inline in `app.py`.
- **`get_db()` must enable `row_factory = sqlite3.Row` and `PRAGMA foreign_keys = ON`** — this is required for all downstream query code to work correctly.
- **Do not commit `expense_tracker.db`** — it is gitignored and environment-specific.
- **Placeholder route stubs** (returning plain strings like `"Logout — coming in Step 3"`) are intentional — replace the whole function body when implementing; do not wrap or call the string return.
- **`app.secret_key` must be set** before any Flask session code works — add it to `app.py` during Step 3 (login/logout).

---

## 7. Roadmap

Ordered by dependency — each step builds on the previous.

**Step 1 — Database setup** *(unblocks everything else)*
- Implement `get_db()`, `init_db()`, `seed_db()` in `database/db.py`.
- Schema needs at minimum: `users` (id, name, email, password_hash, created_at) and `expenses` (id, user_id FK, amount, category, description, date, created_at).
- Call `init_db()` on app startup (in `if __name__ == '__main__'` block).

**Step 2 — Registration POST handler**
- Add `methods=["GET", "POST"]` to the `/register` route.
- Validate name/email/password, hash password with `werkzeug.security`, insert into `users`, redirect to `/login`.
- Show `{{ error }}` in `register.html` on failure.

**Step 3 — Login / logout with sessions**
- Add `app.secret_key`.
- `/login` POST: look up user by email, verify password hash, set `session['user_id']`.
- `/logout`: clear session, redirect to `/`.
- Update `base.html` navbar to show user name + logout link when logged in.

**Step 4 — Login-required decorator**
- Write a `login_required` decorator in `app.py` (or `auth.py`) that redirects to `/login` if `session.get('user_id')` is absent.
- Apply it to all authenticated routes going forward.

**Step 5 — Profile page**
- Implement `/profile` — fetch user row from DB by session user_id, render name/email.

**Step 6 — Dashboard / expense list**
- New route `/dashboard` — fetch all expenses for the logged-in user, pass to template.
- New template `dashboard.html` — table of expenses, monthly total, category breakdown using the `.mock-bar` / `.mock-stat-card` patterns already styled.

**Step 7 — Add expense**
- `/expenses/add` GET + POST — form with amount, category (select), description, date.
- New template `add_expense.html` using `.form-group` / `.form-input` / `.btn-submit` classes.

**Step 8 — Edit expense**
- `/expenses/<int:id>/edit` GET + POST — pre-fill form with existing row, update on submit.
- Verify the expense belongs to `session['user_id']` before allowing edit.

**Step 9 — Delete expense**
- `/expenses/<int:id>/delete` POST only — delete row, redirect to dashboard.
- Same ownership check as edit.

**Step 10 — Filtering and summaries** *(polish)*
- Date-range filter on the dashboard (this month / last 30 days / custom).
- Category breakdown totals shown as percentage bars (CSS already supports this).

**Step 11 — Tests**
- pytest + pytest-flask are already installed.
- Write `tests/conftest.py` with an in-memory SQLite app fixture.
- Test: register, login, add/edit/delete expense, unauthenticated redirect.
