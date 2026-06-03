---
description: Seed dummy expenses for a specific user into the Spendly SQLite database. Accepts three arguments — user_id, number of expenses, and number of past months to distribute them across — and inserts realistic Indian expense records while respecting every table constraint.
argument-hint: <user-id> <num-expenses> <num-months>
allowed-tools: Write, PowerShell
---

# /seed-expense — Seed Dummy Expenses

**Arguments received:** $ARGUMENTS

Parse `$ARGUMENTS` as exactly three space-separated tokens:

| Position | Name           | Type | Description                                                                 |
|----------|----------------|------|-----------------------------------------------------------------------------|
| 1st      | `user_id`      | int  | ID of the user to attach expenses to — must exist in the `users` table      |
| 2nd      | `num_expenses` | int  | Total number of expense rows to insert (min 1)                              |
| 3rd      | `num_months`   | int  | Number of past months to spread the dates across (min 1); dates land in the range `[today − num_months×30 days, today]` inclusive |

**Example invocation:** `/seed-expense 3 10 2`
→ inserts 10 expenses for user 3, dates spread randomly across the last 2 months.

If fewer or more than 3 tokens are provided, print a usage message and stop — do not attempt an insert.

---

## Constraints respected

| Column / Constraint                        | How it is satisfied                                                                                        |
|--------------------------------------------|------------------------------------------------------------------------------------------------------------|
| `user_id INTEGER NOT NULL`                 | Provided as argument; script queries `SELECT id FROM users WHERE id = ?` first and aborts if not found    |
| `amount REAL NOT NULL`                     | Drawn from per-category realistic INR ranges — always `> 0`                                               |
| `category_id INTEGER NOT NULL`             | Fetched from `SELECT id FROM categories WHERE is_default = 1`; guaranteed to exist after `init_db()`      |
| `date TEXT NOT NULL` (format `DD-MM-YYYY`) | Built with `strftime("%d-%m-%Y")`; always ≤ today, always ≥ today − num_months×30 days                    |
| `description TEXT` (nullable)              | Drawn from a per-category description pool; `None` is used occasionally to exercise the nullable path      |
| `created_at TIMESTAMP DEFAULT`             | Omitted — SQLite fills it automatically                                                                    |
| `FOREIGN KEY (user_id) → users(id)`        | Verified by pre-flight SELECT before any INSERT                                                            |
| `FOREIGN KEY (category_id) → categories(id)` | Only IDs returned by the live DB query are used — no hard-coded IDs                                    |
| `PRAGMA foreign_keys = ON`                 | Enforced inside `get_connection()`                                                                         |

---

## Steps to execute

Passing multiline Python to `python -c` is unreliable on Windows. Use the **Write tool** to create a
temp file, then **PowerShell** to run and delete it.

**Step 1** — parse `$ARGUMENTS`. Split on whitespace. If not exactly 3 tokens, tell the user the
correct usage and stop.

**Step 2** — use the Write tool to create `_seed_exp_tmp.py` at the project root
(`C:\Users\ASUS\Downloads\expense-tracker\expense-tracker`) with the script below, substituting
the three parsed values for `USER_ID`, `NUM_EXPENSES`, and `NUM_MONTHS`:

```python
import sys, os, random
from datetime import date, timedelta
sys.path.insert(0, os.getcwd())
from database.db import get_connection

USER_ID      = <user_id>
NUM_EXPENSES = <num_expenses>
NUM_MONTHS   = <num_months>

CATEGORY_AMOUNTS = {
    "Food":          (80,   600),
    "Transport":     (50,   900),
    "Shopping":      (299,  4999),
    "Entertainment": (100,  1500),
    "Health":        (150,  5000),
    "Utilities":     (100,  2500),
    "Education":     (499,  6000),
    "Other":         (50,   1000),
}

CATEGORY_DESCRIPTIONS = {
    "Food":          ["Zomato order", "Swiggy delivery", "Lunch at dhaba", "Tea and samosa",
                      "Grocery run", "Dinner with family", None],
    "Transport":     ["Ola cab", "Rapido bike", "Metro card recharge", "Auto to office",
                      "Uber to airport", None],
    "Shopping":      ["Myntra order", "Amazon purchase", "Reliance Digital", "DMart essentials",
                      "Clothing haul", None],
    "Entertainment": ["BookMyShow tickets", "Netflix subscription", "Spotify premium",
                      "Gaming top-up", None],
    "Health":        ["Apollo pharmacy", "Gym membership", "Doctor consultation",
                      "Lab tests", "Cult.fit session", None],
    "Utilities":     ["Mobile recharge", "Electricity bill", "DTH recharge",
                      "Broadband bill", "Water bill", None],
    "Education":     ["Udemy course", "Coursera subscription", "Book purchase",
                      "Workshop fee", "College fee instalment", None],
    "Other":         ["Miscellaneous", "Gift for friend", "Charity donation",
                      "ATM withdrawal", None],
}

conn = get_connection()

user = conn.execute("SELECT id FROM users WHERE id = ?", (USER_ID,)).fetchone()
if not user:
    print("Error: No user found with id", USER_ID)
    conn.close()
    sys.exit(1)

cats = conn.execute(
    "SELECT id, name FROM categories WHERE is_default = 1"
).fetchall()
if not cats:
    print("Error: No default categories found — run init_db() first.")
    conn.close()
    sys.exit(1)

today      = date.today()
start_date = today - timedelta(days=NUM_MONTHS * 30)
span_days  = (today - start_date).days

inserted = 0
for _ in range(NUM_EXPENSES):
    cat           = random.choice(cats)
    cat_id        = cat["id"]
    cat_name      = cat["name"]
    lo, hi        = CATEGORY_AMOUNTS.get(cat_name, (50, 1000))
    amount        = round(random.uniform(lo, hi), 2)
    rand_day      = random.randint(0, span_days)
    expense_date  = (start_date + timedelta(days=rand_day)).strftime("%d-%m-%Y")
    description   = random.choice(CATEGORY_DESCRIPTIONS.get(cat_name, [None]))
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category_id, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (USER_ID, amount, cat_id, expense_date, description),
    )
    inserted += 1

conn.commit()
conn.close()

print("Expenses inserted:", inserted)
print("  user_id      :", USER_ID)
print("  date range   :", start_date.strftime("%d-%m-%Y"), "to", today.strftime("%d-%m-%Y"))
print("  months span  :", NUM_MONTHS)
```

**Step 3** — use the PowerShell tool to run then delete the temp file:

```powershell
cd "C:\Users\ASUS\Downloads\expense-tracker\expense-tracker"
venv\Scripts\python.exe _seed_exp_tmp.py
Remove-Item _seed_exp_tmp.py
```

---

## After the script runs

Present the output to the user in a clear summary block, e.g.:

```
Expenses seeded:
  user_id    : 3
  count      : 10
  date range : 01-04-2026 to 01-06-2026
  months span: 2

Login and view them at: http://127.0.0.1:5001/dashboard
```

Also remind the user:
- Expenses use only the **8 default categories** (Food, Transport, Shopping, Entertainment, Health, Utilities, Education, Other) — no user-specific custom categories are touched.
- Amounts are in **INR**, drawn from realistic per-category ranges.
- Dates are always in the past — no future date is ever inserted.
- Re-running the command for the same `user_id` safely adds more rows; there is no uniqueness constraint on expenses.
