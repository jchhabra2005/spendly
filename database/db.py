import sqlite3
import os
from datetime import date, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "expense_tracker.db")

DEFAULT_CATEGORIES = [
    "Food", "Transport", "Shopping", "Entertainment",
    "Health", "Utilities", "Education", "Other",
]


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT,
            email         TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS categories (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            is_default INTEGER NOT NULL DEFAULT 0,
            user_id    INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            amount      REAL    NOT NULL,
            category_id INTEGER NOT NULL,
            description TEXT,
            date        TEXT    NOT NULL,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id)     REFERENCES users(id)      ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );

        CREATE INDEX IF NOT EXISTS idx_expenses_user_id  ON expenses(user_id);
        CREATE INDEX IF NOT EXISTS idx_expenses_date     ON expenses(date);
        CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category_id);
    """)
    conn.commit()
    conn.close()
    seed_default_categories()


def seed_default_categories():
    conn = get_connection()
    for name in DEFAULT_CATEGORIES:
        existing = conn.execute(
            "SELECT id FROM categories WHERE name = ? AND is_default = 1", (name,)
        ).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO categories (name, is_default, user_id) VALUES (?, 1, NULL)", (name,)
            )
    conn.commit()
    conn.close()


# ------------------------------------------------------------------ #
# Users                                                               #
# ------------------------------------------------------------------ #

def create_user(email, password, display_name=None):
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (display_name, email, generate_password_hash(password)),
        )
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return user
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_user_by_id(user_id):
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user


def get_user_by_email(email):
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return user


def verify_password(stored_hash, password):
    return check_password_hash(stored_hash, password)


def update_user_profile(user_id, display_name, email):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE users SET name = ?, email = ? WHERE id = ?",
            (display_name, email, user_id),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def update_user_password(user_id, old_pw, new_pw):
    conn = get_connection()
    user = conn.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user or not check_password_hash(user["password_hash"], old_pw):
        conn.close()
        return False
    conn.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (generate_password_hash(new_pw), user_id),
    )
    conn.commit()
    conn.close()
    return True


def delete_user(user_id):
    conn = get_connection()
    result = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    deleted = result.rowcount > 0
    conn.close()
    return deleted


# ------------------------------------------------------------------ #
# Expenses                                                            #
# ------------------------------------------------------------------ #

def create_expense(user_id, amount, category_id, date_str, description=None):
    if amount <= 0:
        return None
    try:
        from datetime import datetime
        expense_date = datetime.strptime(date_str, "%d-%m-%Y").date()
        if expense_date > date.today():
            return None
    except ValueError:
        return None
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO expenses (user_id, amount, category_id, date, description) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category_id, date_str, description),
    )
    conn.commit()
    expense = conn.execute("SELECT * FROM expenses WHERE id = ?", (cursor.lastrowid,)).fetchone()
    conn.close()
    return expense


def get_expense_by_id(expense_id, user_id):
    conn = get_connection()
    expense = conn.execute(
        "SELECT e.*, c.name as category_name FROM expenses e "
        "JOIN categories c ON e.category_id = c.id "
        "WHERE e.id = ? AND e.user_id = ?",
        (expense_id, user_id),
    ).fetchone()
    conn.close()
    return expense


def get_expenses(user_id, page=1, filters=None):
    if filters is None:
        filters = {}
    per_page = 20
    clauses = ["e.user_id = ?"]
    params = [user_id]
    if filters.get("date_from"):
        clauses.append("e.date >= ?")
        params.append(filters["date_from"])
    if filters.get("date_to"):
        clauses.append("e.date <= ?")
        params.append(filters["date_to"])
    if filters.get("category_id"):
        clauses.append("e.category_id = ?")
        params.append(filters["category_id"])
    if filters.get("amount_min"):
        clauses.append("e.amount >= ?")
        params.append(filters["amount_min"])
    if filters.get("amount_max"):
        clauses.append("e.amount <= ?")
        params.append(filters["amount_max"])
    where = " AND ".join(clauses)
    conn = get_connection()
    total = conn.execute(
        "SELECT COUNT(*) FROM expenses e WHERE " + where, params
    ).fetchone()[0]
    offset = (page - 1) * per_page
    items = conn.execute(
        "SELECT e.*, c.name as category_name FROM expenses e "
        "JOIN categories c ON e.category_id = c.id "
        "WHERE " + where + " ORDER BY e.date DESC, e.id DESC LIMIT ? OFFSET ?",
        params + [per_page, offset],
    ).fetchall()
    conn.close()
    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": max(1, (total + per_page - 1) // per_page),
    }


def update_expense(expense_id, user_id, fields):
    allowed = {"amount", "category_id", "date", "description"}
    set_parts = []
    params = []
    for key, val in fields.items():
        if key in allowed:
            set_parts.append(key + " = ?")
            params.append(val)
    if not set_parts:
        return False
    params.extend([expense_id, user_id])
    conn = get_connection()
    result = conn.execute(
        "UPDATE expenses SET " + ", ".join(set_parts) + " WHERE id = ? AND user_id = ?",
        params,
    )
    conn.commit()
    updated = result.rowcount > 0
    conn.close()
    return updated


def delete_expense(expense_id, user_id):
    conn = get_connection()
    result = conn.execute(
        "DELETE FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user_id)
    )
    conn.commit()
    deleted = result.rowcount > 0
    conn.close()
    return deleted


def get_expense_summary(user_id, date_from=None, date_to=None):
    clauses = ["e.user_id = ?"]
    params = [user_id]
    if date_from:
        clauses.append("e.date >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("e.date <= ?")
        params.append(date_to)
    where = " AND ".join(clauses)
    conn = get_connection()
    rows = conn.execute(
        "SELECT c.name as category, SUM(e.amount) as total "
        "FROM expenses e JOIN categories c ON e.category_id = c.id "
        "WHERE " + where + " GROUP BY c.name ORDER BY total DESC",
        params,
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ------------------------------------------------------------------ #
# Categories                                                          #
# ------------------------------------------------------------------ #

def get_categories(user_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM categories WHERE is_default = 1 OR user_id = ? ORDER BY is_default DESC, name",
        (user_id,),
    ).fetchall()
    conn.close()
    return rows


def create_category(user_id, name):
    conn = get_connection()
    existing = conn.execute(
        "SELECT id FROM categories WHERE name = ? AND user_id = ?", (name, user_id)
    ).fetchone()
    if existing:
        conn.close()
        return None
    cursor = conn.execute(
        "INSERT INTO categories (name, is_default, user_id) VALUES (?, 0, ?)", (name, user_id)
    )
    conn.commit()
    cat = conn.execute("SELECT * FROM categories WHERE id = ?", (cursor.lastrowid,)).fetchone()
    conn.close()
    return cat


def update_category(category_id, user_id, name):
    conn = get_connection()
    cat = conn.execute("SELECT is_default FROM categories WHERE id = ?", (category_id,)).fetchone()
    if not cat or cat["is_default"] == 1:
        conn.close()
        return False
    result = conn.execute(
        "UPDATE categories SET name = ? WHERE id = ? AND user_id = ?",
        (name, category_id, user_id),
    )
    conn.commit()
    updated = result.rowcount > 0
    conn.close()
    return updated


def delete_category(category_id, user_id):
    conn = get_connection()
    cat = conn.execute("SELECT is_default FROM categories WHERE id = ?", (category_id,)).fetchone()
    if not cat or cat["is_default"] == 1:
        conn.close()
        return False
    other = conn.execute(
        "SELECT id FROM categories WHERE name = 'Other' AND is_default = 1"
    ).fetchone()
    if other:
        conn.execute(
            "UPDATE expenses SET category_id = ? WHERE category_id = ? AND user_id = ?",
            (other["id"], category_id, user_id),
        )
    conn.execute(
        "DELETE FROM categories WHERE id = ? AND user_id = ?", (category_id, user_id)
    )
    conn.commit()
    conn.close()
    return True


# ------------------------------------------------------------------ #
# Dummy Data                                                          #
# ------------------------------------------------------------------ #

def seed_dummy_data():
    conn = get_connection()
    existing = conn.execute(
        "SELECT COUNT(*) FROM users WHERE email IN (?, ?, ?)",
        ("aarav@example.com", "priya@example.com", "rohan@example.com"),
    ).fetchone()[0]
    if existing > 0:
        conn.close()
        return

    dummy_users = [
        ("Aarav Sharma", "aarav@example.com"),
        ("Priya Mehta",  "priya@example.com"),
        ("Rohan Kapoor", "rohan@example.com"),
    ]
    user_ids = []
    for name, email in dummy_users:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash("password123")),
        )
        user_ids.append(cursor.lastrowid)
    conn.commit()

    cats = {
        row["name"]: row["id"]
        for row in conn.execute(
            "SELECT id, name FROM categories WHERE is_default = 1"
        ).fetchall()
    }

    today = date.today()
    start_of_month = today.replace(day=1)

    def fmt(d):
        return d.strftime("%d-%m-%Y")

    sample_expenses = [
        (120.0,  "Food",          fmt(today - timedelta(days=7)),   "Lunch at dhaba"),
        (450.0,  "Transport",     fmt(today - timedelta(days=14)),  "Ola cab to airport"),
        (1200.0, "Shopping",      fmt(today - timedelta(days=30)),  "T-shirts from Myntra"),
        (80.0,   "Food",          fmt(today - timedelta(days=1)),   "Tea and samosa"),
        (2500.0, "Health",        fmt(today - timedelta(days=45)),  "Pharmacy"),
        (600.0,  "Entertainment", fmt(today - timedelta(days=21)),  None),
        (300.0,  "Utilities",     fmt(start_of_month),              "Mobile recharge"),
        (950.0,  "Education",     fmt(today - timedelta(days=60)),  "Udemy course"),
        (200.0,  "Food",          fmt(today - timedelta(days=4)),   "Zomato order"),
        (3500.0, "Shopping",      fmt(today - timedelta(days=35)),  None),
    ]

    for user_id in user_ids:
        for amount, cat_name, date_str, note in sample_expenses:
            cat_id = cats.get(cat_name, cats["Other"])
            conn.execute(
                "INSERT INTO expenses (user_id, amount, category_id, date, description) VALUES (?, ?, ?, ?, ?)",
                (user_id, amount, cat_id, date_str, note),
            )
    conn.commit()
    conn.close()
