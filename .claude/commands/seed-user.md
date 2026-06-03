---
description: Insert a single dummy user with a realistic Indian name and Gmail address into the Spendly SQLite database (users table) for development and testing. Generates a unique email on every invocation so the UNIQUE constraint is never violated.
allowed-tools: Bash, PowerShell, Write
---

# /seed-user — Seed a Dummy User

Insert one dummy user into `expense_tracker.db` without violating any table constraint.
Report the new user's credentials to the user so they can immediately log in.

---

## What this command does

1. Picks a random Indian first name and last name from curated pools (20 first names, 20 last names).
2. Builds a realistic Gmail address: `firstname.lastname<nn>@gmail.com` where `<nn>` is a random 2-digit number (10–99), giving 36 000+ unique combinations before a collision is possible.
3. Hashes a known plain-text password with `werkzeug.security.generate_password_hash`, satisfying the `NOT NULL` constraint on `password_hash`.
4. Inserts the row using `database.db.get_connection()` (which enables `PRAGMA foreign_keys = ON` and sets `row_factory = sqlite3.Row`).
5. Commits and confirms success, then prints the new user's `id`, `name`, `email`, and plain-text password.

---

## Constraints respected

| Column / Constraint             | How it is satisfied                                                                 |
|---------------------------------|-------------------------------------------------------------------------------------|
| `email TEXT UNIQUE NOT NULL`    | Email is `firstname.lastname<nn>@gmail.com` where `<nn>` is a random 2-digit integer (10–99); 20 first names × 20 last names × 90 suffixes = 36 000 unique combinations before any collision |
| `password_hash TEXT NOT NULL`   | Always produced by `generate_password_hash` before the INSERT                      |
| `name TEXT` (nullable)          | Realistic Indian full name drawn from curated first-name and last-name pools        |
| `created_at TIMESTAMP DEFAULT`  | Not supplied — SQLite default `CURRENT_TIMESTAMP` fills it automatically            |
| `FOREIGN KEY` (categories/expenses) | No expenses are inserted, so no FK dependency on `categories` is created        |
| `PRAGMA foreign_keys = ON`      | Enforced by `get_connection()` — the INSERT never bypasses it                       |

---

## Steps to execute

Passing a multiline Python script to `python -c` via PowerShell here-strings is unreliable on Windows
(quote escaping issues). Instead, use the **Write tool** to write the script to a temp file, run it
with the **PowerShell tool**, then delete the temp file.

**Step 1** — use the Write tool to create `_seed_tmp.py` at the project root with this exact content:

```python
import sys, os, random
sys.path.insert(0, os.getcwd())
from database.db import get_connection
from werkzeug.security import generate_password_hash

FIRST_NAMES = [
    "Aarav", "Arjun", "Rohan", "Vikram", "Rahul",
    "Aditya", "Karan", "Nikhil", "Siddharth", "Gaurav",
    "Priya", "Ananya", "Neha", "Shreya", "Kavya",
    "Divya", "Riya", "Simran", "Tanvi", "Meera",
]
LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Singh", "Kumar",
    "Mehta", "Gupta", "Joshi", "Nair", "Reddy",
    "Iyer", "Khanna", "Malhotra", "Kapoor", "Bose",
    "Das", "Rao", "Chauhan", "Tiwari", "Mishra",
]

first    = random.choice(FIRST_NAMES)
last     = random.choice(LAST_NAMES)
nn       = random.randint(10, 99)
name     = first + " " + last
email    = first.lower() + "." + last.lower() + str(nn) + "@gmail.com"
plain_pw = "Test@1234"
pw_hash  = generate_password_hash(plain_pw)

conn = get_connection()
try:
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, pw_hash),
    )
    conn.commit()
    uid = cur.lastrowid
    print("User inserted successfully")
    print("  id      :", uid)
    print("  name    :", name)
    print("  email   :", email)
    print("  password:", plain_pw, "  <-- plain text, dev only")
except Exception as exc:
    print("Insert failed:", exc)
finally:
    conn.close()
```

**Step 2** — use the PowerShell tool to run then delete the temp file:

```powershell
cd "C:\Users\ASUS\Downloads\expense-tracker\expense-tracker"
venv\Scripts\python.exe _seed_tmp.py
Remove-Item _seed_tmp.py
```

---

## After the script runs

Present the output to the user in a clear summary block, e.g.:

```
New dummy user created:
  id       : <id>
  name     : Arjun Sharma
  email    : arjun.sharma47@gmail.com
  password : Test@1234

Login at: http://127.0.0.1:5001/login
```

Also remind the user:
- This user has **no expenses** — the dashboard will be empty until expenses are added manually or via another seed command.
- The plain-text password (`Test@1234`) is for **local development only** and is never stored — only its bcrypt hash is in the database.
- If the script fails with `UNIQUE constraint failed: users.email`, the same name + 2-digit combo was already used. Simply re-run `/seed-user` — the random pick will almost certainly produce a different combination.
